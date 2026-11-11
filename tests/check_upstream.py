"""Optional source-only compatibility checks; NOT the complete Hermes validator.

Run: python3 tests/check_upstream.py /path/to/trusted/hermes-source
Uses the upstream capability probe verbatim and its static lint functions.
"""
import ast
import json
from pathlib import Path
import subprocess
import sys


def main():
    source = Path(sys.argv[1]).resolve()
    plugin = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(source))
    from hermes_cli.plugin_validate_core_override import core_override_findings
    from hermes_cli.plugin_validate_private_imports import private_import_findings, private_attribute_findings

    for name, check in (("core overrides", core_override_findings), ("private imports", private_import_findings), ("private attributes", private_attribute_findings)):
        findings = check(plugin)
        print(f"{name}: {json.dumps(findings)}")
        if findings:
            return 1
    tree = ast.parse((source / "hermes_cli/plugin_validate.py").read_text())
    script = next(ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_PROBE_SCRIPT" for t in node.targets))
    # Only registration/get_config are used by this plugin. The upstream probe
    # defines these methods itself; no host runtime is installed or stubbed here.
    options = {"context_methods": ["get_config", "register_hook"], "kind": "standalone"}
    result = subprocess.run([sys.executable, "-c", script, str(plugin), "PROBE:", json.dumps(options)], text=True, capture_output=True, check=True)
    print(result.stdout.strip())
    recorded = json.loads(next(line[6:] for line in result.stdout.splitlines() if line.startswith("PROBE:")))
    if recorded.get("hooks") != ["pre_tool_call"] or recorded.get("tools") or recorded.get("middleware") or recorded.get("error"):
        return 1
    print("PASS: source-only lint and registration probe; full Hermes validation not performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
