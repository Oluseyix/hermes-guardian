"""Offline operator entry point. Use `python3 -B guardian_lab.py --help`."""
import sys
sys.dont_write_bytecode = True
from guardian.cli import main

if __name__ == '__main__':
    main()
