import importlib.util
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/learn/scripts/learn.py"
SPEC = importlib.util.spec_from_file_location("learn_helper", SCRIPT)
learn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(learn)
sys.path.insert(0, str(ROOT / "scripts"))
import steering_adapter


class LearnTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        redirect = redirect_stdout(StringIO())
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)
        self.store = Path(self.temporary.name) / ".tkstack/steering"
        self.observation = {
            "source": {"conversation": "session-one", "message": "user-turn-two"},
            "user_text": "No. Not later. Do it all now.",
            "context": "The agent declared completion after doing only one requested item.",
            "kind": "correction",
        }

    def rule(self, evidence, **changes):
        return {
            "id": "complete-the-scope", "status": "active",
            "scope": {"kind": "personal", "value": "*"},
            "trigger": "Deciding when to declare a task complete",
            "assumption": "A useful subset is sufficient",
            "principle": "Use the authorized scope as the completion criterion",
            "action": "Finish feasible authorized work and identify concrete blockers",
            "boundary": "Respect actual access limits and current user instructions",
            "transfer": "Install and configure every requested integration",
            "counterexample": "A required account login remains a real access limit",
            "evidence": [evidence], **changes,
        }

    def test_capture_deduplicates_replay_but_preserves_recurrence(self):
        first = learn.capture(self.store, self.observation)
        self.assertEqual(learn.capture(self.store, self.observation), first)
        repeated = {**self.observation, "source": {"conversation": "session-two", "message": "user-turn-two"}}
        second = learn.capture(self.store, repeated)
        self.assertNotEqual(first, second)
        self.assertEqual(len(learn.read_state(self.store)["corrections"]), 2)
        self.assertEqual(len((self.store / "events.jsonl").read_text().splitlines()), 2)

    def test_candidate_is_kept_out_of_steering_until_activated(self):
        evidence = learn.capture(self.store, self.observation)
        rule = self.rule(evidence, status="candidate")
        learn.write_rule(self.store, rule)
        self.assertNotIn(rule["principle"], (self.store / "rules.md").read_text())
        self.assertTrue((self.store / "patterns/complete-the-scope.md").is_file())
        learn.write_rule(self.store, {**rule, "status": "active"})
        active = (self.store / "rules.md").read_text()
        self.assertIn(rule["principle"], active)
        self.assertNotIn(self.observation["user_text"], active)
        self.assertEqual(len(learn.read_state(self.store)["corrections"]), 1)

    def test_reinforcing_a_rule_retains_all_original_evidence(self):
        first = learn.capture(self.store, self.observation)
        learn.write_rule(self.store, self.rule(first))
        second = learn.capture(self.store, {**self.observation, "source": {"conversation": "another", "message": "turn-one"}})
        rule = self.rule(second)
        learn.write_rule(self.store, rule)
        self.assertEqual(set(learn.read_state(self.store)["rules"][rule["id"]]["evidence"]),
                         {first, second})
        before = (self.store / "events.jsonl").read_bytes()
        learn.write_rule(self.store, rule)
        self.assertEqual(before, (self.store / "events.jsonl").read_bytes())

    def test_missing_evidence_and_silent_scope_expansion_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing user evidence"):
            learn.write_rule(self.store, self.rule("invented"))
        evidence = learn.capture(self.store, self.observation)
        learn.write_rule(self.store, self.rule(evidence))
        before = (self.store / "events.jsonl").read_bytes()
        with self.assertRaisesRegex(ValueError, "Changing scope"):
            learn.write_rule(self.store, self.rule(evidence, scope={"kind": "repository", "value": "org/repo"}))
        self.assertEqual(before, (self.store / "events.jsonl").read_bytes())

    def test_supersession_and_retirement_preserve_evidence(self):
        evidence = learn.capture(self.store, self.observation)
        learn.write_rule(self.store, self.rule(evidence))
        learn.write_rule(self.store, self.rule(evidence, id="newer-scope-rule", supersedes=["complete-the-scope"]))
        state = learn.read_state(self.store)
        self.assertEqual(state["rules"]["complete-the-scope"]["status"], "superseded")
        self.assertNotIn("## complete-the-scope", (self.store / "rules.md").read_text())
        result = subprocess.run([sys.executable, str(SCRIPT), "--store", str(self.store),
                                 "retire", "newer-scope-rule", "--reason", "User reversed this preference"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(learn.read_state(self.store)["rules"]["newer-scope-rule"]["status"], "retired")
        self.assertIn(evidence, learn.read_state(self.store)["corrections"])

    def test_corrupt_ledger_is_reported_without_overwriting_evidence(self):
        learn.capture(self.store, self.observation)
        path = self.store / "events.jsonl"
        with path.open("a") as handle:
            handle.write('{"partial":')
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Invalid ledger at line 2"):
            learn.capture(self.store, self.observation)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.store / ".learn.lock").exists())

    def test_cli_detects_stale_steering_and_rebuilds_it(self):
        command = [sys.executable, str(SCRIPT), "--store", str(self.store)]
        capture = subprocess.run(command + ["capture", "--input", "-"],
                                 input=json.dumps(self.observation), capture_output=True, text=True)
        self.assertEqual(capture.returncode, 0, capture.stderr)
        (self.store / "rules.md").write_text("stale content")
        check = subprocess.run(command + ["check"], capture_output=True, text=True)
        self.assertEqual(check.returncode, 1)
        self.assertIn("stale", check.stderr)
        subprocess.run(command + ["render"], check=True, capture_output=True)
        subprocess.run(command + ["check"], check=True, capture_output=True)

    def test_native_pointers_preserve_existing_instructions_and_remove_cleanly(self):
        root = Path(self.temporary.name) / "dotfiles"
        (root / ".tkstack/steering").mkdir(parents=True)
        target = Path(self.temporary.name) / "project"
        target.mkdir()
        (target / "AGENTS.md").write_text("My project instructions\n")
        (target / "CLAUDE.md").write_text("@AGENTS.md\n")
        original = (target / "AGENTS.md").read_text()
        plan = steering_adapter.instruction_plan(root, target, ["codex", "claude"], "project")
        steering_adapter.apply_instructions(plan, dry_run=True)
        self.assertEqual((target / "AGENTS.md").read_text(), original)
        steering_adapter.apply_instructions(plan)
        self.assertTrue((target / "AGENTS.md").read_text().startswith(original))
        self.assertEqual(steering_adapter.instruction_plan(root, target, ["codex", "claude"], "project"), [])
        remove = steering_adapter.instruction_plan(root, target, ["codex", "claude"], "project", uninstall=True)
        steering_adapter.apply_instructions(remove)
        self.assertEqual((target / "AGENTS.md").read_text(), original)
        self.assertEqual((target / "CLAUDE.md").read_text(), "@AGENTS.md\n")

    def test_home_pointers_use_native_harness_locations(self):
        root = Path(self.temporary.name) / "dotfiles"
        (root / ".tkstack/steering").mkdir(parents=True)
        target = Path(self.temporary.name) / "test-home"
        plan = steering_adapter.instruction_plan(root, target, ["codex", "claude"], "home")
        self.assertEqual({p.relative_to(target) for p, _, _ in plan},
                         {Path(".codex/AGENTS.md"), Path(".claude/CLAUDE.md")})

    def test_principles_loading_does_not_require_a_correction_store(self):
        root = Path(self.temporary.name) / "principles-only"
        skill = root / "skills/tkstack-principles/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# Portable principles\n")
        target = Path(self.temporary.name) / "project"
        plan = steering_adapter.instruction_plan(root, target, ["claude"], "project")
        self.assertEqual(len(plan), 1)
        self.assertIn(str(target / ".agents/principles/SKILL.md"), plan[0][2])
        self.assertNotIn(".agents/steering/rules.md", plan[0][2])


if __name__ == "__main__":
    unittest.main()
