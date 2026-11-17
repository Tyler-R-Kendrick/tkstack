"""Exercise policy gates through real Git snapshots and the standalone CLI."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / 'skills/constrain/scripts/constrain.py'
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


if __name__ == '__main__':
    unittest.main()
