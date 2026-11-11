import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from guardian.builder import (RECIPE, EXAMPLE, check_proposal, digest, from_model,
                              generate_model, offline, review)
from guardian.activation import activate
from guardian.cli import confirm, read_json
from guardian.lab import regression_cases, simulate
from guardian.policy import DEFAULT, Policy


class Fixture:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.home = self.root / 'home'
        self.workspace = self.root / 'work'
        self.vault = self.workspace / 'vault'
        self.vault.mkdir(parents=True)
        self.home.mkdir()
        self.config = copy.deepcopy(DEFAULT)
        self.config['protected_paths'] = [{'path': str(self.vault), 'action': 'block'}]
        self.cases = regression_cases(self.workspace, self.vault)


class LabTests(Fixture, unittest.TestCase):
    def test_regression_and_exact_evaluator(self):
        results = simulate(self.config, self.cases, home=self.home)
        self.assertTrue(all(r['passed'] for r in results))
        evaluator = Policy(self.config, mandatory_paths=(self.home,))
        for case, result in zip(self.cases, results):
            self.assertEqual(evaluator.evaluate(case['tool'], case['args']).action, result['actual'])

    def test_no_external_side_effects(self):
        original_open = os.open
        def read_only(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            return original_open(path, flags, *args, **kwargs)
        before = sorted(str(p) for p in self.root.rglob('*'))
        with patch('builtins.open', side_effect=AssertionError('file content read/write')), \
             patch('io.open', side_effect=AssertionError('file content read/write')), \
             patch('os.open', side_effect=read_only), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('os.system', side_effect=AssertionError('shell')), \
             patch('socket.socket', side_effect=AssertionError('network')), \
             patch('builtins.input', side_effect=AssertionError('approval')):
            self.assertTrue(all(r['passed'] for r in simulate(self.config, self.cases, home=self.home)))
        self.assertEqual(before, sorted(str(p) for p in self.root.rglob('*')))

    def test_mismatch_is_visible(self):
        self.cases[3]['expected'] = 'approve'
        result = simulate(self.config, self.cases, home=self.home)[3]
        self.assertFalse(result['passed'])
        self.assertEqual(result['actual'], 'block')
        self.assertEqual(result['decision']['reason'], 'ambiguous_arguments')

    def test_symlink_and_self_protection(self):
        alias = self.workspace / 'alias'
        alias.symlink_to(self.vault, target_is_directory=True)
        for path in (alias / 'file', self.home / 'config.yaml', Path(__file__).resolve().parents[1] / 'plugin.yaml'):
            cases = [dict(name='protected', tool='read_file', args={'path': str(path)}, expected='block')]
            self.assertTrue(simulate(self.config, cases, home=self.home)[0]['passed'])

    def test_precedence_strongest_not_last(self):
        self.config['rules'] += [{'tool': 'read_file', 'action': 'block'}, {'tool': 'read_file', 'action': 'allow'}]
        self.cases[0]['expected'] = 'block'
        self.assertTrue(simulate(self.config, self.cases, home=self.home)[0]['passed'])

    def test_invalid_cases_and_policy(self):
        for cases in ([], {}, [{'name': 'bad'}], [dict(name='x', tool='read_file', args={}, expected='maybe')]):
            with self.assertRaises(ValueError):
                simulate(self.config, cases, home=self.home)
        with self.assertRaises(ValueError):
            simulate({}, self.cases, home=self.home)
        with self.assertRaises(ValueError):
            simulate(self.config, self.cases, home='relative')

    def test_offline_recipe_and_ambiguity(self):
        self.assertEqual(offline(RECIPE, self.config)['questions'], [])
        for text in (EXAMPLE, 'do whatever is safe', 'Do not ask before edits and deletions; block GitHub pushes.'):
            self.assertTrue(offline(text, self.config)['questions'])
        self.assertEqual(offline(RECIPE, self.config)['policy'], self.config)

    def test_offline_preserves_stricter_tool_rules(self):
        self.config['rules'].append({'tool': 'write_file', 'action': 'block'})
        value = offline(RECIPE, self.config)
        self.assertEqual(Policy(value['policy']).evaluate('write_file', {'path': str(self.workspace/'file')}).action, 'block')

    def test_untrusted_model_output(self):
        valid = {'policy': self.config, 'questions': []}
        self.assertEqual(from_model(valid, self.config)['origin'], 'hermes-model')
        bads = [None, '```json {} ```', {}, dict(valid, extra=True), dict(valid, questions='yes'), dict(valid, questions=['x'*513])]
        for change in ({'default_action':'allow'}, {'rules':[{'tool':'github_push','action':'allow'}]},
                       {'protected_paths':[]}, {'protected_paths':[{'path':str(self.vault),'action':'approve'}]},
                       {'protected_paths':[{'path':'/invented','action':'block'}]},
                       {'rules':[{'tool':'terminal','action':'allow','command':'git push'}]}):
            bads.append(dict(valid, policy={**self.config, **change}))
        for bad in bads:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                from_model(bad, self.config)

    def test_supported_model_interface_and_local_validation(self):
        calls = []
        class LLM:
            def complete_structured(_, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(parsed={'policy': self.config, 'questions': []})
        ctx = SimpleNamespace(get_config=lambda *a: self.config, llm=LLM())
        self.assertEqual(generate_model(ctx, RECIPE)['origin'], 'hermes-model')
        self.assertTrue(calls[0]['json_schema']['additionalProperties'] is False)
        self.assertNotIn('provider', calls[0])
        self.assertNotIn('model', calls[0])
        self.assertEqual(calls[0]['timeout'], 30)

    def test_model_failure_never_exposes_provider_error(self):
        class LLM:
            def complete_structured(_, **kwargs):
                raise RuntimeError('credential=FAKE_PRIVATE_PROVIDER_DETAIL')
        ctx = SimpleNamespace(get_config=lambda *a: self.config, llm=LLM())
        with self.assertRaises(ValueError) as error:
            generate_model(ctx, RECIPE)
        self.assertNotIn('FAKE_PRIVATE', str(error.exception))

    def test_model_malformed_parsed_result_rejected(self):
        class LLM:
            def complete_structured(_, **kwargs): return SimpleNamespace(parsed=None)
        ctx = SimpleNamespace(get_config=lambda *a: self.config, llm=LLM())
        with self.assertRaises(ValueError): generate_model(ctx, RECIPE)

    def test_review_marks_weakening_and_staleness(self):
        value = offline(RECIPE, self.config)
        value['policy']['rules'][1]['action'] = 'allow'
        self.assertTrue(review(value, self.config)['changes'][0]['weakens'])
        with self.assertRaises(ValueError):
            check_proposal(value, DEFAULT)

    def test_json_duplicate_and_size_refused(self):
        path = self.root/'input.json'
        for content in ('{"a":1,"a":2}', '{"a":NaN}', ' '*1048577):
            path.write_text(content)
            with self.assertRaises(ValueError): read_json(path)

    def test_noninteractive_or_denied_confirmation(self):
        with patch('sys.stdin.isatty', return_value=False), self.assertRaises(ValueError):
            confirm('review', 'ACTIVATE test')
        with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='no'), self.assertRaises(ValueError):
            confirm('review', 'ACTIVATE test')


class ActivationTests(Fixture, unittest.TestCase):
    def context(self):
        policy = copy.deepcopy(self.config)
        class Context:
            def get_config(_, key, default=None): return copy.deepcopy(policy)
            def set_config(_, key, value):
                policy.clear(); policy.update(copy.deepcopy(value))
        return Context()

    def candidate(self):
        value = offline(RECIPE, self.config)
        value['policy']['rules'][1]['action'] = 'block'
        return value

    def apply(self, ctx, value, confirmation=None):
        return activate(ctx, value, confirmation=confirmation if confirmation is not None else 'ACTIVATE '+digest(value), storage=lambda:self.home)

    def test_activation_backup_and_success(self):
        ctx = self.context(); value = self.candidate()
        result = self.apply(ctx, value)
        self.assertEqual(ctx.get_config('policy'), value['policy'])
        backup = Path(result['backup'])
        self.assertEqual(json.loads(backup.read_text())['policy'], self.config)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_activation_rejected_approval_no_write(self):
        ctx = self.context()
        with self.assertRaises(ValueError): self.apply(ctx, self.candidate(), 'yes')
        self.assertEqual(ctx.get_config('policy'), self.config)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_activation_unresolved_invalid_stale(self):
        ctx = self.context()
        for value in (offline(EXAMPLE,self.config), {}, {**self.candidate(), 'base_digest':'stale'}):
            with self.assertRaises(ValueError): self.apply(ctx,value)
        self.assertEqual(ctx.get_config('policy'), self.config)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_activation_backup_failure_preserves_policy(self):
        ctx = self.context()
        with patch('guardian.activation._sync_file', side_effect=OSError('disk full')), self.assertRaises(OSError):
            self.apply(ctx,self.candidate())
        self.assertEqual(ctx.get_config('policy'), self.config)

    def test_activation_rollback_after_write_failure(self):
        ctx = self.context(); original = ctx.set_config; calls=[]
        def fail_after_replace(key,value):
            original(key,value); calls.append(value)
            if len(calls)==1:raise OSError('injected post-replace failure')
        ctx.set_config = fail_after_replace
        with self.assertRaisesRegex(RuntimeError,'previous policy preserved'):
            self.apply(ctx,self.candidate())
        self.assertEqual(ctx.get_config('policy'), self.config)
        self.assertEqual(len(calls),2)

    def test_activation_refuses_symlink_storage(self):
        alias=self.root/'alias';alias.symlink_to(self.home,target_is_directory=True)
        value=self.candidate();ctx=self.context()
        with self.assertRaises(OSError):
            activate(ctx,value,confirmation='ACTIVATE '+digest(value),storage=lambda:alias)
        self.assertEqual(ctx.get_config('policy'),self.config)

    def test_activation_readback_failure_rolls_back(self):
        ctx = self.context(); original = ctx.set_config
        def wrong_write(key, value):
            if value != self.config:
                changed = copy.deepcopy(value)
                changed['rules'][0]['action'] = 'block'
                original(key, changed)
            else:
                original(key, value)
        ctx.set_config = wrong_write
        with self.assertRaisesRegex(RuntimeError, 'previous policy preserved'):
            self.apply(ctx, self.candidate())
        self.assertEqual(ctx.get_config('policy'), self.config)

    def test_activation_lock_contention_preserves_previous(self):
        import fcntl
        lock = self.home/'activation.lock'
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ctx = self.context()
            with self.assertRaises(BlockingIOError): self.apply(ctx, self.candidate())
            self.assertEqual(ctx.get_config('policy'), self.config)
        finally:
            os.close(fd)

    def test_activation_failed_rollback_is_explicit(self):
        ctx = self.context(); original = ctx.set_config; calls = []
        def fail(key, value):
            calls.append(value)
            if len(calls)==1: original(key,value)
            raise OSError('storage failure')
        ctx.set_config=fail
        with self.assertRaisesRegex(RuntimeError,'Stop the agent'):
            self.apply(ctx,self.candidate())
        backups=list(self.home.glob('policy-backup-*.json'))
        self.assertEqual(len(backups),1)
        self.assertEqual(json.loads(backups[0].read_text())['policy'],self.config)
