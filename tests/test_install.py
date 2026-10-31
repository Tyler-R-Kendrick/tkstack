"""Exercise installation against temporary targets, never the user's home."""

import importlib.util
import re
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import shutil
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("install", ROOT / "scripts/install.py")
install = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install)


class InstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install.prepare_aliases(ROOT)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        redirect = redirect_stdout(StringIO())
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)
        self.target = Path(self.temporary.name)
        self.plan = install.link_plan(ROOT, self.target, list(install.SKILL_PATHS))
        self.expected_links = len(self.plan)

    def test_pinned_snapshot_is_complete_and_unchanged(self):
        install.verify_vendor(ROOT)
        self.assertEqual(len(list((ROOT / "vendor/pstack/skills").glob("*/SKILL.md"))), 34)
        destinations = {destination.parent.relative_to(self.target)
                        for _, destination in self.plan}
        self.assertEqual(destinations, {Path(".agents/skills"), Path(".claude/skills"),
                                       Path(".cursor/skills"), Path(".claude/agents"),
                                       Path(".cursor/agents"), Path(".cursor/rules"),
                                       Path(".agents")})

    def test_install_preserves_references_and_is_repeatable(self):
        self.assertEqual(install.apply(self.plan), self.expected_links)
        self.assertEqual(install.apply(self.plan), 0)
        for source, destination in self.plan:
            self.assertTrue(install.matches(destination, source))
        reference = self.target / ".cursor/skills/architect/references/runner-prompt.md"
        self.assertTrue(reference.is_file())
        script = self.target / ".cursor/skills/show-me-your-work/scripts/log.sh"
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_skills_install_into_the_directory_matching_their_origin(self):
        by_directory = {}
        for _, destination in self.plan:
            by_directory.setdefault(destination.parent.relative_to(self.target), set()).add(destination.name)
        shared, claude, cursor = (by_directory[Path(p)] for p in
                                  (".agents/skills", ".claude/skills", ".cursor/skills"))
        developed = {path.name for path in (ROOT / "skills").iterdir() if (path / "SKILL.md").is_file()}
        self.assertLessEqual(developed, shared & claude & cursor)
        # Learn's packaged subskills are subcommands, not separately installed skills.
        for name in ("codify", "flowify", "hookify", "instructify", "lintify", "reusify", "skillify"):
            self.assertNotIn(name, shared | claude | cursor)
        # Pstack and its Cursor Team Kit dependency are Cursor packages.
        for name in ("architect", "deslop", "pstack-unslop"):
            self.assertIn(name, cursor)
            self.assertNotIn(name, shared | claude)
        # Harness-independent upstream and third-party-derived skills stay shared.
        for name in ("matt-tdd", "lever", "caveman", "fal-ai", "headroom", "open-design", "rtk"):
            self.assertIn(name, shared)
            self.assertNotIn(name, claude | cursor)
        # Sources with native per-harness variants keep their own directories.
        for name in ("graphify", "impeccable"):
            self.assertIn(name, shared & claude & cursor)

    def test_reinstall_removes_links_outside_their_new_placement(self):
        install.apply(self.plan)
        moved = self.target / ".claude/skills/architect"
        moved.symlink_to(ROOT / "vendor/pstack/skills/architect", target_is_directory=True)
        foreign = self.target / ".claude/skills/someone-elses"
        foreign.symlink_to(self.target, target_is_directory=True)
        stale = install.stale_links(ROOT, self.target, list(install.SKILL_PATHS), self.plan)
        self.assertEqual(stale, [moved])
        self.assertEqual(install.remove_stale(stale), 1)
        self.assertFalse(moved.is_symlink())
        self.assertTrue(foreign.is_symlink())

    def test_collision_stops_before_creating_other_links(self):
        _, destination = self.plan[-1]
        destination.parent.mkdir(parents=True)
        destination.write_text("my existing agent")
        with self.assertRaisesRegex(ValueError, "Refusing to replace"):
            install.apply(self.plan)
        self.assertFalse(self.plan[0][1].exists())
        self.assertEqual(destination.read_text(), "my existing agent")

    def test_dangling_foreign_link_is_preserved(self):
        _, destination = self.plan[-1]
        destination.parent.mkdir(parents=True)
        destination.symlink_to(self.target / "missing")
        with self.assertRaisesRegex(ValueError, "Refusing to replace"):
            install.apply(self.plan)
        self.assertTrue(destination.is_symlink())
        self.assertFalse(self.plan[0][1].exists())

    def test_preview_has_no_side_effects(self):
        self.assertEqual(install.apply(self.plan, dry_run=True), self.expected_links)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_invalid_parent_stops_before_creating_other_links(self):
        parent = self.plan[-1][1].parent
        parent.parent.mkdir(parents=True)
        parent.symlink_to(self.target / "missing-directory")
        with self.assertRaisesRegex(ValueError, "not a directory"):
            install.apply(self.plan)
        self.assertFalse(self.plan[0][1].exists())

    def test_uninstall_preserves_unrelated_content(self):
        install.apply(self.plan)
        _, destination = self.plan[-1]
        destination.unlink()
        destination.write_text("replacement agent")
        self.assertEqual(install.apply(self.plan, uninstall=True), self.expected_links - 1)
        self.assertEqual(destination.read_text(), "replacement agent")
        self.assertEqual(install.apply(self.plan, uninstall=True), 0)

    def test_personal_skills_and_agents_join_the_installation(self):
        personal = self.target / "dotfiles"
        (personal / "skills/example").mkdir(parents=True)
        (personal / "skills/example/SKILL.md").write_text("a personal skill")
        (personal / "agents").mkdir()
        (personal / "agents/my-agent.md").write_text("a personal agent")
        plan = install.link_plan(personal, self.target / "project", ["cursor"])
        self.assertEqual({destination.name for _, destination in plan},
                         {"example", "my-agent.md"})

    def test_every_collection_is_installed_with_unique_matching_names(self):
        skills = install.collect(ROOT, "skills")
        self.assertGreaterEqual(len(skills), 100)
        for name, path in skills.items():
            text = (path / "SKILL.md").read_text()
            declared = re.search(r"^name:\s*(.*)$", text, re.M).group(1)
            self.assertEqual(declared.strip().strip('\"\''), name)
        self.assertEqual(skills["tdd"], ROOT / "vendor/pstack/skills/tdd")
        for name in ("full-send", "full-stop", "ask-matt", "matt-tdd", "deslop",
                     "chief-of-staff", "git-guardrails-claude-code", "learn"):
            self.assertIn(name, skills)

    def test_alias_updates_matt_workflows_and_preserves_relative_references(self):
        skills = install.collect(ROOT, "skills")
        implement = (skills["implement"] / "SKILL.md").read_text()
        self.assertIn('Skill tool with "matt-tdd"', implement)
        tdd = skills["matt-tdd"]
        for reference in ("tests.md", "mocking.md", "agents/openai.yaml"):
            self.assertTrue((tdd / reference).is_file())
        original = ROOT / "vendor/matt-pocock/skills/engineering/tdd/SKILL.md"
        self.assertIn("\nname: tdd\n", original.read_text())
        text = '`tdd` /tdd $tdd "tdd" [TDD](../tdd/SKILL.md)'
        self.assertEqual(install.rewrite_invocations(text, {"tdd": "matt-tdd"}),
                         '`matt-tdd` /matt-tdd $matt-tdd "matt-tdd" [TDD](../tdd/SKILL.md)')

    def test_principles_are_shared_and_readable_without_codex_installation(self):
        for harness in ("claude", "cursor"):
            target = self.target / harness
            plan = install.link_plan(ROOT, target, [harness])
            install.apply(plan)
            shared = target / ".agents/principles"
            self.assertEqual(shared.resolve(), ROOT / "skills/tkstack-principles")
            self.assertEqual((target / install.SKILL_PATHS[harness] / "tkstack-principles").resolve(), shared.resolve())
            self.assertFalse((target / ".agents/skills").exists())
            for relative in re.findall(r"\]\((references/[^)]+)\)", (shared / "SKILL.md").read_text()):
                self.assertTrue((shared / relative).is_file())
            if harness == "claude":
                from steering_adapter import apply_instructions, instruction_plan
                apply_instructions(instruction_plan(ROOT, target, [harness], "project"))
                self.assertIn(str(shared / "SKILL.md"), (target / "CLAUDE.md").read_text())
            else:
                self.assertIn(".agents/principles/SKILL.md", (target / ".cursor/rules/tkstack-steering.mdc").read_text())
            self.assertEqual(install.apply(plan), 0)
            install.apply(plan, uninstall=True)
            self.assertFalse(shared.is_symlink())
            self.assertTrue((ROOT / "skills/tkstack-principles/SKILL.md").is_file())

    def test_principles_pointer_roundtrip_preserves_home_instructions(self):
        from steering_adapter import apply_instructions, instruction_plan
        for path in (self.target / ".codex/AGENTS.md", self.target / ".claude/CLAUDE.md"):
            path.parent.mkdir(parents=True)
            path.write_text("Keep my existing instructions.\n")
        harnesses = ["codex", "claude"]
        apply_instructions(instruction_plan(ROOT, self.target, harnesses, "home"))
        self.assertEqual(instruction_plan(ROOT, self.target, harnesses, "home"), [])
        apply_instructions(instruction_plan(ROOT, self.target, harnesses, "home", uninstall=True))
        for path in (self.target / ".codex/AGENTS.md", self.target / ".claude/CLAUDE.md"):
            self.assertEqual(path.read_text(), "Keep my existing instructions.\n")

    def test_self_project_steering_survives_relocation_and_keeps_foreign_ownership(self):
        from steering_adapter import apply_instructions, instruction_plan
        root = self.target / 'dotfiles'
        for name in ('learn', 'tkstack-principles', 'unslop'):
            directory = root / 'skills' / name
            directory.mkdir(parents=True)
            (directory / 'SKILL.md').write_text('Fixture skill\n')
        (root / 'skills/learn/scripts').mkdir()
        (root / 'skills/learn/scripts/learn.py').write_text('# Fixture helper\n')
        (root / 'AGENTS.md').write_text('Keep repository guidance.\n')
        (root / 'CLAUDE.md').write_text('@AGENTS.md\n')
        apply_instructions(instruction_plan(root, root, ['codex', 'claude'], 'project'))
        for name in ('AGENTS.md', 'CLAUDE.md'):
            text = (root / name).read_text()
            self.assertIn('tkstack:steering:source repository', text)
            self.assertNotIn(str(root), text)
            self.assertIn('`.agents/steering/rules.md`', text)
        relocated = self.target / 'relocated'
        shutil.copytree(root, relocated)
        self.assertEqual(instruction_plan(relocated, relocated, ['codex', 'claude'], 'project'), [])
        foreign = self.target / 'foreign'
        foreign.mkdir()
        shutil.copyfile(relocated / 'AGENTS.md', foreign / 'AGENTS.md')
        before = (foreign / 'AGENTS.md').read_bytes()
        with self.assertRaisesRegex(ValueError, 'another checkout'):
            instruction_plan(relocated, foreign, ['codex'], 'project')
        self.assertEqual((foreign / 'AGENTS.md').read_bytes(), before)
        self.assertEqual(instruction_plan(relocated, foreign, ['codex'], 'project', uninstall=True), [])

    def test_self_project_migrates_only_its_own_legacy_steering_block(self):
        import hashlib
        from steering_adapter import apply_instructions, instruction_plan
        root = self.target / 'dotfiles'
        (root / 'skills/learn').mkdir(parents=True)
        (root / 'skills/learn/SKILL.md').write_text('Fixture skill\n')
        identity = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]
        path = root / 'AGENTS.md'
        path.write_text('Keep guidance.\n<!-- tkstack:steering:start -->\n<!-- tkstack:steering:source ' + identity + ' -->\nOld pointer\n<!-- tkstack:steering:end -->\n')
        apply_instructions(instruction_plan(root, root, ['codex'], 'project'))
        self.assertIn('tkstack:steering:source repository', path.read_text())
        self.assertTrue(path.read_text().startswith('Keep guidance.\n'))
        path.write_text(path.read_text().replace('source repository', 'source unrelated-checkout'))
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'another checkout'):
            instruction_plan(root, root, ['codex'], 'project')
        self.assertEqual(path.read_bytes(), before)

    def test_rendered_learning_command_executes_from_a_source_path_with_spaces(self):
        import json
        import shlex
        from steering_adapter import instruction_plan
        source = self.target / 'dotfiles source'
        helper = source / 'skills/learn/scripts/learn.py'
        helper.parent.mkdir(parents=True)
        (source / 'skills/learn/SKILL.md').write_text('Fixture skill\n')
        helper.write_text('import json,sys\nprint(json.dumps(sys.argv[1:]))\n')
        changes = instruction_plan(source, self.target / 'installed home', ['codex'], 'home')
        line = next(line for line in changes[0][2].splitlines() if line.startswith('Use `python3 '))
        command = line[len('Use `'):].split('` for layered steering.')[0]
        executed = subprocess.run(shlex.split(command), capture_output=True, text=True)
        self.assertEqual(executed.returncode, 0, executed.stderr)
        self.assertEqual(json.loads(executed.stdout), ['show', '--all-scopes'])

    def test_install_into_own_checkout_preserves_portable_instruction_sources(self):
        checkout = self.target / 'self checkout'
        checkout.mkdir()
        for directory in ('vendor', 'scripts', 'harnesses', 'skills'):
            shutil.copytree(ROOT / directory, checkout / directory, symlinks=True,
                            ignore=shutil.ignore_patterns('__pycache__', 'node_modules'))
        for name in ('sources.lock.json', 'AGENTS.md', 'CLAUDE.md'):
            shutil.copy2(ROOT / name, checkout / name)
        before = {name: (checkout / name).read_bytes() for name in ('AGENTS.md', 'CLAUDE.md')}
        command = [sys.executable, str(checkout / 'scripts/install.py'), '--target', str(checkout),
                   '--harness', 'codex', '--harness', 'claude']
        installed = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        for name, data in before.items():
            self.assertEqual((checkout / name).read_bytes(), data)
        checked = subprocess.run([sys.executable, str(checkout / 'scripts/doctor.py'), '--target', str(checkout),
                                  '--harness', 'codex', '--harness', 'claude'], capture_output=True, text=True, timeout=60)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_unslop_personal_ownership_preserves_pstack_and_migrates_only_owned_links(self):
        skills = install.collect(ROOT, "skills")
        self.assertEqual(skills["unslop"], ROOT / "skills/unslop")
        self.assertIn("name: pstack-unslop", (skills["pstack-unslop"] / "SKILL.md").read_text())
        self.assertIn("name: unslop", (ROOT / "vendor/pstack/skills/unslop/SKILL.md").read_text())
        migrations = install.alias_migrations(ROOT, self.target, list(install.SKILL_PATHS))
        for harness, directory in install.SKILL_PATHS.items():
            old = self.target / directory / "unslop"
            old.parent.mkdir(parents=True, exist_ok=True)
            old.symlink_to(ROOT / "vendor/pstack/skills/unslop", target_is_directory=True)
        install.apply(self.plan, migrations=migrations)
        self.assertEqual(install.apply(self.plan, migrations=migrations), 0)
        for directory in install.SKILL_PATHS.values():
            self.assertEqual((self.target / directory / "unslop").resolve(), ROOT / "skills/unslop")
        destination = self.target / install.SKILL_PATHS["codex"] / "unslop"
        destination.unlink()
        destination.symlink_to(self.target / "foreign-unslop")
        with self.assertRaisesRegex(ValueError, "Refusing to replace"):
            install.apply(self.plan, migrations=migrations)
        self.assertEqual(destination.readlink(), self.target / "foreign-unslop")

    def test_fresh_checkout_installs_without_a_preexisting_alias_view(self):
        checkout = self.target / "checkout"
        checkout.mkdir()
        for directory in ("vendor", "scripts", "harnesses", "skills"):
            shutil.copytree(ROOT / directory, checkout / directory, symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(ROOT / "sources.lock.json", checkout / "sources.lock.json")
        target = self.target / "installation"
        command = [sys.executable, str(checkout / "scripts/install.py"),
                   "--target", str(target)]
        subprocess.run(command + ["--dry-run"], check=True, capture_output=True)
        self.assertFalse((checkout / ".tkstack").exists())
        self.assertFalse(target.exists())
        subprocess.run(command, check=True, capture_output=True)
        self.assertTrue((target / ".agents/skills/matt-tdd/SKILL.md").is_file())
        result = subprocess.run([sys.executable, str(checkout / "scripts/doctor.py"),
                                 "--target", str(target)], check=True,
                                capture_output=True, text=True)
        self.assertIn("installed links", result.stdout)
        self.assertTrue((target / ".agents/steering/rules.md").is_file())
        self.assertIn("tkstack:steering:start", (target / "AGENTS.md").read_text())
        again = subprocess.run(command, check=True, capture_output=True, text=True)
        self.assertIn("0 link(s) changed.", again.stdout)


if __name__ == "__main__":
    unittest.main()
