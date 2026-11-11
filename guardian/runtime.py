"""Host adapter: fail closed within the callback, leave approval to Hermes."""
from pathlib import Path
from uuid import uuid4

from .audit import Audit
from .policy import DEFAULT, Decision, Policy


class Guardian:
    def __init__(self, ctx, data_dir):
        self.ctx = ctx
        self.data_dir = data_dir

    def pre_tool_call(self, tool_name, args, task_id="", **kwargs):
        try:
            return self._evaluate(tool_name, args)
        except Exception:
            return {"action": "block", "message": "Guardian blocked this call: internal failure."}

    def _evaluate(self, tool_name, args):
        event_id = uuid4().hex
        directory = None
        try:
            directory = Path(self.data_dir())
            protected = [directory, Path(__file__).resolve().parents[1]]
            # The documented storage layout identifies the active profile's
            # control directory, including a custom HERMES_HOME.
            if directory.parent.name == "plugin-data":
                protected.append(directory.parent.parent)
            policy = Policy(self.ctx.get_config("policy", DEFAULT), mandatory_paths=tuple(protected))
            decision = policy.evaluate(tool_name, args)
        except Exception:
            # Keep error redaction and blocking independent of host exception
            # handling. Re-evaluate each call so correcting config recovers.
            decision = Decision("block", "policy_unavailable")
        try:
            if directory is None:
                directory = Path(self.data_dir())
            Audit(directory).append(event_id, tool_name, decision)
        except Exception:
            return {"action": "block", "message": "Guardian blocked this call: audit unavailable. Repair local audit storage before retrying."}
        if decision.action == "allow":
            return None
        return {
            "action": decision.action,
            "message": f"Guardian: {decision.reason} ({decision.rule}); event {event_id}. Inspect the original tool call before approving.",
            # Unique per invocation: a saved approval cannot authorize a different
            # path/payload later. No secret-bearing input is put into the key.
            "rule_key": f"hermes-guardian:{event_id}",
        }
