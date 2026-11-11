"""Real installed-Hermes dispatcher smoke test; never mocks or patches core.

Developer harness only, not imported by the plugin. Run with Hermes's installed
Python and --source pointing at its matching trusted source tree. Interactive
mode uses the real host prompt on a PTY; answer Once/Deny or let it time out.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
import stat
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--mode", choices=("unattended", "cron", "single-query", "interactive", "approvals-off"), default="unattended")
    parser.add_argument("--expect", choices=("allow", "deny", "timeout"), default="deny")
    options = parser.parse_args()
    options.workspace.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="guardian-host-", dir=options.workspace)).resolve()
    home, fixtures = run / "home", run / "fixtures"
    (home / "plugins").mkdir(parents=True)
    fixtures.mkdir()
    vault = fixtures / "vault"
    vault.mkdir()
    (vault / "key.txt").write_text("PROTECTED_SENTINEL_DO_NOT_RETURN")
    public = fixtures / "public.txt"
    public.write_text("PUBLIC_FIXTURE")
    alias = fixtures / "alias"
    alias.symlink_to(vault, target_is_directory=True)
    plugin = Path(__file__).resolve().parents[1]
    (home / "plugins" / "hermes-guardian").symlink_to(plugin, target_is_directory=True)
    policy = {
        "default_action": "block",
        "rules": [{"tool": "read_file", "action": "allow"},
                  {"tool": "write_file", "action": "approve"},
                  {"tool": "patch", "action": "approve"},
                  {"tool": "terminal", "action": "allow"}],
        "protected_paths": [{"path": str(vault), "action": "block"}],
    }
    config = {
        "cli": {"expose_on_path": False},
        "terminal": {"backend": "local", "cwd": str(fixtures)},
        "plugins": {"enabled": ["hermes-guardian"], "entries": {"hermes-guardian": {"settings": {"policy": policy}}}},
        "approvals": {"mode": "off" if options.mode == "approvals-off" else "manual", "timeout": 3 if options.expect == "timeout" else 30,
                      "cron_mode": "deny", "unattended_mode": "deny", "single_query_mode": "deny"},
    }
    (home / "config.yaml").write_text(json.dumps(config))
    os.environ["HERMES_HOME"] = str(home)
    for key in ("HERMES_INTERACTIVE", "HERMES_CRON_SESSION", "HERMES_SINGLE_QUERY_SESSION", "HERMES_EXEC_ASK", "HERMES_GATEWAY_SESSION", "HERMES_YOLO"):
        os.environ.pop(key, None)
    if options.mode == "interactive":
        os.environ["HERMES_INTERACTIVE"] = "1"
    elif options.mode == "cron":
        os.environ["HERMES_CRON_SESSION"] = "1"
    elif options.mode == "single-query":
        os.environ["HERMES_SINGLE_QUERY_SESSION"] = "1"
    sys.path.insert(0, str(options.source.resolve()))

    from hermes_cli.plugins import discover_plugins, get_plugin_manager
    discover_plugins()
    loaded = next(p for p in get_plugin_manager().list_plugins() if p["name"] == "hermes-guardian")
    assert loaded["enabled"] and loaded["hooks"] == 1 and not loaded["error"], loaded
    print("LOADED:", json.dumps(loaded), flush=True)
    from model_tools import handle_function_call

    checks = []

    def call(name, args):
        return handle_function_call(name, args, task_id="guardian-integration", session_id="guardian-integration")

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print("PASS:", name, flush=True)

    result = call("read_file", {"path": str(public)})
    check("real allowed read returns fixture", "PUBLIC_FIXTURE" in result)
    for label, path in (("protected", vault / "key.txt"), ("symlink", alias / "key.txt"), ("traversal", fixtures / "unused" / ".." / "vault" / "key.txt")):
        result = call("read_file", {"path": str(path)})
        check(f"{label} read blocked", "Guardian" in result and "PROTECTED_SENTINEL_DO_NOT_RETURN" not in result)
    result = call("terminal", {"command": f"cat {public}"})
    check("real allowed terminal cat", "PUBLIC_FIXTURE" in result)
    result = call("terminal", {"command": f"rm -rf {vault}"})
    check("protected deletion veto preserves fixture", "Guardian" in result and (vault / "key.txt").exists())
    for command in ("pwd && pwd", "cat $(pwd)", "cat /tmp/*", "sh -c pwd"):
        result = call("terminal", {"command": command})
        check(f"ambiguous command blocked: {command}", "Guardian" in result and "ambiguous_arguments" in result)
    result = call("patch", {"mode": "patch", "patch": f"*** Begin Patch\n*** Delete File: {public}\n*** End Patch"})
    check("alternate patch mode veto", "Guardian" in result and public.exists())
    result = call("read_file", {"path": "public.txt"})
    check("relative path blocked", "Guardian" in result)
    loop = fixtures / "loop"
    loop.symlink_to(loop)
    result = call("read_file", {"path": str(loop)})
    check("symlink loop blocked", "Guardian" in result and "ambiguous_arguments" in result)
    result = call("write_file", {"path": str(vault / "key.txt"), "content": "MUST_NOT_WRITE"})
    check("protected write veto preserves contents", "Guardian" in result and (vault / "key.txt").read_text() == "PROTECTED_SENTINEL_DO_NOT_RETURN")
    destination = fixtures / "approval.txt"
    started = time.monotonic()
    result = call("write_file", {"path": str(destination), "content": "SENSITIVE_DEMO_PAYLOAD_NOT_FOR_AUDIT"})
    elapsed = time.monotonic() - started
    expected_write = options.expect == "allow" or options.mode == "approvals-off"
    check("approval write outcome", destination.exists() == expected_write)
    if expected_write:
        check("approved fixture content", destination.read_text() == "SENSITIVE_DEMO_PAYLOAD_NOT_FOR_AUDIT")
    else:
        check("denial has host error", "error" in result.lower())
    if options.mode != "interactive":
        check("unattended gate returns promptly", elapsed < 10)
    if options.expect == "timeout" and options.mode == "interactive":
        check("interactive timeout was bounded", 2 <= elapsed < 12)
    audit_path = home / "plugin-data" / "hermes-guardian" / "audit.jsonl"
    result_self = call("read_file", {"path": str(audit_path)})
    check("audit self-protection", "Guardian" in result_self and "[REDACTED]" not in result_self)
    with audit_path.open("rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        blocked = call("read_file", {"path": str(public)})
        check("real audit contention blocks allowed tool", "audit unavailable" in blocked and "PUBLIC_FIXTURE" not in blocked)
    recovered = call("read_file", {"path": str(public)})
    check("recovers after audit lock release", "Guardian" not in recovered and "error" not in json.loads(recovered))
    config["plugins"]["entries"]["hermes-guardian"]["settings"]["policy"] = {"invalid": True}
    (home / "config.yaml").write_text(json.dumps(config))
    blocked = call("read_file", {"path": str(public)})
    check("invalid live configuration blocks", "policy_unavailable" in blocked and "PUBLIC_FIXTURE" not in blocked)
    config["plugins"]["entries"]["hermes-guardian"]["settings"]["policy"] = policy
    (home / "config.yaml").write_text(json.dumps(config))
    repaired_fixture = fixtures / "after-repair.txt"
    repaired_fixture.write_text("RECOVERY_FIXTURE")
    recovered = call("read_file", {"path": str(repaired_fixture)})
    check("recovers after configuration repair", "RECOVERY_FIXTURE" in recovered)
    audit = audit_path.read_text()
    check("audit file owner-only", stat.S_IMODE(audit_path.stat().st_mode) == 0o600)
    for secret in ("SENSITIVE_DEMO_PAYLOAD_NOT_FOR_AUDIT", "PROTECTED_SENTINEL_DO_NOT_RETURN", str(fixtures), "guardian-integration"):
        check("audit excludes " + ("fixture paths" if secret == str(fixtures) else "test payload/ID"), secret not in audit)
    records = [json.loads(line) for line in audit.splitlines()]
    check("audit records all exercised decisions", len(records) >= 13 and {"allow", "approve", "block"} <= {r["action"] for r in records})
    summary = {"mode": options.mode, "expected": options.expect, "checks": len(checks), "approval_elapsed_seconds": round(elapsed, 3), "run_directory": str(run), "loaded": loaded, "approval_result": result}
    (run / "result.json").write_text(json.dumps(summary, indent=2))
    print("RESULT:", json.dumps(summary), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
