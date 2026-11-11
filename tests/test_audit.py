from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import multiprocessing
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from guardian.audit import Audit, _open_audit
from guardian.policy import Decision


def _process_writer(directory, index, start, ready, results):
    audit = Audit(Path(directory))
    ready.put(index)
    if not start.wait(10):
        results.put((0, "start timeout"))
        return
    written = 0
    try:
        for item in range(20):
            try:
                audit.append(f"{index}:{item}", "read_file", Decision("allow", "tool_rule", "tool:0"))
                written += 1
            except BlockingIOError:
                pass
        results.put((written, None))
    except Exception as exc:
        results.put((written, type(exc).__name__))


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.directory = self.root / "data"
        self.audit = Audit(self.directory)
        self.decision = Decision("allow", "tool_rule", "tool:0")

    def append(self, event="event"):
        self.audit.append(event, "read_file", self.decision)

    def test_persistence_across_instances(self):
        self.append("one")
        Audit(self.directory).append("two", "terminal", self.decision)
        records = [json.loads(line) for line in (self.directory / "audit.jsonl").read_text().splitlines()]
        self.assertEqual([r["event_id"] for r in records], ["one", "two"])
        self.assertEqual(records[0]["event"], "policy_decision")

    def test_private_permissions(self):
        self.append()
        self.assertEqual(stat.S_IMODE((self.directory / "audit.jsonl").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode), 0o700)

    def test_existing_file_permissions_narrowed(self):
        self.append()
        (self.directory / "audit.jsonl").chmod(0o644)
        self.append()
        self.assertEqual(stat.S_IMODE((self.directory / "audit.jsonl").stat().st_mode), 0o600)

    def test_symlink_file_rejected(self):
        self.directory.mkdir()
        target = self.root / "target"
        target.write_text("untouched")
        (self.directory / "audit.jsonl").symlink_to(target)
        with self.assertRaises(OSError):
            self.append()
        self.assertEqual(target.read_text(), "untouched")

    def test_symlink_directory_rejected(self):
        target = self.root / "target"
        target.mkdir()
        self.directory.symlink_to(target, target_is_directory=True)
        with self.assertRaises(OSError):
            self.append()
        self.assertFalse((target / "audit.jsonl").exists())

    def test_hardlink_file_rejected(self):
        self.append()
        os.link(self.directory / "audit.jsonl", self.root / "alias")
        with self.assertRaises(OSError):
            self.append()

    def test_capacity_failure_retains_records(self):
        self.append()
        before = (self.directory / "audit.jsonl").read_bytes()
        with self.assertRaises(OSError):
            Audit(self.directory, max_bytes=len(before)).append("overflow", "terminal", self.decision)
        self.assertEqual((self.directory / "audit.jsonl").read_bytes(), before)

    def test_lock_contention_fails_promptly(self):
        self.append()
        with (self.directory / "audit.jsonl").open("rb") as file:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.append()

    def test_concurrent_records_not_interleaved(self):
        def attempt(i):
            try:
                self.append(str(i))
                return True
            except BlockingIOError:
                return False  # Runtime blocks these calls, by design.
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(80)))
        records = [json.loads(line) for line in (self.directory / "audit.jsonl").read_text().splitlines()]
        self.assertEqual(len(records), sum(results))
        self.assertEqual(len({r["event_id"] for r in records}), len(records))

    def test_process_records_not_interleaved(self):
        context = multiprocessing.get_context("spawn")
        start, ready, results = context.Event(), context.Queue(), context.Queue()
        processes = [context.Process(target=_process_writer, args=(str(self.directory), i, start, ready, results)) for i in range(4)]
        try:
            for process in processes:
                process.start()
            for _ in processes:
                ready.get(timeout=10)
            start.set()
            outcomes = [results.get(timeout=10) for _ in processes]
            for process in processes:
                process.join(timeout=10)
                self.assertEqual(process.exitcode, 0)
            self.assertTrue(all(error is None for _, error in outcomes), outcomes)
            records = [json.loads(line) for line in (self.directory / "audit.jsonl").read_text().splitlines()]
            self.assertEqual(len(records), sum(count for count, _ in outcomes))
            self.assertEqual(len({r["event_id"] for r in records}), len(records))
        finally:
            for process in processes:
                if process.is_alive():
                    process.kill()
                    process.join()
            ready.close()
            results.close()

    def test_incomplete_record_blocks_future_writes(self):
        self.directory.mkdir()
        file = self.directory / "audit.jsonl"
        file.write_text('{"partial":')
        with self.assertRaises(OSError):
            self.append()
        self.assertEqual(file.read_text(), '{"partial":')

    def test_partial_write_completed(self):
        original = os.write
        with patch("guardian.audit.os.write", side_effect=lambda fd, data: original(fd, data[:7])):
            self.append()
        json.loads((self.directory / "audit.jsonl").read_text())

    def test_zero_write_fails(self):
        with patch("guardian.audit.os.write", return_value=0):
            with self.assertRaises(OSError):
                self.append()

    def test_first_creation_is_exclusive(self):
        original = os.open
        with patch("guardian.audit.os.open", wraps=original) as opened:
            self.append()
        creates = [call for call in opened.call_args_list if call.args[1] & os.O_CREAT]
        self.assertEqual(len(creates), 1)
        self.assertTrue(creates[0].args[1] & os.O_EXCL)

    def test_losing_creator_opens_existing_file_without_creation(self):
        with patch("guardian.audit.os.open", side_effect=[FileNotFoundError(), FileExistsError(), 123]) as opened:
            self.assertEqual(_open_audit(42), 123)
        self.assertFalse(opened.call_args_list[-1].args[1] & os.O_CREAT)
        self.assertTrue(opened.call_args_list[-1].args[1] & os.O_NOFOLLOW)

    def test_concurrent_delete_is_not_retried(self):
        with patch("guardian.audit.os.open", side_effect=[FileNotFoundError(), FileExistsError(), FileNotFoundError()]) as opened:
            with self.assertRaises(FileNotFoundError):
                _open_audit(42)
        self.assertEqual(opened.call_count, 3)

    def test_sync_failure_propagates(self):
        with patch("guardian.audit.os.fsync", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.append()


if __name__ == "__main__":
    unittest.main()
