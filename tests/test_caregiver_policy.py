import copy
import tempfile
import unittest
from pathlib import Path

from guardian.policy import DEFAULT, Policy


class CaregiverPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.root = Path(self.tmp.name).resolve()
        self.records = self.root / "confidential_records"
        self.records.mkdir()

        self.schedule = self.root / "team_schedule.txt"
        self.record = self.records / "fictional_patient.txt"

        config = copy.deepcopy(DEFAULT)
        config["protected_paths"] = [
            {"path": str(self.records), "action": "block"}
        ]
        self.policy = Policy(config)

    def action(self, tool, **args):
        return self.policy.evaluate(tool, args).action

    def test_confidential_record_read_blocked(self):
        self.assertEqual(
            self.action("read_file", path=str(self.record)), "block"
        )

    def test_confidential_record_change_blocked(self):
        self.assertEqual(
            self.action("write_file", path=str(self.record), content="test"),
            "block"
        )

    def test_team_schedule_change_requires_approval(self):
        self.assertEqual(
            self.action("write_file", path=str(self.schedule), content="test"),
            "approve"
        )

    def test_unknown_caregiver_integration_blocked(self):
        self.assertEqual(
            self.action("send_patient_record", recipient="example"),
            "block"
        )

    def test_symlink_cannot_expose_confidential_records(self):
        alias = self.root / "shared_records"
        alias.symlink_to(self.records, target_is_directory=True)

        self.assertEqual(
            self.action("read_file", path=str(alias / "fictional_patient.txt")),
            "block"
        )


if __name__ == "__main__":
    unittest.main()
