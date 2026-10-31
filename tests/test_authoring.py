"""Public scaffold, validation, predicate, and native adapter contracts."""

import copy
import importlib.util
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


skillify = load("skillify_helper", ROOT / "skills/skillify/scripts/skillify.py")
hookify = load("hookify_helper", ROOT / "skills/hookify/scripts/hookify.py")


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.policy = json.loads((ROOT / "skills/hookify/examples/policy.json").read_text())
        self.rules = self.root / "rules with spaces.json"
        self.save()

    def save(self):
        self.rules.write_text(json.dumps(self.policy))

    def hook(self, payload, adapter="claude"):
        return subprocess.run([sys.executable, str(ROOT / "skills/hookify/scripts/hookify.py"),
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
            self.assertEqual(skillify.validate(ROOT / "skills" / name)["name"], name)
        cache = self.root / "plugin cache/skillify"
        shutil.copytree(ROOT / "skills/skillify", cache, ignore=shutil.ignore_patterns("__pycache__"))
        helper = load("copied_skillify", cache / "scripts/skillify.py")
        before = {str(p.relative_to(cache)): p.read_bytes() for p in cache.rglob("*") if p.is_file()}
        target = self.root / "project/skills/new-check"
        helper.scaffold(target, "new-check", "Use for the specified compatibility check.")
        after = {str(p.relative_to(cache)): p.read_bytes() for p in cache.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertTrue((target / "SKILL.md").is_file())

    def test_replay_known_decisions_is_stable_under_parallelism(self):
        cases = json.loads((ROOT / "skills/hookify/examples/cases.json").read_text())
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


if __name__ == "__main__":
    unittest.main()
