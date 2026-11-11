"""Untrusted proposals only. No persistence or enforcement in this module."""
import copy
import hashlib
import json
from .policy import DEFAULT, KNOWN, Policy, RANK

GAPS = [
    'Rules are tool-wide, not project-scoped. File edits cannot be allowed only inside coding projects.',
    'Terminal approval covers the supported grammar, not deletion alone. Git push, gh, wrappers and scripts are blocked as unsupported.',
    'Unknown tools default to block. Explicitly allowed unknown tools would have no argument adapter; this builder refuses them.',
    'Simulation checks policy only, including current local path metadata; it does not test audit availability, other plugins or final host approval.',
    'Host automatic approval can bypass approve decisions. This is not a sandbox; remote namespaces, aliases, races and later argument rewriting are not secured.',
]
RECIPE = 'Ask before edits and deletions; block GitHub pushes.'
EXAMPLE = 'Hermes can edit my coding projects, but must ask before deleting files or pushing code to GitHub.'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_candidate(policy, baseline):
    Policy(baseline)
    Policy(policy)
    if policy['default_action'] != 'block':
        raise ValueError('Builder proposals require default_action block.')
    if any(r['tool'] not in KNOWN for r in policy['rules']):
        raise ValueError('Builder proposals may only name recognized adapters.')
    # Do not remove, rename or weaken an existing protected-path rule. No paths
    # invented by a model: additional roots must first be configured by operator.
    old = {r['path'] for r in baseline['protected_paths']}
    if any(r['path'] not in old for r in policy['protected_paths']):
        raise ValueError('Generated paths must already exist in the baseline policy.')
    for before in baseline['protected_paths']:
        if not any(after['path'] == before['path'] and RANK[after['action']] >= RANK[before['action']]
                   for after in policy['protected_paths']):
            raise ValueError('A proposal may not remove or weaken protected paths.')
    return copy.deepcopy(policy)


def proposal(policy, baseline, questions, origin):
    validate_candidate(policy, baseline)
    if not isinstance(questions, list) or len(questions) > 8 or any(
            not isinstance(q, str) or not 1 <= len(q) <= 512 for q in questions):
        raise ValueError('Malformed clarification questions.')
    if origin not in ('offline-template', 'hermes-model'):
        raise ValueError('Invalid proposal origin.')
    return {'schema': 1, 'base_digest': digest(baseline), 'policy': copy.deepcopy(policy),
            'questions': questions[:], 'origin': origin}


def check_proposal(value, baseline):
    if not isinstance(value, dict) or set(value) != {'schema', 'base_digest', 'policy', 'questions', 'origin'} or type(value['schema']) is not int or value['schema'] != 1:
        raise ValueError('Invalid proposal document.')
    if value['base_digest'] != digest(baseline):
        raise ValueError('Policy changed since proposal generation; regenerate and review.')
    return proposal(value['policy'], baseline, value['questions'], value['origin'])


def offline(instructions, baseline=DEFAULT):
    if not isinstance(instructions, str) or not instructions.strip() or len(instructions) > 4000:
        raise ValueError('Provide 1–4000 characters of instructions.')
    Policy(baseline)
    # Deliberately exact templates, not keyword intent guessing. Unknown prose
    # produces questions and can never be activated until rewritten.
    known = instructions.strip().casefold() == RECIPE.casefold()
    desired = {'read_file': 'allow', 'write_file': 'approve', 'patch': 'approve', 'terminal': 'approve'}
    rules = []
    for tool, wanted in desired.items():
        existing = [r['action'] for r in baseline['rules'] if r['tool'] == tool]
        current = max(existing, key=RANK.get) if existing else baseline['default_action']
        rules.append({'tool': tool, 'action': max((wanted, current), key=RANK.get)})
    policy = {'default_action': 'block', 'rules': rules, 'protected_paths': copy.deepcopy(baseline['protected_paths'])}
    questions = [] if known else [
        'Do you accept approval-gated edits everywhere and blocking GitHub pushes? Project-only edits and push approval are unsupported.',
        'To explicitly choose that conservative template, describe: ' + RECIPE,
    ]
    return proposal(policy, baseline, questions, 'offline-template')


def model_schema():
    action = {'type': 'string', 'enum': list(RANK)}
    def obj(properties):
        return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
    return obj({'policy': obj({'default_action': {'const': 'block', 'type': 'string'},
        'rules': {'type': 'array', 'maxItems': 256, 'items': obj({'tool': {'type': 'string', 'enum': sorted(KNOWN)}, 'action': action})},
        'protected_paths': {'type': 'array', 'maxItems': 256, 'items': obj({'path': {'type': 'string'}, 'action': {'type': 'string', 'enum': ['approve', 'block']}})}}),
        'questions': {'type': 'array', 'maxItems': 8, 'items': {'type': 'string', 'minLength': 1, 'maxLength': 512}}})


def from_model(value, baseline):
    if not isinstance(value, dict) or set(value) != {'policy', 'questions'}:
        raise ValueError('Model did not return the required structured object.')
    return proposal(value['policy'], baseline, value['questions'], 'hermes-model')


def generate_model(ctx, instructions):
    if not isinstance(instructions, str) or not 1 <= len(instructions.strip()) <= 4000:
        raise ValueError('Provide 1–4000 characters of instructions.')
    baseline = copy.deepcopy(ctx.get_config('policy', DEFAULT))
    Policy(baseline)
    try:
        result = ctx.llm.complete_structured(
            instructions=('Propose Guardian policy; never execute or activate anything. Return exactly the supplied schema. '
                          'Preserve all baseline protected paths and never invent paths or tool names. '
                          'Ask focused questions for ambiguous or unsupported requests; do not pretend gaps are enforced. '
                          + ' '.join(GAPS)),
            input=[{'type': 'text', 'text': json.dumps({'instructions': instructions, 'baseline_policy': baseline})}],
            json_schema=model_schema(), schema_name='guardian_policy', purpose='guardian.policy-proposal',
            temperature=0.0, max_tokens=2000, timeout=30)
    except Exception:
        raise ValueError('Hermes model generation unavailable or refused; use the offline template. No policy was saved.') from None
    # Validate locally even if optional host JSON-schema validation is absent.
    return from_model(result.parsed, baseline)


def review(value, baseline):
    checked = check_proposal(value, baseline)
    changes = []
    for tool in sorted(KNOWN):
        def action(policy):
            matches = [r['action'] for r in policy['rules'] if r['tool'] == tool]
            return max(matches, key=RANK.get) if matches else policy['default_action']
        before, after = action(baseline), action(checked['policy'])
        if before != after:
            changes.append({'tool': tool, 'before': before, 'after': after, 'weakens': RANK[after] < RANK[before]})
    return {'proposal': checked, 'digest': digest(checked), 'gaps': GAPS, 'changes': changes,
            'ready_for_review': not checked['questions']}
