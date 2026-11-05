"""Exercise installation against temporary targets, never the user's home."""

import hashlib
import io
import os
import re
import tarfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from installer_stubs import (  # noqa: E402
    CURL_TARBALL as _CURL_TARBALL,
    CURL_UV as _CURL_UV,
    GIT_ORIGIN_STUB,
    UV_INSTALLER_BODY as _UV_INSTALLER_BODY,
    UV_STUB as _UV_STUB,
    stub_path as _stub_path,
)


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from skill_roots import load  # noqa: E402

install = load("install", ROOT / "scripts/install.py")


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
                                       Path(".agents"), Path(".grok/skills"),
                                       Path(".kimi/skills"),
                                       Path(".config/opencode/skills"),
                                       Path(".copilot/skills"),
                                       Path(".config/muse/skills")})

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
        for name in ("matt-tdd", "lever", "caveman", "fal-ai", "headroom", "open-design", "rtk",
                     "ub-mode", "emil-design-eng", "emil-prototype"):
            self.assertIn(name, shared)
            self.assertNotIn(name, claude | cursor)
        # Sources with native per-harness variants keep their own directories.
        for name in ("graphify", "impeccable"):
            self.assertIn(name, shared & claude & cursor)
        grok = by_directory[Path(".grok/skills")]
        self.assertIn("learn", grok)
        self.assertIn("matt-tdd", grok)
        self.assertNotIn("architect", grok)
        for relative in (Path(".copilot/skills"), Path(".config/muse/skills")):
            hosted = by_directory[relative]
            self.assertIn("learn", hosted)
            self.assertIn("matt-tdd", hosted)
            self.assertNotIn("architect", hosted)
            self.assertNotIn("graphify", hosted)
        self.assertIsNone(install.skill_directory("t3code"))
        self.assertEqual(install.skill_directory("copilot"), Path(".copilot/skills"))
        self.assertEqual(install.skill_directory("copilot", "project"), Path(".github/skills"))
        self.assertEqual(install.skill_directory("muse"), Path(".config/muse/skills"))
        self.assertEqual(install.skill_directory("muse", "project"), Path(".agents/skills"))
        self.assertEqual(install.skill_directory("opencode"), Path(".config/opencode/skills"))
        self.assertEqual(install.skill_directory("opencode", "project"), Path(".opencode/skills"))

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

    def test_uninstall_preserves_a_foreign_symlink_at_a_planned_destination(self):
        install.apply(self.plan)
        source, destination = next(pair for pair in self.plan if pair[1].parent.name == "skills" and ".grok" in pair[1].parts)
        destination.unlink()
        foreign = self.target / "not-this-checkout"
        destination.symlink_to(foreign)
        removed = install.apply(self.plan, uninstall=True)
        self.assertEqual(removed, self.expected_links - 1)
        self.assertTrue(destination.is_symlink())
        self.assertEqual(os.readlink(destination), str(foreign))

    def test_default_uninstall_removes_links_from_every_harness(self):
        install.apply(self.plan)
        foreign = self.target / ".grok" / "skills" / "foreign-skill"
        foreign.parent.mkdir(parents=True, exist_ok=True)
        foreign.symlink_to(self.target, target_is_directory=True)
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/install.py"), "--uninstall", "--target", str(self.target)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        for _, destination in self.plan:
            self.assertFalse(destination.exists() or destination.is_symlink())
        self.assertTrue(foreign.is_symlink())

    def test_opencode_project_scope_uses_the_project_skills_directory(self):
        project = self.target / "project"
        plan = install.link_plan(ROOT, project, ["opencode"], "project")
        parents = {destination.parent.relative_to(project) for _, destination in plan}
        self.assertIn(Path(".opencode/skills"), parents)
        self.assertNotIn(Path(".config/opencode/skills"), parents)

    def test_copilot_and_muse_project_scopes_use_their_native_directories(self):
        project = self.target / "project"
        copilot = install.link_plan(ROOT, project, ["copilot"], "project")
        copilot_parents = {destination.parent.relative_to(project) for _, destination in copilot}
        self.assertIn(Path(".github/skills"), copilot_parents)
        self.assertNotIn(Path(".copilot/skills"), copilot_parents)
        muse = install.link_plan(ROOT, project, ["muse"], "project")
        muse_parents = {destination.parent.relative_to(project) for _, destination in muse}
        self.assertIn(Path(".agents/skills"), muse_parents)
        self.assertNotIn(Path(".config/muse/skills"), muse_parents)
        both = install.link_plan(ROOT, project, ["codex", "muse"], "project")
        destinations = [destination for _, destination in both]
        self.assertEqual(len(destinations), len(set(destinations)))
        owned = project / ".github" / "skills" / "learn"
        owned.parent.mkdir(parents=True)
        owned.symlink_to(ROOT / "skills" / "learn", target_is_directory=True)
        stale = install.stale_links(ROOT, project, list(install.SKILL_PATHS), [], None)
        self.assertIn(owned, stale)

    def test_uninstall_removes_owned_legacy_muse_links_and_keeps_foreign_ones(self):
        legacy = self.target / ".muse" / "skills"
        legacy.mkdir(parents=True)
        owned = legacy / "learn"
        owned.symlink_to(ROOT / "skills" / "learn", target_is_directory=True)
        foreign = legacy / "other"
        foreign.symlink_to(self.target, target_is_directory=True)
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/install.py"), "--uninstall", "--target", str(self.target)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertFalse(owned.exists() or owned.is_symlink())
        self.assertTrue(foreign.is_symlink())
        self.assertEqual(os.readlink(foreign), str(self.target))

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
                     "chief-of-staff", "git-guardrails-claude-code", "learn",
                     "ub-mode", "emil-design-eng", "emil-prototype"):
            self.assertIn(name, skills)
        self.assertEqual(skills["emil-prototype"],
                         (ROOT / ".tkstack/emil-kowalski/skills/prototype").resolve())
        self.assertEqual(skills["prototype"],
                         (ROOT / ".tkstack/matt-pocock/skills/engineering/prototype").resolve())
        self.assertIn("\nname: prototype\n",
                      (ROOT / "vendor/emil-kowalski/skills/prototype/SKILL.md").read_text())
        self.assertIn("\nname: emil-prototype\n",
                      (skills["emil-prototype"] / "SKILL.md").read_text())

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
            if harness == "cursor":
                self.assertIn(".agents/principles/SKILL.md", (target / ".cursor/rules/tkstack-steering.mdc").read_text())
            self.assertEqual(install.apply(plan), 0)
            install.apply(plan, uninstall=True)
            self.assertFalse(shared.is_symlink())
            self.assertTrue((ROOT / "skills/tkstack-principles/SKILL.md").is_file())

    def test_install_into_own_checkout_preserves_portable_instruction_sources(self):
        checkout = self.target / 'self checkout'
        checkout.mkdir()
        for directory in ('vendor', 'scripts', 'src', 'harnesses', 'skills'):
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
        self.assertTrue((checkout / '.agents/principles').is_symlink())

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
        for directory in ("vendor", "scripts", "src", "harnesses", "skills"):
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
        self.assertTrue((target / ".agents/steering").is_symlink())
        again = subprocess.run(command, check=True, capture_output=True, text=True)
        self.assertIn("0 link(s) changed.", again.stdout)



class InstallerPrerequisiteTests(unittest.TestCase):
    """PATH stubs stand in for a host with no Python 3.11+ or no Git."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / "home with spaces"
        self.home.mkdir()
        self.uv_log = self.base / "uv.log"
        self.curl_log = self.base / "curl.log"
        self.install_log = self.base / "install.log"

    def _env(self, path):
        environment = os.environ.copy()
        environment.update({
            "HOME": str(self.home),
            "PATH": path,
            "UV_LOG": str(self.uv_log),
            "CURL_LOG": str(self.curl_log),
            "INSTALL_LOG": str(self.install_log),
            "GIT_LOG": str(self.base / "git.log"),
        })
        environment.pop("TKSTACK_PYTHON", None)
        environment.pop("UV_INSTALL_DIR", None)
        environment.pop("TKSTACK_HOME", None)
        environment.pop("TKSTACK_REPO", None)
        environment.pop("TKSTACK_TARBALL", None)
        environment.pop("TKSTACK_TRUST_HOME", None)
        environment.pop("BAD_TAR", None)
        environment.pop("UV_INSTALLER_FILE", None)
        environment.pop("CURL_ACCEPT", None)
        environment.pop("FAIL_MV_DEST", None)
        environment.pop("REAL_MV", None)
        environment.pop("MV_LOG", None)
        return environment

    def _installer_body(self):
        path = self.base / "uv-installer.sh"
        path.write_text(_UV_INSTALLER_BODY)
        return path

    def _pinned_checkout(self, digest=None):
        checkout = self.base / "checkout"
        (checkout / "scripts").mkdir(parents=True)
        text = (ROOT / "install.sh").read_text()
        if digest:
            pin = "UV_INSTALLER_SHA256=b8e6c43099ee9f9a550984d3ad56948457c689e7a99c090b35377234ac241491"
            text = text.replace(pin, "UV_INSTALLER_SHA256=" + digest, 1)
        script = checkout / "install.sh"
        script.write_text(text)
        script.chmod(0o755)
        (checkout / "scripts" / "install.py").write_text("raise SystemExit(0)\n")
        return script

    def _run(self, script, path, *arguments, extra=None):
        environment = self._env(path)
        if extra:
            environment.update(extra)
        return subprocess.run(
            ["bash", str(script), *arguments],
            cwd=self.base,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def test_readme_pins_match_the_installer(self):
        script = (ROOT / "install.sh").read_text()
        readme = (ROOT / "README.md").read_text()
        bootstrap = (ROOT / "docs" / "bootstrap.md").read_text()
        for token in (
            "0.12.23",
            "3.12.15",
            "b8e6c43099ee9f9a550984d3ad56948457c689e7a99c090b35377234ac241491",
        ):
            self.assertIn(token, script)
            self.assertIn(token, readme)
            self.assertIn(token, bootstrap)
        self.assertTrue(script.rstrip().endswith('main "$@"'))
        self.assertNotIn("uv/install.sh |", script)
        self.assertIsNone(re.search(r"(?m)^\s*mv -T\b", script))
        self.assertIsNone(re.search(r"(?m)^\s*realpath\b", script))
        install = readme.split("## Develop", 1)[0]
        self.assertEqual(install.count("```sh"), 1)

    def test_truncated_installer_does_not_run_a_prefix(self):
        text = (ROOT / "install.sh").read_text()
        partial = self.base / "partial.sh"
        partial.write_text(text[:text.rfind('main "$@"')])
        path = _stub_path(self.base / "bins", ("python", "uv", "git"), {"curl": _CURL_TARBALL})
        result = self._run(partial, path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.home / ".local" / "share" / "tkstack").exists())
        self.assertFalse(self.curl_log.exists())

    def test_missing_python_uses_uv_without_installing_uv(self):
        path = _stub_path(self.base / "bins", ("python", "uv"), {"uv": _UV_STUB, "curl": "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$CURL_LOG\"\nexit 1\n"})
        target = self.base / "target"
        result = self._run(ROOT / "install.sh", path, "--dry-run", "--target", str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        log = self.uv_log.read_text()
        self.assertIn("python install 3.12.15", log)
        self.assertIn("run --python 3.12.15 --no-project -- python -B ", log)
        self.assertIn(str(ROOT / "scripts" / "install.py"), log)
        self.assertIn("--dry-run", log)
        self.assertNotIn("requires Python 3.11+", result.stderr)
        self.assertFalse(self.curl_log.exists())

    def test_missing_python_and_uv_bootstraps_the_pinned_uv_installer(self):
        body = self._installer_body()
        digest = hashlib.sha256(body.read_bytes()).hexdigest()
        path = _stub_path(self.base / "bins", ("python", "uv"), {"curl": _CURL_UV})
        poison = self.base / "poison-bin"
        script = self._pinned_checkout(digest)
        result = self._run(
            script, path, "--dry-run", "--target", str(self.base / "target"),
            extra={"UV_INSTALLER_FILE": str(body), "UV_INSTALL_DIR": str(poison)},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("https://astral.sh/uv/0.12.23/install.sh", self.curl_log.read_text())
        self.assertIn(" -o ", " " + self.curl_log.read_text())
        log = self.uv_log.read_text()
        self.assertIn("python install 3.12.15", log)
        self.assertIn("run --python 3.12.15", log)
        installed = self.home / ".local" / "bin" / "uv"
        self.assertTrue(installed.is_file())
        self.assertFalse(poison.exists())
        self.assertNotIn("requires Python 3.11+", result.stderr)

    def test_uv_installer_sha256_mismatch_does_not_run_it(self):
        body = self._installer_body()
        path = _stub_path(self.base / "bins", ("python", "uv"), {"curl": _CURL_UV, "sh": "#!/bin/sh\nprintf '%s\\n' ran-sh >> \"$UV_LOG\"\nexit 0\n"})
        script = self._pinned_checkout()
        result = self._run(script, path, extra={"UV_INSTALLER_FILE": str(body)})
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("sha256", result.stderr)
        self.assertFalse((self.home / ".local" / "bin" / "uv").exists())
        self.assertFalse(self.uv_log.exists())

    def test_missing_git_downloads_the_repository_tarball(self):
        path = _stub_path(self.base / "bins", ("git",), {"curl": _CURL_TARBALL})
        script = self.base / "downloaded-install.sh"
        script.write_text((ROOT / "install.sh").read_text())
        script.chmod(0o755)
        result = self._run(script, path, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("https://codeload.github.com/Tyler-R-Kendrick/tkstack/tar.gz/main", self.curl_log.read_text())
        self.assertIn("local-install --dry-run", self.install_log.read_text())
        checkout = self.home / ".local" / "share" / "tkstack"
        self.assertTrue((checkout / "install.sh").is_file())
        receipt = (checkout / ".tkstack" / "source-receipt.txt").read_text()
        self.assertIn("kind=tarball", receipt)
        (checkout / ".tkstack" / "keep").write_text("state\n")
        refused = self._run(script, path, "--check")
        self.assertNotEqual(refused.returncode, 0, refused.stdout + refused.stderr)
        self.assertIn("Refusing to run it", refused.stderr)
        self.assertIn("TKSTACK_TRUST_HOME", refused.stderr)
        self.assertEqual(self.curl_log.read_text().count("codeload.github.com"), 1)
        self.assertNotIn("local-install --check", self.install_log.read_text())
        self.assertEqual((checkout / ".tkstack" / "keep").read_text(), "state\n")
        again = self._run(script, path, "--check", extra={"TKSTACK_TRUST_HOME": "1"})
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertIn("frozen", again.stderr)
        self.assertEqual(self.curl_log.read_text().count("codeload.github.com"), 2)
        self.assertIn("local-install --check", self.install_log.read_text())
        self.assertEqual((checkout / ".tkstack" / "keep").read_text(), "state\n")

    def _bad_archive(self, name, build):
        archive = self.base / name
        with tarfile.open(archive, "w:gz") as tar:
            build(tar)
        return archive

    def _reject_archive(self, archive):
        path = _stub_path(self.base / "bins-bad", ("git", "realpath"), {"curl": _CURL_TARBALL})
        script = self.base / "downloaded-install.sh"
        if not script.exists():
            script.write_text((ROOT / "install.sh").read_text())
            script.chmod(0o755)
        result = self._run(script, path, extra={"BAD_TAR": str(archive)})
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.home / ".local" / "share" / "tkstack" / "install.sh").exists())
        return result

    def test_tarball_rejects_multiple_top_level_directories(self):
        def build(tar):
            for name in ("one/install.sh", "one/scripts/install.py", "two/extra.txt"):
                data = b"x\n"
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        result = self._reject_archive(self._bad_archive("multi.tar.gz", build))
        self.assertIn("more than one top-level", result.stderr)

    def test_tarball_rejects_parent_directory_members(self):
        def build(tar):
            data = b"nope\n"
            info = tarfile.TarInfo("../escape.txt")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        result = self._reject_archive(self._bad_archive("escape.tar.gz", build))
        self.assertIn("escapes", result.stderr)

    def test_tarball_rejects_a_symlink_that_leaves_the_extract_directory(self):
        def build(tar):
            for name, data in (("tkstack-main/install.sh", b"#!/bin/sh\n"), ("tkstack-main/scripts/install.py", b"print(1)\n")):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            link = tarfile.TarInfo("tkstack-main/outside")
            link.type = tarfile.SYMTYPE
            link.linkname = "/tmp"
            tar.addfile(link)
        result = self._reject_archive(self._bad_archive("link.tar.gz", build))
        self.assertIn("symlink escapes", result.stderr)

    def test_tarball_rejects_a_relative_symlink_that_leaves_the_extract_directory(self):
        def build(tar):
            for name, data in (("tkstack-main/install.sh", b"#!/bin/sh\n"), ("tkstack-main/scripts/install.py", b"print(1)\n")):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            link = tarfile.TarInfo("tkstack-main/outside")
            link.type = tarfile.SYMTYPE
            link.linkname = "../../../outside"
            tar.addfile(link)
        result = self._reject_archive(self._bad_archive("rel-link.tar.gz", build))
        self.assertIn("symlink escapes", result.stderr)

    def test_tarball_accepts_a_symlink_inside_the_extract_directory(self):
        def build(tar):
            for name, data in (("tkstack-main/install.sh", b"#!/bin/sh\n"), ("tkstack-main/scripts/install.py", b"print(1)\n")):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o755
                tar.addfile(info, io.BytesIO(data))
            link = tarfile.TarInfo("tkstack-main/inside")
            link.type = tarfile.SYMTYPE
            link.linkname = "scripts/install.py"
            tar.addfile(link)
        archive = self._bad_archive("inside-link.tar.gz", build)
        path = _stub_path(self.base / "bins-inside", ("git", "realpath"), {"curl": _CURL_TARBALL})
        script = self.base / "downloaded-install.sh"
        script.write_text((ROOT / "install.sh").read_text())
        script.chmod(0o755)
        result = self._run(script, path, extra={"BAD_TAR": str(archive)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.home / ".local" / "share" / "tkstack" / "install.sh").is_file())

    def test_tarball_url_must_be_https(self):
        path = _stub_path(self.base / "bins-scheme", ("git",), {"curl": _CURL_TARBALL})
        script = self.base / "downloaded-install.sh"
        script.write_text((ROOT / "install.sh").read_text())
        script.chmod(0o755)
        for url in ("http://example.com/tk.tar.gz", "file:///tmp/tk.tar.gz", "/tmp/tk.tar.gz"):
            result = self._run(script, path, extra={"TKSTACK_TARBALL": url})
            self.assertNotEqual(result.returncode, 0, url + result.stdout + result.stderr)
            self.assertIn("https://", result.stderr)
        self.assertFalse(self.curl_log.exists())
        accepted = "https://example.com/tkstack.tar.gz"
        result = self._run(script, path, extra={"TKSTACK_TARBALL": accepted, "CURL_ACCEPT": accepted})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(accepted, self.curl_log.read_text())

    def test_receipt_alone_does_not_run_a_preexisting_checkout(self):
        dest = self.home / ".local" / "share" / "tkstack"
        (dest / "scripts").mkdir(parents=True)
        (dest / "scripts" / "install.py").write_text("print(1)\n")
        (dest / "install.sh").write_text("#!/bin/sh\nprintf '%s\\n' PLANTED >> \"$INSTALL_LOG\"\n")
        (dest / "install.sh").chmod(0o755)
        (dest / ".tkstack").mkdir()
        (dest / ".tkstack" / "source-receipt.txt").write_text(
            "kind=tarball\n"
            "repo=https://github.com/Tyler-R-Kendrick/tkstack\n"
            "url=https://codeload.github.com/Tyler-R-Kendrick/tkstack/tar.gz/main\n"
        )
        (dest / ".tkstack" / "keep").write_text("state\n")
        path = _stub_path(self.base / "bins-plant", ("git",), {"curl": _CURL_TARBALL})
        script = self.base / "downloaded-install.sh"
        script.write_text((ROOT / "install.sh").read_text())
        script.chmod(0o755)
        refused = self._run(script, path)
        self.assertNotEqual(refused.returncode, 0, refused.stdout + refused.stderr)
        self.assertIn("Refusing to run it", refused.stderr)
        self.assertFalse(self.install_log.exists())
        self.assertEqual((dest / "install.sh").read_text().splitlines()[0], "#!/bin/sh")
        self.assertEqual((dest / ".tkstack" / "keep").read_text(), "state\n")
        trusted = self._run(script, path, extra={"TKSTACK_TRUST_HOME": "1"})
        self.assertEqual(trusted.returncode, 0, trusted.stdout + trusted.stderr)
        self.assertIn("local-install", self.install_log.read_text())
        self.assertNotIn("PLANTED", self.install_log.read_text())
        self.assertEqual((dest / ".tkstack" / "keep").read_text(), "state\n")

    def test_matching_git_origin_runs_without_trust_and_a_mismatch_does_not(self):
        dest = self.home / ".local" / "share" / "tkstack"
        (dest / "scripts").mkdir(parents=True)
        (dest / "scripts" / "install.py").write_text("print(1)\n")
        (dest / "install.sh").write_text("#!/bin/sh\nprintf '%s\\n' \"PLANTED $*\" >> \"$INSTALL_LOG\"\n")
        (dest / "install.sh").chmod(0o755)
        (dest / ".git").mkdir()
        path = _stub_path(self.base / "bins-origin", ("git",), {"git": GIT_ORIGIN_STUB})
        script = self.base / "downloaded-install.sh"
        script.write_text((ROOT / "install.sh").read_text())
        script.chmod(0o755)
        mismatch = self._run(script, path, "--dry-run", extra={"GIT_ORIGIN": "https://example.com/other.git"})
        self.assertNotEqual(mismatch.returncode, 0, mismatch.stdout + mismatch.stderr)
        self.assertIn("Refusing to run it", mismatch.stderr)
        self.assertFalse(self.install_log.exists())
        self.assertNotIn("pull", (self.base / "git.log").read_text())
        trusted = self._run(
            script, path, "--dry-run",
            extra={"GIT_ORIGIN": "https://example.com/other.git", "TKSTACK_TRUST_HOME": "1"},
        )
        self.assertEqual(trusted.returncode, 0, trusted.stdout + trusted.stderr)
        self.assertIn("PLANTED --dry-run", self.install_log.read_text())
        self.assertNotIn("pull", (self.base / "git.log").read_text())
        self.install_log.unlink()
        matched = self._run(
            script, path, "--check",
            extra={"GIT_ORIGIN": "https://github.com/Tyler-R-Kendrick/tkstack.git"},
        )
        self.assertEqual(matched.returncode, 0, matched.stdout + matched.stderr)
        self.assertIn("PLANTED --check", self.install_log.read_text())
        self.assertIn("pull", (self.base / "git.log").read_text())

    def test_failed_replacement_restores_the_previous_checkout(self):
        path = _stub_path(self.base / "bins-restore", ("git", "realpath"), {"curl": _CURL_TARBALL})
        script = self.base / "downloaded-install.sh"
        script.write_text((ROOT / "install.sh").read_text())
        script.chmod(0o755)
        first = self._run(script, path, "--dry-run")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        checkout = self.home / ".local" / "share" / "tkstack"
        (checkout / ".tkstack" / "keep").write_text("state\n")
        (checkout / "install.sh").write_text("#!/bin/sh\nprintf '%s\\n' ORIGINAL\n")
        real_mv = shutil.which("mv")
        mv_log = self.base / "mv.log"
        blocker = r"""#!/bin/sh
dest=
for arg in "$@"; do
  case "$arg" in
    --) ;;
    *) dest=$arg ;;
  esac
done
if [ "$dest" = "$FAIL_MV_DEST" ] && [ ! -f "$MV_LOG" ]; then
  printf '%s\n' "blocked $dest" >> "$MV_LOG"
  exit 1
fi
exec "$REAL_MV" "$@"
"""
        blocked = _stub_path(
            self.base / "bins-mv", ("git", "realpath"),
            {"curl": _CURL_TARBALL, "mv": blocker},
        )
        failed = self._run(
            script, blocked, "--dry-run",
            extra={
                "TKSTACK_TRUST_HOME": "1",
                "FAIL_MV_DEST": str(checkout),
                "REAL_MV": real_mv,
                "MV_LOG": str(mv_log),
            },
        )
        self.assertNotEqual(failed.returncode, 0, failed.stdout + failed.stderr)
        self.assertIn("restored", failed.stderr)
        self.assertEqual((checkout / ".tkstack" / "keep").read_text(), "state\n")
        self.assertIn("ORIGINAL", (checkout / "install.sh").read_text())
        self.assertTrue(mv_log.is_file())

    def test_chatty_uv_installer_does_not_pollute_the_uv_path(self):
        body = self.base / "uv-installer.sh"
        body.write_text(_UV_INSTALLER_BODY + "\nprintf '%s\\n' 'chatty installer revision'\n")
        digest = hashlib.sha256(body.read_bytes()).hexdigest()
        path = _stub_path(self.base / "bins-chatty", ("python", "uv"), {"curl": _CURL_UV})
        script = self._pinned_checkout(digest)
        result = self._run(script, path, "--dry-run", "--target", str(self.base / "target"), extra={"UV_INSTALLER_FILE": str(body)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("chatty installer revision", result.stderr)
        log = self.uv_log.read_text()
        self.assertIn("python install 3.12.15", log)
        self.assertNotIn("chatty", log)


if __name__ == "__main__":
    unittest.main()
