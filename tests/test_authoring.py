"""Public scaffold, validation, predicate, and native adapter contracts."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


skillify = load("skillify_helper", ROOT / "skills/learn/skills/skillify/scripts/skillify.py")
hookify = load("hookify_helper", ROOT / "skills/learn/skills/hookify/scripts/hookify.py")


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.policy = json.loads((ROOT / "skills/learn/skills/hookify/examples/policy.json").read_text())
        self.rules = self.root / "rules with spaces.json"
        self.save()

    def save(self):
        self.rules.write_text(json.dumps(self.policy))

    def hook(self, payload, adapter="claude"):
        return subprocess.run([sys.executable, str(ROOT / "skills/learn/skills/hookify/scripts/hookify.py"),
            "run", "--rules", str(self.rules), "--adapter", adapter],
            input=json.dumps(payload), text=True, capture_output=True)

    def package(self):
        target = self.root / "skills/inspect-contracts"
        skillify.scaffold(target, target.name, "Inspect compatibility: use when reviewing contracts.")
        return target

    def test_scaffold_is_draft_until_procedure_is_completed_and_never_overwrites(self):
        target = self.package()
        with self.assertRaisesRegex(ValueError, "Complete the scaffold"):
            skillify.validate(target)
        before = (target / "SKILL.md").read_bytes()
        with self.assertRaises(FileExistsError):
            skillify.scaffold(target, target.name, "Overwrite")
        self.assertEqual((target / "SKILL.md").read_bytes(), before)
        source = (target / "SKILL.md").read_text()
        complete = "\n".join("Inspect the provider response against the consumer-required fields." if line.startswith("TODO(SKILLIFY):") else line for line in source.splitlines())
        (target / "SKILL.md").write_text(complete)
        with self.assertRaisesRegex(ValueError, "Complete the scaffold reference"):
            skillify.validate(target)
        for path in [*(target / "references").glob("*.md"), *(target / "commands").glob("*.md")]:
            content = path.read_text().replace("TODO(SKILLIFY):", "Completed:")
            path.write_text("\n".join("Inspect the provider response against the consumer-required fields."
                                     if line.startswith("TODO(SKILLIFY):") else line
                                     for line in content.splitlines()))
        self.assertEqual(skillify.validate(target)["status"], "structurally-valid")
        self.assertEqual((target / "SKILL.md").read_text(), complete)

    def test_package_validation_rejects_broken_escaping_references_and_invalid_python(self):
        target = self.package()
        for path in (target / "references").glob("*.md"):
            path.unlink()
        content = '---\nname: inspect-contracts\ndescription: "Inspect contracts when asked."\n---\n\nRead [details](references/check.md).\n'
        for path in (target / 'commands').glob('*.md'):
            path.write_text(path.read_text().replace('TODO(SKILLIFY):', 'Fixture contract:'))
        (target / "SKILL.md").write_text(content)
        with self.assertRaisesRegex(ValueError, "Missing or external"):
            skillify.validate(target)
        (target / "references").mkdir(exist_ok=True)
        (target / "references/check.md").write_text("Check required consumer fields.")
        self.assertEqual(skillify.validate(target)["name"], target.name)
        (target / "references/check.md").unlink()
        outside = self.root / "outside.md"
        outside.write_text("External content")
        (target / "references/check.md").symlink_to(outside)
        with self.assertRaises(ValueError):
            skillify.validate(target)
        (target / "references/check.md").unlink()
        (target / "references/check.md").write_text("Check required fields.")
        (target / "scripts").mkdir(exist_ok=True)
        (target / "scripts/check.py").write_text("def broken(:")
        with self.assertRaises(SyntaxError):
            skillify.validate(target)

    def test_profile_rejects_boolean_description_and_unsupported_multiline_yaml(self):
        target = self.package()
        for description in ("false", ">-\n  Multi-line description"):
            (target / "SKILL.md").write_text(f"---\nname: inspect-contracts\ndescription: {description}\n---\nA concrete procedure.\n")
            with self.assertRaises(ValueError):
                skillify.validate(target)

    def test_owned_authoring_packages_are_self_contained_and_copied_skill_still_works(self):
        for name in ("skillify", "hookify"):
            self.assertEqual(skillify.validate(ROOT / "skills/learn/skills" / name)["name"], name)
        cache = self.root / "plugin cache/skillify"
        shutil.copytree(ROOT / "skills/learn/skills/skillify", cache, ignore=shutil.ignore_patterns("__pycache__"))
        helper = load("copied_skillify", cache / "scripts/skillify.py")
        before = {str(p.relative_to(cache)): p.read_bytes() for p in cache.rglob("*") if p.is_file()}
        target = self.root / "project/skills/new-check"
        helper.scaffold(target, "new-check", "Use for the specified compatibility check.")
        after = {str(p.relative_to(cache)): p.read_bytes() for p in cache.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertTrue((target / "SKILL.md").is_file())

    def test_replay_known_decisions_is_stable_under_parallelism(self):
        cases = json.loads((ROOT / "skills/learn/skills/hookify/examples/cases.json").read_text())
        serial = hookify.replay(self.policy, cases, 1)
        parallel = hookify.replay(self.policy, list(reversed(cases)), 4)
        self.assertTrue(serial["passed"])
        self.assertEqual(serial, parallel)
        cases[0]["expected"] = {"decision": "allow", "matches": []}
        self.assertFalse(hookify.replay(self.policy, cases, 2)["passed"])

    def test_typed_equality_missing_and_present_null_are_distinct(self):
        condition = {"field": "flag", "operator": "equals", "value": True}
        self.assertFalse(hookify.matches(condition, {"flag": 1}))
        self.assertTrue(hookify.matches(condition, {"flag": True}))
        condition.update(operator="exists", value=True)
        self.assertTrue(hookify.matches(condition, {"flag": None}))
        self.assertFalse(hookify.matches(condition, {}))
        condition.update(operator="equals", value=None)
        self.assertFalse(hookify.matches(condition, {}))
        self.assertTrue(hookify.matches(condition, {"flag": None}))

    def test_block_precedence_disabled_rules_and_declaration_order(self):
        event = {"event": "before-tool", "fields": {"tool_name": "Write", "tool_input": {
            "file_path": "api.generated.ts", "content": "console.log(value)"}}}
        expected = hookify.evaluate(self.policy, event)
        self.assertEqual(expected["decision"], "block")
        self.policy["rules"].reverse()
        self.assertEqual(hookify.evaluate(self.policy, event), expected)
        for rule in self.policy["rules"]:
            if rule["action"] == "block":
                rule["enabled"] = False
        self.assertEqual(hookify.evaluate(self.policy, event)["decision"], "warn")

    def test_claude_pretool_json_denies_and_other_tools_remain_unchanged(self):
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Edit",
                   "tool_input": {"file_path": "api.generated.ts", "new_string": "replacement"}}
        blocked = self.hook(payload)
        self.assertEqual(blocked.returncode, 0, blocked.stderr)
        self.assertEqual(blocked.stderr, "")
        output = json.loads(blocked.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "deny")
        allowed = self.hook({**payload, "tool_name": "Read"})
        self.assertEqual(json.loads(allowed.stdout), {})
        self.assertEqual(allowed.returncode, 0)

    def test_stop_continuation_has_reentry_guard_without_transcript_matching(self):
        self.policy["rules"] = [{"id": "demo-stop-reminder", "event": "before-stop", "enabled": True,
            "action": "block", "conditions": [{"field": "stop_hook_active", "operator": "equals", "value": False}],
            "message": "Demonstration reminder; no completion proof claimed."}]
        self.save()
        first = self.hook({"hook_event_name": "Stop", "stop_hook_active": False})
        self.assertEqual(json.loads(first.stdout)["decision"], "block")
        second = self.hook({"hook_event_name": "Stop", "stop_hook_active": True})
        self.assertEqual(json.loads(second.stdout), {})

    def test_unknown_operator_duplicate_ids_and_bad_flags_are_rejected(self):
        for mutation in ("operator", "duplicate", "flag"):
            policy = copy.deepcopy(self.policy)
            if mutation == "operator":
                policy["rules"][0]["conditions"][0]["operator"] = "guess"
            elif mutation == "duplicate":
                policy["rules"].append(copy.deepcopy(policy["rules"][0]))
            else:
                policy["rules"][0]["enabled"] = "true"
            with self.assertRaises(ValueError):
                hookify.validate(policy)

    def test_runtime_error_uses_explicit_failure_mode_and_invalid_policy_blocks(self):
        event = {"hook_event_name": "PreToolUse", "tool_input": {}}
        blocked = self.hook(event)
        self.assertEqual(blocked.returncode, 2)
        self.assertEqual(blocked.stdout, "")
        self.policy["failure_mode"] = "warn"
        self.save()
        warned = self.hook(event)
        self.assertEqual(warned.returncode, 0)
        self.assertIn("requires tool_name", json.loads(warned.stdout)["systemMessage"])
        self.rules.write_text('{"version":NaN}')
        invalid = self.hook(event)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("Non-finite", invalid.stderr)

    def test_emitted_command_quotes_paths_and_executes_native_protocol(self):
        before = self.rules.read_bytes()
        fragment = hookify.fragment(self.policy, self.rules)
        self.assertEqual(self.rules.read_bytes(), before)
        self.assertEqual(set(fragment["hooks"]), {"PreToolUse"})
        command = fragment["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        args = shlex.split(command)
        self.assertIn(str(self.rules), args)
        result = subprocess.run(args, input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {}}),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})

    def test_duplicate_json_fields_cannot_silently_change_policy(self):
        self.rules.write_text('{"version":1,"failure_mode":"warn","failure_mode":"block","rules":[]}')
        with self.assertRaisesRegex(ValueError, "Duplicate JSON field"):
            hookify.read_json(self.rules)
        result = self.hook({"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {}})
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")


class TestifyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'src').mkdir()
        (self.root / 'tests').mkdir()
        self.program = self.root / 'src/cli.py'
        self.program.write_text('import json,sys\nif sys.argv[1:] == ["ok"]: print(json.dumps({"value": 7}))\nelse: print("invalid request", file=sys.stderr); sys.exit(2)\n')
        self.spec = self.root / 'spec.json'
        self.data = {'version': 1, 'entrypoint': 'src/cli.py', 'risk': 'A malformed request may be accepted or return an incorrect value.',
            'distinction': 'The actual CLI contract exercises the consumer boundary without internal mocks.', 'timeout': 4,
            'cases': [{'name': 'valid', 'args': ['ok'], 'exit': 0, 'stdout_json': {'value': 7}},
                      {'name': 'invalid', 'args': ['bad'], 'exit': 2, 'stderr_contains': 'invalid request'}]}
        self.save_spec()
        self.script = ROOT / 'skills/learn/skills/testify/scripts/testify.py'
        self.target = self.root / 'tests/test_cli.py'

    def save_spec(self):
        self.spec.write_text(json.dumps(self.data))

    def invoke(self, command, expected=0, target='tests/test_cli.py'):
        args = [sys.executable, '-B', str(self.script), command, '--project', str(self.root), '--target', target]
        if command != 'run':
            args += ['--spec', str(self.spec)]
        result = subprocess.run(args, cwd=self.root, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_plan_create_and_real_run_detect_a_behavioral_fault(self):
        planned = json.loads(self.invoke('plan').stdout)
        self.assertEqual(planned['status'], 'planned')
        self.assertFalse(self.target.exists())
        self.assertIn('invalid request', planned['content'])
        del self.data['timeout']
        self.save_spec()
        default = json.loads(self.invoke('plan').stdout)
        self.assertIn('timeout=30', default['content'])
        self.data['timeout'] = 4
        self.save_spec()
        routed = subprocess.run([sys.executable, '-B', str(ROOT / 'src/tkstack.py'), '--project', str(self.root),
                                 'skills', 'learn', '--', 'testify', 'native', 'plan',
                                 '--project', str(self.root), '--target', 'tests/test_cli.py', '--spec', str(self.spec)],
                                cwd=self.root, capture_output=True, text=True, timeout=45)
        self.assertEqual(routed.returncode, 0, routed.stdout + routed.stderr)
        self.assertEqual(json.loads(routed.stdout)['content'], planned['content'])
        self.assertFalse(self.target.exists())
        self.invoke('create')
        before = self.target.read_bytes()
        self.invoke('create', expected=1)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(json.loads(self.invoke('run').stdout)['status'], 'pass')
        routed_run = subprocess.run([sys.executable, '-B', str(ROOT / 'src/tkstack.py'), '--project', str(self.root),
            'skills', 'learn', '--', 'testify', 'native', 'run', '--project', str(self.root),
            '--target', 'tests/test_cli.py'], cwd=self.root, capture_output=True, text=True, timeout=45)
        self.assertEqual(routed_run.returncode, 0, routed_run.stdout + routed_run.stderr)
        self.assertEqual(json.loads(routed_run.stdout)['status'], 'pass')
        original = self.program.read_text()
        self.program.write_text(original.replace('"value": 7', '"value": 8'))
        failed = json.loads(self.invoke('run', expected=1).stdout)
        self.assertIn('FAIL', failed['stderr'])
        self.program.write_text(original)
        self.assertEqual(json.loads(self.invoke('run').stdout)['status'], 'pass')

    def test_invalid_specs_and_unsafe_paths_do_not_create_or_replace_a_test(self):
        for mutation in ('no_oracle', 'bool_exit', 'escape', 'duplicate_case', 'duplicate', 'timeout_zero', 'timeout_bool'):
            data = copy.deepcopy(self.data)
            if mutation == 'no_oracle':
                del data['cases'][0]['stdout_json']
            elif mutation == 'bool_exit':
                data['cases'][0]['exit'] = True
            elif mutation == 'escape':
                data['entrypoint'] = '../outside.py'
            elif mutation == 'duplicate_case':
                data['cases'].append({**data['cases'][0], 'name': 'repeated'})
            elif mutation == 'timeout_zero':
                data['timeout'] = 0
            elif mutation == 'timeout_bool':
                data['timeout'] = True
            if mutation == 'duplicate':
                self.spec.write_text('{"version":1,"version":1}')
            else:
                self.spec.write_text(json.dumps(data))
            with self.subTest(mutation=mutation):
                self.invoke('create', expected=1)
                self.assertFalse(self.target.exists())
        self.save_spec()
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / 'tests/link').symlink_to(outside, target_is_directory=True)
        self.invoke('create', expected=1, target='tests/link/test_escape.py')
        self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(os.name == 'posix' and hasattr(os, 'waitid') and hasattr(os, 'WNOWAIT'), 'POSIX process supervision')
    def test_generated_case_keeps_group_ownership_until_cleanup(self):
        self.invoke('create')
        wrapper = '''import importlib.util, os, subprocess, sys
spec = importlib.util.spec_from_file_location('generated_contract', sys.argv[1])
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
original = os.killpg
def guarded(pid, sig):
    try:
        os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError:
        raise RuntimeError('group leader was already reaped')
    return original(pid, sig)
os.killpg = guarded
assert module.run_case([sys.executable, '-c', 'print("ok")'], sys.argv[2], 5).stdout == 'ok\\n'
try:
    module.run_case([sys.executable, '-c', 'import time; time.sleep(5)'], sys.argv[2], .2)
except subprocess.TimeoutExpired:
    pass
else:
    raise AssertionError('deadline did not expire')
'''
        env = {key: value for key, value in os.environ.items() if key != 'TKSTACK_CODIFY_EXECUTION'}
        result = subprocess.run([sys.executable, '-c', wrapper, str(self.target), str(self.root)],
                                env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(os.name == 'posix' and Path('/proc').is_dir(), 'POSIX process cleanup fixture')
    def test_direct_run_outer_deadline_stops_the_generated_case_group(self):
        self.program.write_text('''import os, pathlib, subprocess, sys, time
root = pathlib.Path(__file__).resolve().parent.parent
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
tmp = root / 'pids.tmp'
tmp.write_text(__import__('json').dumps([os.getpid(), child.pid]))
tmp.replace(root / 'pids.json')
time.sleep(30)
''')
        self.data['timeout'] = 30
        self.data['cases'] = [{'name': 'slow', 'args': [], 'exit': 0, 'stdout_text': ''}]
        self.save_spec()
        self.invoke('create')
        wrapper = '''import importlib.util, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]).parent))
spec = importlib.util.spec_from_file_location('testify_review', sys.argv[1])
module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
module.RUN_TIMEOUT = 3
original = subprocess.run
def shorten(*args, **kwargs):
    if kwargs.get('timeout') == 120: kwargs['timeout'] = 3
    return original(*args, **kwargs)
module.subprocess.run = shorten
raise SystemExit(module.main(['run', '--project', sys.argv[2], '--target', 'tests/test_cli.py']))
'''
        env = {key: value for key, value in os.environ.items() if key != 'TKSTACK_CODIFY_EXECUTION'}
        result = subprocess.run([sys.executable, '-c', wrapper, str(self.script), str(self.root)],
                                cwd=self.root, env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 124, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual((receipt['status'], receipt['timeout_seconds']), ('timeout', 3))
        self.assertGreaterEqual(receipt['elapsed_ms'], 2500)
        pids = json.loads((self.root / 'pids.json').read_text())
        try:
            for pid in pids:
                stat = Path(f'/proc/{pid}/stat')
                alive = stat.exists() and stat.read_text().split(') ', 1)[1].split()[0] != 'Z'
                self.assertFalse(alive, f'Outer deadline left process {pid} running')
        finally:
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    @unittest.skipUnless(os.name == 'posix' and Path('/proc').is_dir(), 'POSIX process cleanup fixture')
    def test_direct_run_interruption_stops_the_generated_case_group(self):
        self.program.write_text('''import json, os, pathlib, subprocess, sys, time
root = pathlib.Path(__file__).resolve().parent.parent
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
tmp = root / 'pids.tmp'
tmp.write_text(json.dumps([os.getpid(), child.pid]))
tmp.replace(root / 'pids.json')
time.sleep(30)
''')
        self.data['timeout'] = 30
        self.data['cases'] = [{'name': 'slow', 'args': [], 'exit': 0, 'stdout_text': ''}]
        self.save_spec()
        self.invoke('create')
        env = {key: value for key, value in os.environ.items() if key != 'TKSTACK_CODIFY_EXECUTION'}
        process = subprocess.Popen([sys.executable, str(self.script), 'run', '--project', str(self.root),
            '--target', 'tests/test_cli.py'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pids = []
        try:
            deadline = time.monotonic() + 8
            while not (self.root / 'pids.json').exists() and time.monotonic() < deadline:
                time.sleep(.02)
            pids = json.loads((self.root / 'pids.json').read_text())
            process.terminate()
            out, err = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 143, out + err)
            self.assertEqual(json.loads(out)['status'], 'interrupted')
            for pid in pids:
                stat = Path(f'/proc/{pid}/stat')
                alive = stat.exists() and stat.read_text().split(') ', 1)[1].split()[0] != 'Z'
                self.assertFalse(alive, f'Interrupted run left process {pid} running')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    @unittest.skipUnless(os.name == 'posix' and Path('/proc').is_dir(), 'POSIX process cleanup fixture')
    def test_generated_case_timeout_cleans_ordinary_descendants(self):
        self.program.write_text('''import pathlib, subprocess, sys, time
root = pathlib.Path(__file__).resolve().parent.parent
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
(root / 'child.pid').write_text(str(child.pid))
time.sleep(30)
''')
        self.data['timeout'] = 1
        self.data['cases'] = [{'name': 'slow', 'args': [], 'exit': 0, 'stdout_text': ''}]
        self.save_spec()
        self.invoke('create')
        self.invoke('run', expected=1)
        pid = int((self.root / 'child.pid').read_text())
        try:
            state = Path(f'/proc/{pid}/stat')
            alive = state.exists() and state.read_text().split(') ', 1)[1].split()[0] != 'Z'
            self.assertFalse(alive, 'Timed-out test left its ordinary child running')
        finally:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


if __name__ == "__main__":
    unittest.main()
