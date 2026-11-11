"""Reproducible policy-only demo. No tool, shell command or model is executed."""
import argparse
import json
from pathlib import Path
import tempfile

from guardian.runtime import Guardian


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Audit location outside the protected plugin source tree (default: new temporary directory)")
    options = parser.parse_args()
    root = options.output.resolve() if options.output else Path(tempfile.mkdtemp(prefix="hermes-guardian-demo-")).resolve()

    class Context:
        def get_config(self, key, default=None):
            return {
                "default_action": "block",
                "rules": [
                    {"tool": "read_file", "action": "allow"},
                    {"tool": "write_file", "action": "approve"},
                    {"tool": "terminal", "action": "approve"},
                ],
                "protected_paths": [{"path": str(root / "vault"), "action": "block"}],
            }

    guardian = Guardian(Context(), lambda: root / "audit")
    scenarios = [
        ("ordinary read", "read_file", {"path": str(root / "public.txt")}, "allow"),
        ("write requests Hermes approval", "write_file", {"path": str(root / "public.txt"), "content": "DEMO_SECRET_NOT_LOGGED"}, "approve"),
        ("protected read", "read_file", {"path": str(root / "vault" / "key")}, "block"),
        ("protected deletion", "terminal", {"command": f"rm -rf {root}/vault"}, "block"),
        ("ambiguous shell", "terminal", {"command": "cat $(printf /tmp/key)"}, "block"),
        ("unknown executor", "execute_code", {"code": "print('not executed')"}, "block"),
        ("audit self-protection", "read_file", {"path": str(root / "audit" / "audit.jsonl")}, "block"),
    ]
    for name, tool, args, expected in scenarios:
        directive = guardian.pre_tool_call(tool, args, task_id="demo")
        action = directive["action"] if directive else "allow"
        if action != expected:
            raise SystemExit(f"FAIL: {name}: expected {expected}, got {action}")
        print(f"{action.upper():7} {name}")
    audit = root / "audit" / "audit.jsonl"
    text = audit.read_text()
    assert "DEMO_SECRET_NOT_LOGGED" not in text
    for line in text.splitlines():
        json.loads(line)
    print(f"PASS: 7 scenarios; redacted decision records: {audit}")
    print("Approval directives only; a real Hermes approval UI was not exercised.")


if __name__ == "__main__":
    main()
