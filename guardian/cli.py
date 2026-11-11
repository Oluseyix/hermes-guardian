"""Terminal operator interface. No activation command is exposed to agent tools."""
import argparse
import json
from pathlib import Path
import sys
from .activation import ActivationError
from .builder import DEFAULT, RECIPE, check_proposal, digest, generate_model, offline, review
from .lab import regression_cases, simulate


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON keys are not accepted.')
            result[key] = value
        return result
    with Path(path).open('rb') as stream:
        data = stream.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('JSON input exceeds 1 MiB.')
    return json.loads(data, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON number.')))


def render(value):
    # JSON escaping also keeps untrusted names/model text from issuing terminal controls.
    print(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False))


def confirm(prompt, token):
    if not sys.stdin.isatty():
        raise ValueError('An interactive operator terminal is required; there is no --yes bypass.')
    print(prompt + '\nType exactly: ' + token, flush=True)
    if input('Confirmation: ') != token:
        raise ValueError('Not confirmed; no change saved.')
    return token


def setup(parser):
    sub = parser.add_subparsers(dest='guardian_action', required=True)
    describe = sub.add_parser('propose', help='Describe permissions; generate an untrusted proposal only.')
    describe.add_argument('instructions')
    describe.add_argument('--model', action='store_true', help='Explicitly send instructions and policy paths to the current Hermes model; provider costs may apply.')
    describe.add_argument('--output', type=Path, help='Save only after terminal confirmation; never overwrite.')
    inspect = sub.add_parser('review', help='Review a proposal against the current effective policy.')
    inspect.add_argument('proposal', type=Path)
    lab = sub.add_parser('simulate', help='Read-only Policy Lab; no tool execution or approval.')
    lab.add_argument('--proposal', type=Path)
    lab.add_argument('--policy', type=Path)
    lab.add_argument('--home', required=True, type=Path, help='Absolute intended Hermes home for mandatory protections.')
    lab.add_argument('--cases', type=Path)
    lab.add_argument('--workspace', type=Path)
    lab.add_argument('--protected', type=Path)
    apply = sub.add_parser('activate', help='Operator-only confirmed activation, atomic host save and backup.')
    apply.add_argument('proposal', type=Path)


def run(args, ctx=None):
    baseline = ctx.get_config('policy', DEFAULT) if ctx else DEFAULT
    action = args.guardian_action
    if action == 'propose':
        if args.model:
            if ctx is None:
                raise ValueError('Model generation requires hermes guardian propose --model.')
            print('Sending instructions and baseline policy paths to the configured Hermes provider. No credentials are read by Guardian.', file=sys.stderr)
            value = generate_model(ctx, args.instructions)
        else:
            value = offline(args.instructions, baseline)
        render(review(value, baseline))
        if args.output:
            confirm('Save this untrusted proposal (not activation)?', 'SAVE ' + digest(value))
            # Exclusive creation avoids silent overwrites; only operator-confirmed saves.
            import os
            fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
        return 0
    if action in ('review', 'activate'):
        value = read_json(args.proposal)
        render(review(value, baseline))
        if action == 'activate':
            if ctx is None:
                raise ValueError('Activation requires hermes guardian activate in the intended profile.')
            checked = check_proposal(value, baseline)
            if checked['questions']:
                raise ValueError('Resolve clarification questions before activation.')
            token = confirm('Stop other config editors. Review all changes and limitations before activating.', 'ACTIVATE ' + digest(checked))
            from .activation import activate
            from plugins.plugin_storage import plugin_data_dir
            render(activate(ctx, checked, confirmation=token, storage=lambda: plugin_data_dir('hermes-guardian')))
        return 0
    if args.proposal and args.policy:
        raise ValueError('Choose --proposal or --policy, not both.')
    policy = check_proposal(read_json(args.proposal), baseline)['policy'] if args.proposal else read_json(args.policy) if args.policy else baseline
    if args.cases:
        if args.workspace or args.protected:
            raise ValueError('Choose a cases file or regression template paths.')
        cases = read_json(args.cases)
    else:
        if not args.workspace or not args.protected:
            raise ValueError('Supply --cases, or both --workspace and --protected. No paths are guessed.')
        cases = regression_cases(args.workspace, args.protected)
    results = simulate(policy, cases, home=args.home)
    render({'scope': 'Policy decisions only; local path metadata read. No tools, writes, network, audits or approvals.', 'results': results})
    return 0 if all(r['passed'] for r in results) else 1


def handle(args, ctx=None):
    try:
        code = run(args, ctx)
    except (ValueError, ActivationError) as error:
        print('Guardian: ' + json.dumps(str(error), ensure_ascii=True), file=sys.stderr)
        raise SystemExit(2)
    except (Exception, KeyboardInterrupt):
        # Detailed ValueErrors are safe to display as escaped strings, but host
        # provider errors may contain credentials. Keep all failures payload-free.
        print('Guardian command refused or failed; nothing was approved automatically. Check inputs, clarification questions and profile. If activation reports storage trouble, inspect its backup before restarting.', file=sys.stderr)
        raise SystemExit(2)
    if code:
        raise SystemExit(code)


def main():
    parser = argparse.ArgumentParser(description='Hermes Guardian Policy Lab — offline proposals and read-only simulation')
    setup(parser)
    handle(parser.parse_args())
