"""Run standalone checks and official validation when Hermes is installed."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-hermes", action="store_true")
    options = parser.parse_args()
    root = Path(__file__).resolve().parent
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=root, env=environment, check=True)
    with tempfile.TemporaryDirectory(prefix="guardian-demo-") as directory:
        subprocess.run([sys.executable, "demo.py", "--output", directory], cwd=root, env=environment, check=True)
    hermes = shutil.which("hermes")
    if hermes:
        subprocess.run([hermes, "plugins", "validate", str(root), "--install-deps"], env=environment, check=True)
    else:
        print("SKIPPED: hermes plugins validate --install-deps (Hermes is not on PATH).", flush=True)
        if options.require_hermes:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
