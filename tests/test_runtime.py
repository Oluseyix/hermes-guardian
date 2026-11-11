import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from guardian.policy import DEFAULT
from guardian.runtime import Guardian


class Context:
    def __init__(self, config):
        self.config = config
        self.hooks = {}

    def get_config(self, key, default=None):
        assert key == "policy"
        return self.config

    def register_cli_command(self, *args, **kwargs):
        pass

    def register_hook(self, name, callback):
        self.hooks[name] = callback


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.config = copy.deepcopy(DEFAULT)
        self.config["protected_paths"] = [{"path": str(self.root / "vault"), "action": "block"}]
        self.ctx = Context(self.config)
        self.guard = Guardian(self.ctx, lambda: self.root / "audit")

    def call(self, tool="read_file", **args):
        return self.guard.pre_tool_call(tool, args, task_id="sensitive-task", future_argument=True)

    def records(self):
        return [json.loads(line) for line in (self.root / "audit" / "audit.jsonl").read_text().splitlines()]

    def test_allow_returns_none(self):
        self.assertIsNone(self.call(path=str(self.root / "public")))
        self.assertEqual(self.records()[0]["action"], "allow")

    def test_official_approval_directive(self):
        result = self.call("write_file", path=str(self.root / "public"), content="private-body")
        self.assertEqual(result["action"], "approve")
        self.assertTrue(result["rule_key"].startswith("hermes-guardian:"))
        self.assertNotIn("private-body", str(result))
        self.assertEqual(self.records()[0]["action"], "approve")

    def test_approval_keys_per_invocation(self):
        a = self.call("terminal", command="pwd")
        b = self.call("terminal", command="pwd")
        self.assertNotEqual(a["rule_key"], b["rule_key"])

    def test_block_has_message(self):
        result = self.call(path=str(self.root / "vault" / "secret"))
        self.assertEqual(result["action"], "block")
        self.assertTrue(result["message"])

    def test_invalid_config_blocks_and_audits(self):
        self.ctx.config = {"typo": "private-error"}
        result = self.call(path=str(self.root / "public"))
        self.assertEqual(result["action"], "block")
        self.assertEqual(self.records()[0]["reason"], "policy_unavailable")
        self.assertNotIn("private-error", str(result))

    def test_configuration_recovers_next_call(self):
        self.ctx.config = None
        self.assertEqual(self.call(path=str(self.root / "public"))["action"], "block")
        self.ctx.config = self.config
        self.assertIsNone(self.call(path=str(self.root / "public")))

    def test_config_read_exception_caught(self):
        with patch.object(self.ctx, "get_config", side_effect=OSError("secret")):
            self.assertEqual(self.call(path=str(self.root / "public"))["action"], "block")

    def test_evaluator_exception_caught(self):
        with patch("guardian.runtime.Policy.evaluate", side_effect=RuntimeError("secret")):
            result = self.call(path=str(self.root / "public"))
        self.assertEqual(result["action"], "block")
        self.assertNotIn("secret", str(result))

    def test_storage_resolution_failure_blocks(self):
        self.guard.data_dir = lambda: (_ for _ in ()).throw(OSError("private-path"))
        result = self.call(path=str(self.root / "public"))
        self.assertEqual(result["action"], "block")
        self.assertNotIn("private-path", str(result))

    def test_audit_failure_blocks_even_allow(self):
        with patch("guardian.runtime.Audit.append", side_effect=OSError("secret")):
            result = self.call(path=str(self.root / "public"))
        self.assertEqual(result["action"], "block")
        self.assertIn("audit unavailable", result["message"])

    def test_outer_boundary_failure_blocks(self):
        with patch("guardian.runtime.uuid4", side_effect=OSError("entropy failure")):
            self.assertEqual(self.call(path=str(self.root / "public"))["action"], "block")

    def test_self_protection_survives_empty_user_paths(self):
        self.ctx.config["protected_paths"] = []
        self.assertEqual(self.call(path=str(self.root / "audit" / "audit.jsonl"))["action"], "block")
        self.assertEqual(self.call(path=str(Path(__file__).resolve().parents[1] / "plugin.yaml"))["action"], "block")

    def test_custom_hermes_home_control_files_protected(self):
        self.ctx.config["protected_paths"] = []
        self.guard.data_dir = lambda: self.root / "profile" / "plugin-data" / "hermes-guardian"
        self.assertEqual(self.call(path=str(self.root / "profile" / "config.yaml"))["action"], "block")

    def test_profile_storage_is_not_cached_between_calls(self):
        self.guard.data_dir = lambda: self.root / "profile-a" / "plugin-data" / "hermes-guardian"
        self.call(path=str(self.root / "public"))
        self.guard.data_dir = lambda: self.root / "profile-b" / "plugin-data" / "hermes-guardian"
        self.call(path=str(self.root / "public"))
        for profile in ("profile-a", "profile-b"):
            self.assertTrue((self.root / profile / "plugin-data" / "hermes-guardian" / "audit.jsonl").exists())

    def test_no_sensitive_values_in_audit_or_directive(self):
        secrets = ["password=SuperSecret", "Bearer opaque-token", "https://u:p@example.test/?key=secret", "-----BEGIN PRIVATE KEY-----"]
        for secret in secrets:
            result = self.call("write_file", path=str(self.root / "public"), content=secret)
            self.assertNotIn(secret, str(result))
        self.call("my-secret-tool-name", token="api-secret", nested={"password": "nested-secret"})
        serialized = (self.root / "audit" / "audit.jsonl").read_text()
        for secret in secrets + ["my-secret-tool-name", "api-secret", "nested-secret", "sensitive-task", str(self.root)]:
            self.assertNotIn(secret, serialized)
        self.assertEqual(self.records()[-1]["tool"], "[REDACTED]")

    def test_native_entrypoint_registers_only_declared_hook(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("guardian_plugin_test", root / "__init__.py", submodule_search_locations=[str(root)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(lambda: [sys.modules.pop(k, None) for k in list(sys.modules) if k.startswith(spec.name)])
        spec.loader.exec_module(module)
        module.register(self.ctx)
        self.assertEqual(set(self.ctx.hooks), {"pre_tool_call"})


if __name__ == "__main__":
    unittest.main()
