"""Durable JSONL, restrictive permissions, cross-process locking, no raw payloads."""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import stat

from .policy import Decision, KNOWN


def _open_audit(directory_fd: int) -> int:
    flags = os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        return os.open("audit.jsonl", flags, dir_fd=directory_fd)
    except FileNotFoundError:
        # Concurrent non-exclusive O_CREAT opens can spuriously fail with ENOENT
        # on macOS. Elect one creator atomically, then open the winning file.
        # No retry on deletion/symlink races: those still fail closed.
        try:
            return os.open("audit.jsonl", flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory_fd)
        except FileExistsError:
            return os.open("audit.jsonl", flags, dir_fd=directory_fd)


class Audit:
    def __init__(self, directory: Path, *, max_bytes: int = 16 * 1024 * 1024):
        self.directory = directory
        self.max_bytes = max_bytes

    def append(self, event_id: str, tool: object, decision: Decision) -> None:
        # Redaction by omission: even arbitrary tool names, task IDs and exception
        # messages can carry secrets. Never persist them or argument fingerprints.
        record = {
            "schema": 1, "event_id": event_id,
            "time": datetime.now(timezone.utc).isoformat(),
            "event": "policy_decision", "action": decision.action,
            "reason": decision.reason, "rule": decision.rule,
            "tool": tool if isinstance(tool, str) and tool in KNOWN else "[REDACTED]",
            "arguments": "[REDACTED]", "task_id": "[REDACTED]",
        }
        payload = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Do not follow a swapped data directory or audit-file symlink.
        directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fd = _open_audit(directory_fd)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
                    raise OSError("unsafe audit file")
                os.fchmod(fd, 0o600)
                # Never wait indefinitely inside the host's bounded hook worker.
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                size = os.fstat(fd).st_size
                if size and os.pread(fd, 1, size - 1) != b"\n":
                    raise OSError("incomplete audit record; operator repair required")
                if size + len(payload) > self.max_bytes:
                    raise OSError("audit capacity reached")
                view = memoryview(payload)
                while view:
                    written = os.write(fd, view)
                    if written <= 0:
                        raise OSError("short audit write")
                    view = view[written:]
                os.fsync(fd)
                os.fsync(directory_fd)
            finally:
                os.close(fd)
        finally:
            os.close(directory_fd)
