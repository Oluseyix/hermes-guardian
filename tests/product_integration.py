"""Real Hermes 0.23.1 Policy Lab/activation integration and optional 80s demo.
No core mocks; developer-only imports below. --demo requires a real terminal.
"""
import argparse
import copy
import json
import os
import pty
import select
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from guardian.builder import DEFAULT, EXAMPLE, RECIPE, digest, offline, review
from guardian.lab import regression_cases, simulate
from guardian.activation import activate
from guardian.cli import confirm


def interactive_cli(executable, arguments, answer):
    master, slave = pty.openpty()
    child = subprocess.Popen([str(executable), 'guardian', *arguments], stdin=slave, stdout=slave, stderr=slave, env=os.environ)
    os.close(slave)
    output = b''; sent = False; deadline = time.monotonic() + 30
    try:
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.2)[0]:
                try: chunk = os.read(master, 65536)
                except OSError: break
                if not chunk: break
                output += chunk
                if b'Confirmation:' in output and not sent:
                    os.write(master, (answer + '\n').encode()); sent = True
            if child.poll() is not None: break
        if child.poll() is None: child.terminate()
        code = child.wait(timeout=5)
    finally:
        os.close(master)
        if child.poll() is None: child.kill(); child.wait()
    return code, sent, output.decode(errors='replace')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix='guardian-product-', dir='/tmp')).resolve()
    home, work = root/'home', root/'work'
    vault = work/'vault'
    vault.mkdir(parents=True)
    (home/'plugins').mkdir(parents=True)
    (home/'plugins/hermes-guardian').symlink_to(Path(__file__).resolve().parents[1], target_is_directory=True)
    (work/'public.txt').write_text('HELLO_POLICY_LAB')
    (vault/'demo.txt').write_text('PROTECTED_DEMO_ONLY')
    baseline = copy.deepcopy(DEFAULT)
    baseline['protected_paths'] = [{'path': str(vault), 'action': 'block'}]
    legacy = copy.deepcopy(baseline)
    legacy['rules'][0]['action'] = 'block'
    config = {'cli': {'expose_on_path': False}, 'terminal': {'backend': 'local'},
              'display': {'compact': False},
              'plugins': {'enabled': ['hermes-guardian'], 'entries': {'hermes-guardian': {
                  'config': {'policy': legacy, 'legacy_marker': 'PRESERVE'},
                  'settings': {'policy': baseline, 'operator_marker': 'PRESERVE'}}}},
              'approvals': {'mode': 'manual', 'timeout': 15, 'unattended_mode': 'deny', 'cron_mode': 'deny', 'single_query_mode': 'deny'}}
    (home/'config.yaml').write_text(json.dumps(config))
    os.environ['HERMES_HOME'] = str(home)
    for key in ('HERMES_INTERACTIVE','HERMES_CRON_SESSION','HERMES_SINGLE_QUERY_SESSION','HERMES_EXEC_ASK','HERMES_GATEWAY_SESSION','HERMES_YOLO'):
        os.environ.pop(key,None)
    if args.demo:os.environ['HERMES_INTERACTIVE']='1'
    sys.path.insert(0,str(args.source.resolve()))
    from hermes_cli.plugins import discover_plugins, get_plugin_manager
    from hermes_cli.plugins_context import PluginContext
    from model_tools import handle_function_call
    from plugins.plugin_storage import plugin_data_dir
    import hermes_yaml
    discover_plugins()
    manager = get_plugin_manager()
    loaded = next(p for p in manager.list_plugins() if p['name']=='hermes-guardian')
    assert loaded['enabled'] and loaded['hooks']==1 and not loaded['error'], loaded
    ctx = PluginContext(manager._plugins['hermes-guardian'].manifest, manager)
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(name)
        print('PASS:', name, flush=True)
    check('settings policy overrides legacy config policy',ctx.get_config('policy')==baseline)
    fallback = copy.deepcopy(config)
    del fallback['plugins']['entries']['hermes-guardian']['settings']['policy']
    (home/'config.yaml').write_text(json.dumps(fallback))
    check('legacy policy fallback when settings key absent',ctx.get_config('policy')==legacy)
    (home/'config.yaml').write_text(json.dumps(config))
    check('settings precedence restored',ctx.get_config('policy')==baseline)
    # Real public CLI discovery, with no model request and no config writes.
    command = subprocess.run([str(Path(sys.executable).parent/'hermes'),'guardian','propose',RECIPE],capture_output=True,text=True,env=os.environ,timeout=45)
    if command.returncode:
        print(command.stdout, command.stderr, flush=True)
    check('real hermes guardian propose command',command.returncode==0 and 'offline-template' in command.stdout)
    executable = Path(sys.executable).parent/'hermes'
    proposal_path = root/'proposal.json'
    pending = offline(RECIPE, baseline)
    code, sent, _ = interactive_cli(executable, ['propose', RECIPE, '--output', str(proposal_path)], 'NO')
    check('real CLI rejected save leaves no file', code==2 and sent and not proposal_path.exists())
    code, sent, _ = interactive_cli(executable, ['propose', RECIPE, '--output', str(proposal_path)], 'SAVE '+digest(pending))
    check('real CLI confirmed save creates exact owner-only proposal', code==0 and sent and json.loads(proposal_path.read_text())==pending and proposal_path.stat().st_mode & 0o777 == 0o600)
    code, sent, _ = interactive_cli(executable, ['activate', str(proposal_path)], 'NO')
    check('real CLI rejected activation preserves policy', code==2 and sent and ctx.get_config('policy')==baseline)
    code, sent, transcript = interactive_cli(executable, ['activate', str(proposal_path)], 'ACTIVATE '+digest(pending))
    check('real CLI confirmed activation succeeds', code==0 and sent and '"activated": true' in transcript and ctx.get_config('policy')==baseline)
    cases = regression_cases(work,vault)
    started = time.monotonic()
    def cue(at, label):
        if args.demo:time.sleep(max(0,started+at-time.monotonic()))
        print('\n'+label,flush=True)
    cue(0,'LIVE: Describe -> Generate -> Simulate -> Review -> Activate -> Enforce')
    instruction = input('Describe permissions: ') if args.demo else EXAMPLE
    first = offline(instruction,ctx.get_config('policy'))
    check('ambiguous project/GitHub instruction asks clarification',bool(first['questions']))
    cue(10,'CLARIFICATION: project-scoped edits and git-push approval are unsupported.')
    for question in first['questions']:print(question,flush=True)
    cue(20,'Choose the explicitly conservative wording shown above.')
    clarified = input('Clarified instruction: ') if args.demo else RECIPE
    value = offline(clarified,ctx.get_config('policy'))
    check('clarified proposal validated',not value['questions'])
    print(json.dumps(value['policy'],indent=2),flush=True)
    cue(30,'POLICY LAB: exact evaluator, hypothetical calls only')
    results = simulate(value['policy'],cases,home=home)
    for result in results:
        print(f"{result['name']}: expected={result['expected']} actual={result['actual']} rule={result['decision']['rule']} reason={result['decision']['reason']}",flush=True)
    check('seven deterministic regression scenarios pass',all(r['passed'] for r in results))
    cue(40,'REVIEW: edits ask everywhere; supported deletions ask; GitHub pushes BLOCK.')
    print('Not a sandbox. Host automatic approval can bypass approve requests. No provider/model was used: this is the offline template.',flush=True)
    cue(45,'ACTIVATE: operator approves exact proposal digest; host saves atomically with backup')
    token = 'ACTIVATE '+digest(value)
    if args.demo:token=confirm('Approve this reviewed policy?',token)
    activated=activate(ctx,value,confirmation=token,storage=lambda:plugin_data_dir('hermes-guardian'))
    check('activated policy readback',ctx.get_config('policy')==value['policy'])
    check('backup contains previous policy',json.loads(Path(activated['backup']).read_text())['policy']==baseline)
    saved=hermes_yaml.safe_load((home/'config.yaml').read_text())
    entry=saved['plugins']['entries']['hermes-guardian']
    check('atomic settings save preserves other configuration',entry['settings']['operator_marker']=='PRESERVE' and entry['config']['legacy_marker']=='PRESERVE' and entry['config']['policy']==legacy and saved['approvals']==config['approvals'])
    def call(tool,arguments):
        result=handle_function_call(tool,arguments,task_id='policy-lab-demo',session_id='policy-lab-demo')
        print(result,flush=True)
        return result
    audit=home/'plugin-data/hermes-guardian/audit.jsonl'
    if args.demo:
        cue(55,'REAL HERMES: allowed read')
        check('allowed read executed','HELLO_POLICY_LAB' in call('read_file',{'path':str(work/'public.txt')}))
        cue(60,'REAL HERMES: approval-required write; choose o / Once')
        call('write_file',{'path':str(work/'approved.txt'),'content':'APPROVED_DEMO'})
        check('native approval write executed',(work/'approved.txt').read_text()=='APPROVED_DEMO')
        cue(72,'REAL HERMES: protected write blocked; operator reads actual audit')
        result=call('write_file',{'path':str(vault/'demo.txt'),'content':'MUST_NOT_WRITE'})
        check('protected file unchanged','Guardian' in result and (vault/'demo.txt').read_text()=='PROTECTED_DEMO_ONLY')
        print(audit.read_text(),flush=True)
        cue(80,'DONE')
        print(f'Elapsed: {time.monotonic()-started:.2f} seconds',flush=True)
    else:
        for case,result in zip(cases,results):
            output=call(case['tool'],case['args'])
            record=json.loads(audit.read_text().splitlines()[-1])
            check('lab/live parity: '+case['name'],record['action']==result['actual'] and record['rule']==result['decision']['rule'] and record['reason']==result['decision']['reason'])
            if result['actual']=='allow':check('real allowed read result','HELLO_POLICY_LAB' in output)
            else:check('real unattended/protected execution refused','error' in output.lower())
        check('simulated deletions never ran',(work/'public.txt').read_text()=='HELLO_POLICY_LAB')
        check('protected fixture preserved',(vault/'demo.txt').read_text()=='PROTECTED_DEMO_ONLY')
        # Public setter activation of a stricter rule; same loaded hook observes it.
        stricter=copy.deepcopy(value);stricter['policy']['rules'][0]['action']='block'
        activate(ctx,stricter,confirmation='ACTIVATE '+digest(stricter),storage=lambda:plugin_data_dir('hermes-guardian'))
        result=call('read_file',{'path':str(work/'fresh.txt')})
        check('loaded hook enforces changed policy without rewrite','Guardian' in result and json.loads(audit.read_text().splitlines()[-1])['action']=='block')
    print('RESULT:',json.dumps({'checks':len(checks),'demo':args.demo,'fixture_directory':str(root)}),flush=True)


if __name__=='__main__':main()
