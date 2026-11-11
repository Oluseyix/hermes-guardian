"""Small, deliberately incomplete policy language. Unknown syntax is not safe syntax."""
from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import os
from pathlib import Path
import re
import shlex
import stat

RANK = {"allow": 0, "approve": 1, "block": 2}
FILES = {"read_file": "read", "write_file": "write", "patch": "write"}
KNOWN = {*FILES, "terminal"}
DEFAULT = {
    "default_action": "block",
    "rules": [
        {"tool": "read_file", "action": "allow"},
        {"tool": "write_file", "action": "approve"},
        {"tool": "patch", "action": "approve"},
        {"tool": "terminal", "action": "approve"},
    ],
    "protected_paths": [
        {"path": "~/.ssh", "action": "block"},
        {"path": "~/.aws", "action": "block"},
        {"path": "~/.hermes", "action": "block"},
    ],
}


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    rule: str = "builtin"


def _path(value: object, *, trusted: bool = False) -> Path:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ValueError("invalid path")
    if any(ord(c) < 32 for c in value) or any(c in value for c in "$`*?[]{}\\"):
        raise ValueError("ambiguous path")
    if trusted:
        value = os.path.expanduser(value)
    # The hook has no authoritative terminal cwd, home or backend identity.
    if not value.startswith("/") or value.startswith("//") or "~" in value:
        raise ValueError("absolute local path required")
    return Path(value)


def _variants(path: Path) -> tuple[Path, Path]:
    # Retain lexical identity as well as the current symlink target.
    # Python 3.13's non-strict resolve silently tolerates symlink loops. Walk
    # components explicitly, allowing missing future files but rejecting loops
    # and permission errors; process '..' AFTER expanding preceding symlinks.
    pending = deque(path.parts[1:])
    resolved = Path("/")
    links = 0
    while pending:
        component = pending.popleft()
        if component == "..":
            resolved = resolved.parent
            continue
        candidate = resolved / component
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            resolved = candidate
            continue
        if stat.S_ISLNK(info.st_mode):
            links += 1
            if links > 40:
                raise ValueError("symlink resolution limit")
            target = Path(os.readlink(candidate))
            if target.is_absolute():
                resolved = Path("/")
                pending.extendleft(reversed(target.parts[1:]))
            else:
                pending.extendleft(reversed(target.parts))
        else:
            resolved = candidate
    return Path(os.path.abspath(path)), resolved


def _overlaps(path: Path, root: Path, *, ancestors: bool) -> bool:
    return any(p == r or r in p.parents or (ancestors and p in r.parents)
               for p in _variants(path) for r in _variants(root))


def _shell(command: object) -> tuple[str, list[Path]]:
    if not isinstance(command, str) or not command or len(command) > 16384:
        raise ValueError("invalid command")
    # Reject even inside quotes: conservative by design, not a general shell parser.
    if any(ord(c) < 32 for c in command) or any(c in command for c in ";|&><$`\\*?[]{}()!#~"):
        raise ValueError("shell syntax outside supported grammar")
    tokens = shlex.split(command, posix=True)
    if not tokens:
        raise ValueError("empty command")
    executable, *args = tokens
    if executable == "pwd" and not args:
        return "read", []
    # No wrappers, interpreters, PATH assignments, executable paths or hidden options.
    if executable not in {"cat", "rm", "touch", "mkdir", "cp", "mv"}:
        raise ValueError("unsupported executable")
    allowed = {"rm": {"-r", "-f", "-rf", "-fr"}, "mkdir": {"-p"}}
    while args and args[0].startswith("-"):
        flag = args.pop(0)
        if flag == "--":
            break
        if flag not in allowed.get(executable, set()):
            raise ValueError("unsupported option")
    if not args or len(args) > 64 or (executable in {"cp", "mv"} and len(args) != 2):
        raise ValueError("unsupported operands")
    return ("read" if executable == "cat" else "write"), [_path(a) for a in args]


class Policy:
    def __init__(self, config: object, *, mandatory_paths: tuple[Path, ...] = ()):
        if not isinstance(config, dict) or set(config) != {"default_action", "rules", "protected_paths"}:
            raise ValueError("policy requires exactly default_action, rules, protected_paths")
        self.default = self._action(config["default_action"])
        self.rules: list[tuple[str, str]] = []
        rules = config["rules"]
        if not isinstance(rules, list) or len(rules) > 256:
            raise ValueError("invalid rules")
        for rule in rules:
            if not isinstance(rule, dict) or set(rule) != {"tool", "action"}:
                raise ValueError("invalid rule")
            tool = rule["tool"]
            if not isinstance(tool, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,127}", tool):
                raise ValueError("tool must be an exact name")
            self.rules.append((tool, self._action(rule["action"])))
        roots = config["protected_paths"]
        if not isinstance(roots, list) or len(roots) > 256:
            raise ValueError("invalid protected_paths")
        self.roots: list[tuple[Path, str, str]] = []
        for i, item in enumerate(roots):
            if not isinstance(item, dict) or set(item) != {"path", "action"} or item["action"] not in ("approve", "block"):
                raise ValueError("protected paths require approve or block")
            self.roots.append((_path(item["path"], trusted=True), item["action"], f"path:{i}"))
        self.roots.extend((p, "block", "self_protection") for p in mandatory_paths)

    @staticmethod
    def _action(value: object) -> str:
        if not isinstance(value, str) or value not in RANK:
            raise ValueError("invalid action")
        return value

    def evaluate(self, tool: object, args: object) -> Decision:
        if not isinstance(tool, str) or not isinstance(args, dict):
            return Decision("block", "invalid_call")
        candidates = [Decision(action, "tool_rule", f"tool:{i}")
                      for i, (name, action) in enumerate(self.rules) if tool == name]
        if not candidates:
            candidates = [Decision(self.default, "default")]
        paths = []
        try:
            if tool == "terminal":
                if set(args) - {"command", "timeout", "background", "workdir"} or args.get("background", False) is not False:
                    raise ValueError("unsupported terminal mode")
                if "timeout" in args and (type(args["timeout"]) is not int or not 1 <= args["timeout"] <= 180):
                    raise ValueError("unsupported terminal timeout")
                _, paths = _shell(args.get("command"))
                if "workdir" in args:
                    paths.append(_path(args["workdir"]))
            elif tool in FILES:
                allowed = {
                    "read_file": {"path", "offset", "limit"},
                    "write_file": {"path", "content"},
                    "patch": {"path", "old_string", "new_string", "replace_all", "mode"},
                }[tool]
                if set(args) - allowed or (tool == "patch" and args.get("mode", "replace") != "replace"):
                    raise ValueError("unsupported file mode")
                paths = [_path(args.get("path"))]
            for path in paths:
                for root, action, rule in self.roots:
                    # Ancestor operations may recurse, replace directories or traverse links.
                    if _overlaps(path, root, ancestors=True):
                        candidates.append(Decision(action, "protected_path", rule))
        except (ValueError, OSError, RuntimeError):
            return Decision("block", "ambiguous_arguments")
        return max(candidates, key=lambda d: RANK[d.action])
