"""Exercise real Hermes prompts with scripted PTY answers on disposable fixtures.

Run using the installed Hermes Python, --source SOURCE --workspace OUTPUT.
No API/model credentials are needed. This is a developer test, not an approval
transport or production auto-approval feature.
"""
import argparse
import errno
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import time


def pty_case(command, answer):
    master, slave = pty.openpty()
    process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    output = bytearray()
    sent = False
    saw_prompt = False
    deadline = time.monotonic() + 60
    try:
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError("host integration PTY exceeded 60 seconds")
            if select.select([master], [], [], 0.1)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
                if b"Choice [o/s/a/D]:" in output:
                    saw_prompt = True
                    if answer is not None and not sent:
                        os.write(master, answer.encode() + b"\n")
                        sent = True
            elif process.poll() is not None:
                break
        code = process.wait(timeout=5)
    finally:
        os.close(master)
        if process.poll() is None:
            process.kill()
            process.wait()
    if not saw_prompt:
        raise AssertionError("actual English Hermes approval prompt was not displayed: " + output.decode(errors="replace"))
    return code, output.decode(errors="replace")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    options = parser.parse_args()
    workspace = options.workspace.resolve()
    logs = workspace / "matrix-logs"
    logs.mkdir(parents=True, exist_ok=True)
    results = []
    for mode, expected, answer in (("unattended", "deny", None), ("cron", "deny", None),
                                   ("single-query", "deny", None), ("approvals-off", "allow", None),
                                   ("interactive", "allow", "o"), ("interactive", "deny", "d"),
                                   ("interactive", "timeout", None)):
        command = [sys.executable, str(Path(__file__).with_name("hermes_integration.py")),
                   "--source", str(options.source.resolve()), "--workspace", str(workspace),
                   "--mode", mode, "--expect", expected]
        if mode == "interactive":
            code, output = pty_case(command, answer)
        else:
            process = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            code, output = process.returncode, process.stdout
        log = logs / f"{mode}-{expected}.log"
        log.write_text(output)
        if code:
            print(output)
            raise SystemExit(f"FAILED ({code}): {log}")
        summary = json.loads(next(line[8:] for line in output.splitlines() if line.startswith("RESULT: ")))
        results.append(summary)
        print(f"PASS {mode}/{expected}: {summary['checks']} checks; approval {summary['approval_elapsed_seconds']}s", flush=True)
    (logs / "summary.json").write_text(json.dumps(results, indent=2))
    print(f"PASS: {len(results)} real-runtime scenarios, {sum(r['checks'] for r in results)} checks. Logs: {logs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
