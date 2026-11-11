"""Read-only hypothetical evaluation, using the live Policy class unchanged."""
from dataclasses import asdict
from pathlib import Path
import shlex
from .policy import Policy, RANK

EXPLANATIONS = {
    'tool_rule': 'An exact tool-name rule matched; the strongest matching action wins.',
    'default': 'No exact tool rule matched; the configured default applies.',
    'protected_path': 'A protected path, descendant, ancestor or resolved symlink overlaps.',
    'ambiguous_arguments': 'Unsupported or ambiguous arguments are blocked conservatively.',
    'invalid_call': 'The hypothetical call has an invalid shape.',
}


def simulate(config, cases, *, home):
    """No handlers, audit, approvals, writes or network. Path metadata is inspected.

    home must be the intended absolute local Hermes home. Results describe only
    Guardian policy, not other host guards, audit availability or final consent.
    """
    home = Path(home)
    if not home.is_absolute():
        raise ValueError('An absolute target Hermes home is required.')
    policy = Policy(config, mandatory_paths=(home / 'plugin-data' / 'hermes-guardian',
                                            Path(__file__).resolve().parents[1], home))
    if not isinstance(cases, list) or not 1 <= len(cases) <= 128:
        raise ValueError('Provide 1–128 hypothetical cases.')
    results = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'name', 'tool', 'args', 'expected'}:
            raise ValueError('Cases require exactly name, tool, args, expected.')
        if not isinstance(case['name'], str) or not 1 <= len(case['name']) <= 120:
            raise ValueError('Invalid case name.')
        if not isinstance(case['expected'], str) or case['expected'] not in RANK:
            raise ValueError('Expected decision must be allow, approve or block.')
        decision = policy.evaluate(case['tool'], case['args'])
        results.append({'name': case['name'], 'expected': case['expected'],
                        'actual': decision.action, 'passed': case['expected'] == decision.action,
                        'decision': asdict(decision), 'explanation': EXPLANATIONS[decision.reason]})
    return results


def regression_cases(workspace, protected):
    """Deterministic templates; paths are supplied by the operator, never inferred."""
    workspace, protected = Path(workspace), Path(protected)
    if not workspace.is_absolute() or not protected.is_absolute():
        raise ValueError('Supply absolute fixture and protected paths.')
    public = str(workspace / 'public.txt')
    def case(name, tool, args, expected):
        return dict(name=name, tool=tool, args=args, expected=expected)
    return [
        case('normal read', 'read_file', {'path': public}, 'allow'),
        case('edit requires approval', 'write_file', {'path': public, 'content': 'DEMO_ONLY'}, 'approve'),
        case('deletion requires approval', 'terminal', {'command': 'rm -- ' + shlex.quote(public)}, 'approve'),
        case('GitHub push unsupported', 'terminal', {'command': 'git push origin main'}, 'block'),
        case('compound command ambiguous', 'terminal', {'command': 'pwd && pwd'}, 'block'),
        case('protected path overrides read allow', 'read_file', {'path': str(protected / 'demo.txt')}, 'block'),
        case('protected deletion overrides approval', 'terminal', {'command': 'rm -- ' + shlex.quote(str(protected / 'demo.txt'))}, 'block'),
    ]
