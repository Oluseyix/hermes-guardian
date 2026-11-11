"""80-second real Hermes dispatcher demo. Run with Hermes 0.23.1's Python.
Development harness only: imports host internals, never imported by Guardian.
Answer the real approval prompt with o (Once) before the 45-second cue.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix='guardian-live-', dir='/tmp')).resolve()
    home, fixtures = root / 'home', root / 'fixtures'
    (home / 'plugins').mkdir(parents=True)
    (fixtures / 'vault').mkdir(parents=True)
    public = fixtures / 'public.txt'
    public.write_text('Hello from a harmless demo fixture!')
    protected = fixtures / 'vault' / 'protected.txt'
    protected.write_text('DEMO_ONLY')
    (home / 'plugins' / 'hermes-guardian').symlink_to(Path(__file__).resolve().parents[1], target_is_directory=True)
    policy = {'default_action': 'block', 'rules': [
        {'tool': 'read_file', 'action': 'allow'},
        {'tool': 'write_file', 'action': 'approve'}],
        'protected_paths': [{'path': str(protected.parent), 'action': 'block'}]}
    (home / 'config.yaml').write_text(json.dumps({
        'cli': {'expose_on_path': False},
        'plugins': {'enabled': ['hermes-guardian'], 'entries': {'hermes-guardian': {'settings': {'policy': policy}}}},
        'approvals': {'mode': 'manual', 'timeout': 20, 'unattended_mode': 'deny', 'cron_mode': 'deny', 'single_query_mode': 'deny'}}))
    os.environ['HERMES_HOME'] = str(home)
    for key in ('HERMES_CRON_SESSION', 'HERMES_SINGLE_QUERY_SESSION', 'HERMES_EXEC_ASK', 'HERMES_GATEWAY_SESSION', 'HERMES_YOLO'):
        os.environ.pop(key, None)
    os.environ['HERMES_INTERACTIVE'] = '1'
    sys.path.insert(0, str(args.source.resolve()))
    from hermes_cli.plugins import discover_plugins, get_plugin_manager
    discover_plugins()
    loaded = next(p for p in get_plugin_manager().list_plugins() if p['name'] == 'hermes-guardian')
    assert loaded['enabled'] and loaded['hooks'] == 1 and not loaded['error'], loaded
    from model_tools import handle_function_call
    started = time.monotonic()

    def cue(seconds, label):
        time.sleep(max(0, started + seconds - time.monotonic()))
        print('\n' + label, flush=True)

    def call(tool, arguments):
        result = handle_function_call(tool, arguments, task_id='demo-only', session_id='demo-only')
        print(result, flush=True)
        return result

    print('LIVE: real Hermes dispatcher; Guardian loaded with one hook. No model calls.', flush=True)
    print('Disposable fixtures:', root, flush=True)
    cue(10, '1. ALLOW: read harmless public fixture')
    assert 'Hello from a harmless demo fixture!' in call('read_file', {'path': str(public)})
    cue(25, '2. APPROVE: write harmless new file. Choose o / Once in the host prompt.')
    destination = fixtures / 'approved.txt'
    call('write_file', {'path': str(destination), 'content': 'APPROVED_DEMO'})
    assert destination.exists() and destination.read_text() == 'APPROVED_DEMO', 'Approval was not granted; stop and rerun, do not claim success.'
    cue(45, '3. BLOCK: attempt to overwrite protected disposable file')
    result = call('write_file', {'path': str(protected), 'content': 'MUST_NOT_WRITE'})
    assert 'Guardian' in result and protected.read_text() == 'DEMO_ONLY'
    print('Operator verification: protected fixture unchanged.', flush=True)
    cue(60, '4. AUDIT: operator reads actual persisted decision records')
    audit = (home / 'plugin-data' / 'hermes-guardian' / 'audit.jsonl').read_text()
    records = [json.loads(line) for line in audit.splitlines()]
    assert [r['action'] for r in records] == ['allow', 'approve', 'block']
    assert all(s not in audit for s in (str(fixtures), 'APPROVED_DEMO', 'DEMO_ONLY', 'demo-only'))
    print(audit, flush=True)
    cue(80, 'DONE: policy decisions, not proof of execution or a sandbox.')
    print(f'Elapsed: {time.monotonic() - started:.2f} seconds. Fixtures retained at {root}', flush=True)


if __name__ == '__main__':
    main()
