"""Exercise policy gates through real Git snapshots and the standalone CLI."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / 'skills/constrain/scripts/constrain.py'
MUTATE = ROOT / 'skills/constrain/scripts/mutate.py'
GOOD = '''import unittest
class Contract(unittest.TestCase):
    def test_result(self):
        actual = int('42')
        self.assertEqual(actual, 42)
'''


class ConstrainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'project with spaces'
        self.repo.mkdir()
        self.git('init', '-q')
        (self.repo / 'tests').mkdir()
        (self.repo / '.constrain').mkdir()
        self.policy = json.loads((ROOT / '.constrain/config.json').read_text())
        self.policy.pop('boundaries', None)
        self.policy['tests']['exceptions'] = []
        self.policy['tests']['max_cases'] = 380
        self.suite = self.repo / 'tests/test_contract.py'
        self.suite.write_text(GOOD)
        self.write_policy()
        self.review()

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.repo), *args], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def write_policy(self):
        (self.repo / '.constrain/config.json').write_text(json.dumps(self.policy))

    def review(self):
        record = {'sha256': hashlib.sha256(self.suite.read_bytes()).hexdigest(),
                  'risk': 'Consumer parses a valid numeric boundary response incorrectly.',
                  'oracle': 'Actual parsed value must equal the independently supplied number.',
                  'kinds': ['contract'], 'overlap': 'One boundary example; no parallel lower-layer test covers this fixture.'}
        (self.repo / '.constrain/reviews.json').write_text(json.dumps({'tests/test_contract.py': record}))

    def cli(self, *args, expected=0):
        result = subprocess.run([sys.executable, '-B', str(ENGINE), 'audit', '--repo', str(self.repo), *args],
                                cwd=self.repo.parent, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else result

    def test_good_bad_and_helper_exception_use_actual_cli_without_executing_tests(self):
        marker = self.repo / 'IMPORTED'
        self.suite.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n" + GOOD)
        self.review()
        before = {p.relative_to(self.repo).as_posix(): p.read_bytes() for p in self.repo.rglob('*') if p.is_file() and '.git' not in p.parts}
        self.assertEqual(self.cli()['status'], 'pass')
        self.assertFalse(marker.exists())
        after = {p.relative_to(self.repo).as_posix(): p.read_bytes() for p in self.repo.rglob('*') if p.is_file() and '.git' not in p.parts}
        self.assertEqual(before, after)
        self.suite.write_text(GOOD.replace("actual = int('42')\n        self.assertEqual(actual, 42)", 'self.assertEqual(1, 1)'))
        self.review()
        rules = {e['rule'] for e in self.cli(expected=1)['errors']}
        self.assertEqual(rules, {'tests.constant-oracle', 'tests.self-comparison'})
        self.suite.write_text(GOOD.replace("actual = int('42')\n        self.assertEqual(actual, 42)", 'self.helper()').replace('    def test_result', '    def helper(self):\n        self.assertEqual(int("42"), 42)\n    def test_result'))
        self.review()
        self.assertEqual(self.cli(expected=1)['errors'][0]['rule'], 'tests.no-oracle')
        self.policy['tests']['exceptions'] = [{'rule': 'tests.no-oracle', 'path': 'tests/test_contract.py:Contract.test_result', 'reason': 'The helper owns the actual boundary assertion for this workflow.'}]
        self.write_policy()
        self.assertEqual(self.cli()['status'], 'pass')
        self.suite.write_text(GOOD)
        self.review()
        self.assertEqual(self.cli(expected=1)['errors'][0]['rule'], 'tests.stale-exception')

    def test_duplicate_renamed_tests_and_budget_growth_block_without_automatic_baseline(self):
        self.suite.write_text(GOOD + "\n    def test_other(self):\n        actual = int('42')\n        self.assertEqual(actual, 42)\n")
        self.review()
        self.policy['tests']['max_cases'] = 1
        self.write_policy()
        report = self.cli(expected=1)
        self.assertEqual({e['rule'] for e in report['errors']}, {'tests.duplicate-body', 'tests.budget'})
        self.assertEqual(report['metrics']['test_cases'], 2)
        self.policy['layout']['budgets'][0]['max_files'] = 0
        self.write_policy()
        self.assertIn('layout.budget', {e['rule'] for e in self.cli(expected=1)['errors']})

    def test_identical_bodies_with_distinct_fixtures_or_decorators_are_not_proven_duplicates(self):
        self.suite.write_text('''import unittest
def another_case(function): return function
class First(unittest.TestCase):
    def setUp(self): self.value, self.expected = 'primary', 'primary'
    def test_result(self): self.assertEqual(self.value, self.expected)
    @another_case
    def test_decorated_case(self): self.assertEqual(self.value, self.expected)
class Second(unittest.TestCase):
    def setUp(self): self.value, self.expected = 'replica', 'replica'
    def test_result(self): self.assertEqual(self.value, self.expected)
''')
        self.review()
        self.assertEqual(self.cli()['status'], 'pass')

    def test_staged_policy_reviews_and_tests_cannot_be_hidden_by_unstaged_repairs(self):
        self.git('add', '.')
        self.assertEqual(self.cli('--staged')['status'], 'pass')
        self.suite.write_text(GOOD.replace("int('42')", "int('43')"))
        self.assertEqual(self.cli(expected=1)['errors'][0]['rule'], 'tests.stale-review')
        self.assertEqual(self.cli('--staged')['status'], 'pass')
        self.git('add', 'tests')
        self.review()  # A worktree review cannot approve staged bytes.
        self.assertEqual(self.cli('--staged', expected=1)['errors'][0]['rule'], 'tests.stale-review')
        self.git('add', '.constrain/reviews.json')
        self.assertEqual(self.cli('--staged')['status'], 'pass')
        self.policy['tests']['max_cases'] = 0
        self.write_policy()
        self.git('add', '.constrain/config.json')
        self.policy['tests']['max_cases'] = 100
        self.write_policy()
        self.assertEqual(self.cli('--staged', expected=1)['errors'][0]['rule'], 'tests.budget')
        # Invoke the actual hook: constraint failure must stop before the docs gate.
        hook = subprocess.run([str(ROOT / '.githooks/pre-commit')], cwd=self.repo,
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(hook.returncode, 1, hook.stdout + hook.stderr)
        self.assertIn('tests.budget', hook.stdout)


    def test_invalid_policy_missing_inputs_and_symlinks_fail_closed(self):
        path = self.repo / '.constrain/config.json'
        original = path.read_text()
        invalid_budget = json.loads(original)
        invalid_budget['tests']['max_cases'] = True
        for bad in ('{"version":1,"version":1}', json.dumps(invalid_budget), original.replace('tests/test_*.py', '../test_*.py')):
            with self.subTest(policy=bad[:40]):
                path.write_text(bad)
                result = self.cli(expected=2)
                self.assertIn('constrain:', result.stderr)
        path.write_text(original)
        self.suite.unlink()
        self.suite.symlink_to(ROOT / 'tests/test_constrain.py')
        self.assertIn('symlinks', self.cli(expected=2).stderr)
        self.suite.unlink()
        self.suite.write_text(GOOD)
        (self.repo / '.constrain/reviews.json').unlink()
        self.assertIn('Missing constraint input', self.cli(expected=2).stderr)

    def test_ignored_artifact_checks_deployment_ceiling_and_feature_growth_independently(self):
        (self.repo / '.gitignore').write_text('bundle.bin\n')
        bundle = self.repo / 'bundle.bin'
        bundle.write_bytes(b'x' * 100)
        self.policy['artifacts'] = [{'path': 'bundle.bin', 'max_bytes': 120, 'baseline_bytes': 100,
                                    'max_growth_bytes': 10, 'environment': 'Fixture deployment accepts at most 120 bytes.',
                                    'value': 'New useful feature has an explicit 10 byte allowance.'}]
        self.write_policy()
        self.assertEqual(self.cli('--category', 'artifacts')['metrics']['bundle.bin']['bytes'], 100)
        bundle.write_bytes(b'x' * 111)
        self.assertEqual(self.cli('--category', 'artifacts', expected=1)['errors'][0]['rule'], 'artifacts.unbudgeted-growth')
        bundle.write_bytes(b'x' * 121)
        self.assertEqual({e['rule'] for e in self.cli('--category', 'artifacts', expected=1)['errors']},
                         {'artifacts.environment-limit', 'artifacts.unbudgeted-growth'})
        bundle.unlink()
        self.assertIn('Missing or symlinked build artifact', self.cli('--category', 'artifacts', expected=2).stderr)
        self.assertEqual(self.cli()['status'], 'pass')  # Source gate runs before build.
        site = self.repo / 'site'
        site.mkdir()
        (site / 'index.html').write_bytes(b'a' * 60)
        (site / 'app.js').write_bytes(b'b' * 40)
        self.policy['artifacts'] = [{'path': 'site', 'kind': 'directory', 'max_bytes': 110,
                                    'baseline_bytes': 100, 'max_growth_bytes': 5, 'max_file_bytes': 65,
                                    'max_files': 2, 'environment': 'Fixture host limits the expanded published site.',
                                    'value': 'The baseline provides the existing published site.'}]
        self.write_policy()
        self.assertEqual(self.cli('--category', 'artifacts')['metrics']['site']['bytes'], 100)
        (site / 'app.js').write_bytes(b'b' * 70)
        rules = {item['rule'] for item in self.cli('--category', 'artifacts', expected=1)['errors']}
        self.assertEqual(rules, {'artifacts.environment-limit', 'artifacts.unbudgeted-growth', 'artifacts.file-limit'})
        (site / 'escape').symlink_to(self.repo.parent, target_is_directory=True)
        self.assertIn('Symlinked build artifact', self.cli('--category', 'artifacts', expected=2).stderr)


    def test_immutable_dependencies_and_real_execution_budgets_use_staged_sources(self):
        workflow = self.repo / '.github/workflows/ci.yml'
        workflow.parent.mkdir(parents=True)
        pinned = 'a' * 40
        template = 'name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    timeout-minutes: 15\n    steps:\n      - uses: actions/checkout@' + pinned + '\n'
        workflow.write_text(template)
        package = self.repo / 'package.json'
        package.write_text(json.dumps({'name': 'example', 'version': '1.0.0', 'dependencies': {'x': '1.0.0'}}))
        record = {'version':'1.0.0','resolved':'https://example.test/x.tgz','integrity':'sha256-' + 'A'*43 + '='}
        lock = self.repo / 'package-lock.json'
        data = {'lockfileVersion':3,'packages':{'':json.loads(package.read_text()),'node_modules/x':record}}
        lock.write_text(json.dumps(data))
        requirements = self.repo / 'requirements.lock'
        requirements.write_text('example==1.0 --hash=sha256:' + 'b'*64 + '\n')
        self.assertEqual(self.cli()['status'], 'pass')
        self.git('add', '.')
        workflow.write_text(template.replace(pinned, 'v4'))
        data['packages']['node_modules/x'].pop('integrity')
        lock.write_text(json.dumps(data))
        requirements.write_text('example==1.0 --hash=sha1:' + 'b'*40 + '\n')
        rules = {item['rule'] for item in self.cli(expected=1)['errors']}
        self.assertEqual(rules, {'dependencies.action-pin', 'dependencies.npm-integrity', 'dependencies.pip-integrity'})
        self.assertEqual(self.cli('--staged')['status'], 'pass')
        missing_parser = subprocess.run([sys.executable, '-S', '-B', str(ENGINE), 'check', '--repo', str(self.repo)],
                                        cwd=self.repo, capture_output=True, text=True, timeout=15)
        self.assertEqual(missing_parser.returncode, 2, missing_parser.stdout + missing_parser.stderr)
        self.assertIn('need PyYAML', missing_parser.stderr)
        shrinkwrap = self.repo / 'npm-shrinkwrap.json'
        shrinkwrap.write_text('{}')
        self.assertIn('dependencies.unsupported-lock', {item['rule'] for item in self.cli(expected=1)['errors']})
        shrinkwrap.unlink()
        self.git('add', '.github', 'package-lock.json', 'requirements.lock')
        self.assertEqual({item['rule'] for item in self.cli('--staged', expected=1)['errors']}, rules)
        workflow.write_text(template.replace('timeout-minutes: 15', 'timeout-minutes: 16'))
        self.assertIn('execution.timeout-budget', {item['rule'] for item in self.cli(expected=1)['errors']})
        mcp = self.repo / 'mcp.json'
        mcp.write_text(json.dumps({'mcpServers':{'unlocked':{'command':'npx', 'args':['example@latest']}}}))
        strict = self.cli('--category', 'dependencies', '--strict-dependencies', expected=1)
        self.assertIn('dependencies.runtime-unlocked', {item['rule'] for item in strict['errors']})
        (self.repo / 'scripts').mkdir()
        (self.repo / 'scripts/install.py').write_text("SERENA_FROM = 'git+https://example.test/repo@abc'\nlaunch = ['uvx', '--from', SERENA_FROM]\n")
        (self.repo / 'install.sh').write_text('TKSTACK_TARBALL=https://example.test/tar.gz/main\n')
        strict = self.cli('--category', 'dependencies', '--strict-dependencies', expected=1)
        self.assertTrue({'scripts/install.py:serena', 'install.sh:archive'} <= {item['path'] for item in strict['errors']})

    def test_document_duplicates_and_python_boundary_rules_are_independently_enforced(self):
        docs = self.repo / 'docs'
        docs.mkdir()
        (docs / 'a.md').write_text('Canonical factual information.\n')
        (docs / 'b.md').write_text('Different operational information.\n')
        code = self.repo / 'src'
        code.mkdir()
        (code / 'checker.py').write_text('import json\nresult = json.dumps({"ok": True})\n')
        self.policy['documents'] = {'include':['docs/*.md'], 'exclude':[]}
        self.policy['boundaries'] = [{'id':'offline', 'include':['src/*.py'], 'forbid_imports':['socket'], 'forbid_calls':['eval']}]
        self.write_policy()
        self.assertEqual(self.cli()['status'], 'pass')
        (docs / 'b.md').write_bytes((docs / 'a.md').read_bytes())
        (code / 'checker.py').write_text('import socket\nvalue = eval("1")\n')
        rules = {item['rule'] for item in self.cli(expected=1)['errors']}
        self.assertEqual(rules, {'documents.duplicate-bytes', 'boundaries.forbidden-import', 'boundaries.forbidden-call'})
        (code / 'checker.py').unlink()
        self.assertIn('boundaries.empty-scope', {item['rule'] for item in self.cli(expected=1)['errors']})


@unittest.skipUnless(os.name == 'posix' and hasattr(os, 'waitid') and hasattr(os, 'WNOWAIT'), 'POSIX process supervisor')
class MutationExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo with spaces'
        self.repo.mkdir()
        for args in [('init', '-q'), ('config', 'user.name', 'Fixture'), ('config', 'user.email', 'fixture@example.invalid')]:
            subprocess.run(['git', '-C', str(self.repo), *args], check=True, timeout=10)
        (self.repo / 'app.py').write_text('def increment(value):\n    return value + 1\n')
        (self.repo / 'test_app.py').write_text('''import subprocess, unittest
from app import increment
class Contract(unittest.TestCase):
    def test_exact(self): self.assertEqual(increment(3), 4)
    def test_positive(self):
        self.assertGreater(increment(3), 0)
        git = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, timeout=3)
        self.assertNotEqual(git.returncode, 0)
''')
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True, timeout=10)
        subprocess.run(['git', '-C', str(self.repo), 'commit', '-qm', 'fixture'], check=True, timeout=10)
        self.engine = self.root / 'fake-cosmic-ray'
        hanging = ('import subprocess,sys,time,pathlib; '
                   f'pathlib.Path({str(self.root / "child.pid")!r}).write_text(str('
                   'subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]).pid)); '
                   'time.sleep(30); return value + 1')
        orphan = hanging.replace('time.sleep(30); return', 'return')
        self.engine.write_text(f'''#!{sys.executable}
import pathlib, sys, time
if sys.argv[1:] == ['--version']:
    print('cosmic-ray, version 8.9.0')
else:
    path = pathlib.Path(sys.argv[2]); occurrence = int(sys.argv[4])
    source = path.read_text()
    replacement = {{0: 'return value - 1', 1: 'return (', 2: 'raise RuntimeError("broken mutant")',
                    3: {hanging!r}, 4: {orphan!r}}}[occurrence]
    path.write_text(source.replace('return value + 1', replacement))
''')
        self.engine.chmod(0o755)
        self.plan = self.root / 'plan.json'
        self.output = self.root / 'receipt.json'

    def run_mutations(self, tests, occurrences, timeout=10, source_sha256=None, operator='core/Fixture', version=1, total_timeout=60):
        plan = {'version': version, 'tests': tests, 'mutants': [
            {'id': str(i), 'module': 'app.py', 'operator': operator, 'occurrence': i}
            for i in occurrences]}
        if source_sha256 is not None:
            for mutant in plan['mutants']:
                mutant['source_sha256'] = source_sha256
        self.plan.write_text(json.dumps(plan))
        return subprocess.run([sys.executable, str(MUTATE), '--repo', str(self.repo), '--plan', str(self.plan),
            '--engine', str(self.engine), '--output', str(self.output), '--test-timeout', str(timeout),
            '--total-timeout', str(total_timeout)], capture_output=True, text=True, timeout=75,
            env={**os.environ, 'GIT_DIR': str(self.root / 'foreign/.git'),
                 'GIT_WORK_TREE': str(self.root / 'foreign')})

    def test_separates_assertion_failures_errors_invalid_mutants_and_survivors(self):
        result = self.run_mutations(['test_app.Contract.test_exact', 'test_app.Contract.test_positive'], [0, 1, 2])
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual([row['status'] for row in report['baseline']], ['passed'] * 4)
        self.assertEqual([row['status'] for row in report['mutants'][0]['tests']], ['assertion_failure', 'passed'])
        self.assertEqual(report['mutants'][1]['status'], 'invalid_mutation')
        self.assertEqual([row['status'] for row in report['mutants'][2]['tests']], ['error', 'error'])
        self.assertEqual((self.repo / 'app.py').read_text(), 'def increment(value):\n    return value + 1\n')

    @unittest.skipUnless(os.name == 'posix' and Path('/proc').is_dir(), 'POSIX process cleanup fixture')
    def test_deadline_is_not_a_kill_and_existing_receipt_is_never_overwritten(self):
        result = self.run_mutations(['test_app.Contract.test_exact'], [3], timeout=5)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual(report['mutants'][0]['tests'][0]['status'], 'timeout')
        child = int((self.root / 'child.pid').read_text())
        stat = Path(f'/proc/{child}/stat')
        alive = stat.exists() and stat.read_text().split(') ', 1)[1].split()[0] != 'Z'
        self.assertFalse(alive, 'Deadline left a test descendant running')
        previous = self.output.read_bytes()
        result = self.run_mutations(['test_app.Contract.test_exact'], [0])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_bytes(), previous)
        self.output = self.root / 'successful-receipt.json'
        result = self.run_mutations(['test_app.Contract.test_exact'], [4])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.output.read_text())['mutants'][0]['tests'][0]['status'], 'passed')
        child = int((self.root / 'child.pid').read_text())
        stat = Path(f'/proc/{child}/stat')
        alive = stat.exists() and stat.read_text().split(') ', 1)[1].split()[0] != 'Z'
        self.assertFalse(alive, 'A successful test left a child running')

    def test_failed_baseline_stops_before_any_mutant_is_applied(self):
        path = self.repo / 'test_app.py'
        path.write_text(path.read_text().replace('increment(3), 4', 'increment(3), 99'))
        subprocess.run(['git', '-C', str(self.repo), 'commit', '-qam', 'bad baseline'], check=True, timeout=10)
        result = self.run_mutations(['test_app.Contract.test_exact'], [0])
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(self.output.read_text())
        self.assertEqual(report['status'], 'baseline_invalid')
        self.assertEqual(report['mutants'], [])
        self.assertTrue(all(row['status'] == 'assertion_failure' for row in report['baseline']))

    def test_total_deadline_includes_the_engine_version_check(self):
        source = self.engine.read_text().replace("print('cosmic-ray, version 8.9.0')",
                                                 "time.sleep(5); print('cosmic-ray, version 8.9.0')")
        self.engine.write_text(source)
        started = time.monotonic()
        result = self.run_mutations(['test_app.Contract.test_exact'], [0], total_timeout=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('deadline', result.stderr)
        self.assertLess(time.monotonic() - started, 15)
        self.assertFalse(self.output.exists())

    def test_invalid_plan_or_changed_source_stops_before_a_mutation_is_applied(self):
        result = self.run_mutations(['test_app.Contract.test_exact'], [0], version=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        result = self.run_mutations(['test_app.Contract.test_exact'], [0], source_sha256='0' * 64)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(self.output.read_text())
        self.assertEqual(report['status'], 'error')
        self.assertIn('source no longer matches', report['error'])
        self.assertNotIn('apply', report['mutants'][0])

    @unittest.skipUnless(os.environ.get('TKSTACK_COSMIC_RAY_BIN'), 'install the locked Cosmic Ray tool')
    def test_real_engine_mutates_a_snapshot_and_attributes_the_distinct_failure(self):
        self.engine = Path(os.environ['TKSTACK_COSMIC_RAY_BIN'])
        digest = hashlib.sha256((self.repo / 'app.py').read_bytes()).hexdigest()
        result = self.run_mutations(['test_app.Contract.test_exact', 'test_app.Contract.test_positive'],
                                    [0], timeout=10, source_sha256=digest,
                                    operator='core/ReplaceBinaryOperator_Add_Sub')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(self.output.read_text())
        self.assertIn('return value - 1', report['mutants'][0]['diff'])
        self.assertEqual([row['status'] for row in report['mutants'][0]['tests']], ['assertion_failure', 'passed'])
        self.assertEqual((self.repo / 'app.py').read_text(), 'def increment(value):\n    return value + 1\n')


if __name__ == '__main__':
    unittest.main()
