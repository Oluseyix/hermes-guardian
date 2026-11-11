import copy
from pathlib import Path
import tempfile
import unittest

from guardian.policy import DEFAULT, Policy


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.protected = self.root / "vault"
        self.protected.mkdir()
        self.public = self.root / "public.txt"
        self.config = copy.deepcopy(DEFAULT)
        self.config["protected_paths"] = [{"path": str(self.protected), "action": "block"}]
        self.policy = Policy(self.config)

    def action(self, tool, **args):
        return self.policy.evaluate(tool, args).action

    def test_allowed_read(self):
        self.assertEqual(self.action("read_file", path=str(self.public)), "allow")

    def test_write_approval(self):
        self.assertEqual(self.action("write_file", path=str(self.public), content="hello"), "approve")

    def test_replace_patch_approval(self):
        self.assertEqual(self.action("patch", path=str(self.public), old_string="a", new_string="b"), "approve")

    def test_unknown_tool_block(self):
        self.assertEqual(self.action("execute_code", code="pass"), "block")

    def test_explicit_external_tool_rule(self):
        self.config["rules"].append({"tool": "web_search", "action": "allow"})
        self.assertEqual(Policy(self.config).evaluate("web_search", {"query": "weather"}).action, "allow")
        self.assertEqual(Policy(self.config).evaluate("web_search_extra", {}).action, "block")

    def test_protected_tools(self):
        for tool in ("read_file", "write_file", "patch"):
            with self.subTest(tool=tool):
                self.assertEqual(self.action(tool, path=str(self.protected / "key")), "block")

    def test_path_boundary(self):
        self.assertEqual(self.action("read_file", path=str(self.root / "vault-copy")), "allow")

    def test_traversal(self):
        self.assertEqual(self.action("read_file", path=str(self.root / "x" / ".." / "vault" / "key")), "block")

    def test_ancestor_block(self):
        self.assertEqual(self.action("terminal", command=f"rm -rf {self.root}"), "block")

    def test_symlink_to_protected(self):
        link = self.root / "alias"
        link.symlink_to(self.protected, target_is_directory=True)
        self.assertEqual(self.action("read_file", path=str(link / "not-created")), "block")

    def test_protected_symlink_alias(self):
        target = self.root / "real"
        target.mkdir()
        link = self.root / "protected-link"
        link.symlink_to(target, target_is_directory=True)
        self.config["protected_paths"] = [{"path": str(link), "action": "block"}]
        policy = Policy(self.config)
        self.assertEqual(policy.evaluate("read_file", {"path": str(target / "key")}).action, "block")

    def test_symlink_loop(self):
        link = self.root / "loop"
        link.symlink_to(link)
        self.assertEqual(self.action("read_file", path=str(link)), "block")

    def test_path_ambiguity(self):
        for path in ("relative", "~/key", "$HOME/key", "/tmp/*", "//host/path", "/tmp/a\nb", "", None, 42, ["/tmp/x"]):
            with self.subTest(path=path):
                self.assertEqual(self.action("read_file", path=path), "block")

    def test_conflict_precedence_order_independent(self):
        for actions in (("allow", "approve", "block"), ("block", "approve", "allow"), ("approve", "allow")):
            self.config["rules"] = [{"tool": "x", "action": a} for a in actions]
            self.assertEqual(Policy(self.config).evaluate("x", {}).action, "block" if "block" in actions else "approve")

    def test_allow_cannot_override_protection(self):
        self.config["rules"] = [{"tool": "terminal", "action": "allow"}]
        self.assertEqual(Policy(self.config).evaluate("terminal", {"command": f"cat {self.protected}/key"}).action, "block")

    def test_protected_approval(self):
        self.config["protected_paths"][0]["action"] = "approve"
        self.assertEqual(Policy(self.config).evaluate("read_file", {"path": str(self.protected / "key")}).action, "approve")

    def test_self_protection(self):
        self.config["protected_paths"] = []
        policy = Policy(self.config, mandatory_paths=(self.root,))
        result = policy.evaluate("read_file", {"path": str(self.public)})
        self.assertEqual((result.action, result.rule), ("block", "self_protection"))

    def test_shell_grammar(self):
        for command in ("pwd", f"cat '{self.public}'", f"rm -rf -- {self.public}", f"touch {self.public}", f"mkdir -p {self.root}/new", f"cp {self.public} {self.root}/copy", f"mv {self.public} {self.root}/moved"):
            with self.subTest(command=command):
                self.assertEqual(self.action("terminal", command=command), "approve")

    def test_ambiguous_shell_corpus(self):
        corpus = ["pwd; id", "pwd && id", "pwd | cat", "pwd > /tmp/file", "cat $(pwd)",
                  "cat `pwd`", "cat /tmp/*", "cat /tmp/{a,b}", "cat /tmp/[ab]", "cat /tmp/?",
                  "sh -c pwd", "bash -c pwd", "python -c pass", "sudo cat /tmp/x", "env cat /tmp/x",
                  "X=y cat /tmp/x", "/bin/cat /tmp/x", "cat relative", "cat ~/key", "cat $HOME/key",
                  "cat /tmp/x\nrm /tmp/y", "cat /tmp/x &", "cat < /tmp/x", "cat /tmp/a\\ b",
                  "cat '/tmp/unterminated", "rm --preserve-root /tmp/x", "cp /tmp/x", "pwd -P",
                  "cat", "cat /tmp/x # comment", "cat /tmp/!x", "", " ", None, 42,
                  "cat '/tmp/a;b'", "cat '/tmp/a\x00b'", "cat /tmp/x " + "x" * 17000]
        for command in corpus:
            with self.subTest(command=repr(command)[:80]):
                self.assertEqual(self.action("terminal", command=command), "block")

    def test_cp_both_operands_guarded(self):
        for command in (f"cp {self.protected}/key {self.public}", f"cp {self.public} {self.protected}/key"):
            self.assertEqual(self.action("terminal", command=command), "block")

    def test_workdir_guarded(self):
        self.assertEqual(self.action("terminal", command="pwd", workdir=str(self.protected)), "block")
        self.assertEqual(self.action("terminal", command="pwd", workdir="relative"), "block")

    def test_background_and_unrecognized_parameters_blocked(self):
        for extra in ({"background": True}, {"background": "false"}, {"stdin": "data"}, {"cwd": "/tmp"}):
            self.assertEqual(self.action("terminal", command="pwd", **extra), "block")

    def test_timeout_bounds(self):
        for timeout in (True, "30", -1, 0, 181, 10000, None):
            self.assertEqual(self.action("terminal", command="pwd", timeout=timeout), "block")
        self.assertEqual(self.action("terminal", command="pwd", timeout=60), "approve")

    def test_symlink_before_parent_traversal(self):
        nested = self.protected / "nested"
        nested.mkdir()
        link = self.root / "alias"
        link.symlink_to(nested, target_is_directory=True)
        self.assertEqual(self.action("read_file", path=str(link / ".." / "key")), "block")

    def test_symlink_to_missing_protected_target(self):
        link = self.root / "alias"
        link.symlink_to(self.protected / "future")
        self.assertEqual(self.action("write_file", path=str(link), content="data"), "block")

    def test_alternate_patch_modes_blocked(self):
        for extra in ({"mode": "patch"}, {"patch": "*** Delete File: /tmp/x"}, {"cross_profile": True}):
            self.assertEqual(self.action("patch", path=str(self.public), **extra), "block")

    def test_invalid_call(self):
        for tool, args in ((None, {}), ([], {}), ("read_file", None), ("read_file", [])):
            self.assertEqual(self.policy.evaluate(tool, args).action, "block")

    def test_configuration_strictness(self):
        invalid = [None, [], {}, {**self.config, "typo": True}, {**self.config, "default_action": "permit"},
                   {**self.config, "rules": [{"tool": "*", "action": "allow"}]},
                   {**self.config, "rules": [{"tool": "x", "action": "allow", "args": {}}]},
                   {**self.config, "rules": "x"}, {**self.config, "rules": [{"tool": [], "action": "allow"}]},
                   {**self.config, "protected_paths": [{"path": "/tmp", "action": "allow"}]},
                   {**self.config, "protected_paths": [{"path": "relative", "action": "block"}]},
                   {**self.config, "protected_paths": [{"path": "$HOME", "action": "block"}]}]
        for config in invalid:
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    Policy(config)

    def test_input_not_mutated(self):
        args = {"command": f"rm -rf {self.public}"}
        before = copy.deepcopy((self.config, args))
        self.policy.evaluate("terminal", args)
        self.assertEqual((self.config, args), before)

    def test_deterministic(self):
        decisions = [self.policy.evaluate("read_file", {"path": str(self.public)}) for _ in range(20)]
        self.assertTrue(all(d == decisions[0] for d in decisions))


if __name__ == "__main__":
    unittest.main()
