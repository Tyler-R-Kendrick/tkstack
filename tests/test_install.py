"""Exercise installation against temporary targets, never the user's home."""

import hashlib
import io
import json
import os
import platform
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
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from installer_stubs import (  # noqa: E402
    CURL_TARBALL as _CURL_TARBALL,
    CURL_UV as _CURL_UV,
    GIT_ORIGIN_STUB,
    UV_STUB as _UV_STUB,
    stub_path as _stub_path,
)


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from skill_roots import load  # noqa: E402

install = load("install", ROOT / "scripts/install.py")


def _env_without_uv():
    """Drop uv and uvx so a real install.py run cannot fetch Serena or write ~/.serena."""
    kept = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        directory = Path(entry)
        if any((directory / name).exists() for name in ("uv", "uvx", "uv.exe", "uvx.exe")):
            continue
        kept.append(entry)
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(kept)
    env["TKSTACK_OFFLINE"] = "1"
    return env


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
        self.assertEqual(len(list((ROOT / "vendor/pstack/skills").glob("*/SKILL.md"))), 58)
        destinations = {destination.parent.relative_to(self.target)
                        for _, destination in self.plan}
        self.assertEqual(destinations, {Path(".agents/skills"), Path(".claude/skills"),
                                       Path(".cursor/skills"), Path(".claude/agents"),
                                       Path(".cursor/agents"), Path(".cursor/rules"),
                                       Path(".agents"), Path(".tkstack"), Path(".grok/skills"),
                                       Path(".kimi/skills"),
                                       Path(".config/opencode/skills"),
                                       Path(".copilot/skills"),
                                       Path(".config/muse/skills")})

        skills = install.collect(ROOT, "skills")
        self.assertEqual(skills["tdd"], ROOT / "vendor/pstack/skills/tdd")
        self.assertIn("name: pstack-teach", (skills["pstack-teach"] / "SKILL.md").read_text())
        help_text = (skills["poteto-help"] / "SKILL.md").read_text()
        self.assertIn("`/pstack-teach`", help_text)
        self.assertIn("`/unslop`", help_text)
        self.assertNotIn("`/pstack-unslop`", help_text)
        self.assertTrue((skills["statechart"] / "scripts/statechart").stat().st_mode & 0o111)

    def test_current_sources_update_and_keep_the_previous_generation_on_failure(self):
        updater = load("latest_source_test", ROOT / "integrations/latest.py")
        repository = self.target / "upstream"
        repository.mkdir()
        subprocess.run(["git", "init", "-q", "--initial-branch=main", str(repository)], check=True)
        def commit(message):
            subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repository), "-c", "user.name=Fixture", "-c",
                            "user.email=fixture@example.invalid", "commit", "-qm", message], check=True)
        first = repository / "skills/example/SKILL.md"
        first.parent.mkdir(parents=True)
        first.write_text("first version\n")
        commit("first")
        checkout = self.target / "checkout"
        checkout.mkdir()
        catalog = {"sources": {"example": {"repository": "https://github.com/example/repo", "path": ".",
                                               "revision": "old-fixed-value", "files": {"skills/example/SKILL.md": {}}}}}
        (checkout / "sources.lock.json").write_text(json.dumps(catalog))
        rewrite = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "url." + repository.as_uri() + ".insteadOf",
                   "GIT_CONFIG_VALUE_0": "https://github.com/example/repo.git"}
        with patch.dict(os.environ, rewrite):
            initial = updater.prepare_sources(checkout)
            updater.publish(checkout / ".tkstack/cache/upstreams/current", initial)
            first.write_text("second version\n")
            added = repository / "skills/added/SKILL.md"
            added.parent.mkdir(parents=True)
            added.write_text("new skill\n")
            commit("second")
            updated = updater.prepare_sources(checkout)
            self.assertNotEqual(updated, initial)
            self.assertEqual((initial / "sources/example/skills/example/SKILL.md").read_text(), "first version\n")
            self.assertEqual((updated / "sources/example/skills/example/SKILL.md").read_text(), "second version\n")
            self.assertEqual((updated / "sources/example/skills/added/SKILL.md").read_text(), "new skill\n")
            updater.publish(checkout / ".tkstack/cache/upstreams/current", updated)
            self.assertEqual(updater.prepare_sources(checkout), updated)
            catalog["sources"]["example"]["paths"] = {"skills": "skills/example"}
            (checkout / "sources.lock.json").write_text(json.dumps(catalog))
            reselection = updater.prepare_sources(checkout)
            self.assertNotEqual(reselection, updated)
            self.assertFalse((reselection / "sources/example/skills/added/SKILL.md").exists())
            updater.publish(checkout / ".tkstack/cache/upstreams/current", reselection)
            (checkout / "skills").mkdir()
            (checkout / "skills/skills.json").write_text('{"aliases": {}}')
            changed_views = updater.prepare_sources(checkout)
            self.assertNotEqual(changed_views, reselection)
            updater.publish(checkout / ".tkstack/cache/upstreams/current", updated)
            with patch.dict(os.environ, {"GIT_CONFIG_KEY_0": "url." + (self.target / "missing").as_uri() + ".insteadOf",
                                        "GIT_CONFIG_VALUE_0": "https://github.com/unreachable/repo.git"}):
                catalog["sources"]["example"]["repository"] = "https://github.com/unreachable/repo"
                (checkout / "sources.lock.json").write_text(json.dumps(catalog))
                with self.assertRaises(ValueError):
                    updater.prepare_sources(checkout)
            self.assertEqual((checkout / ".tkstack/cache/upstreams/current").resolve(), updated)
            self.assertEqual((updated / "sources/example/skills/example/SKILL.md").read_text(), "second version\n")
        previous = checkout / ".tkstack/runtime/versions/previous"
        previous.mkdir(parents=True)
        (previous / "marker").write_text("working runtime")
        pointer = checkout / ".tkstack/runtime/current"
        updater.publish(pointer, previous)
        fake_uv = checkout / "uv"
        fake_uv.write_text("fixture")
        with patch.object(updater, "latest_node", return_value=("v1.2.3", "node-fixture")), \
             patch.object(updater, "current_uv", return_value=(fake_uv, "fixture")), \
             patch.object(updater, "current_python", return_value={}), \
             patch.object(updater, "runtime_current", return_value=None), \
             patch.object(updater, "python_runtime"), patch.object(updater, "binary_release"), \
             patch.object(updater, "install_node", side_effect=ValueError("download failed")):
            with self.assertRaisesRegex(ValueError, "download failed"):
                updater.prepare_runtime(checkout)
        self.assertEqual(pointer.resolve(), previous)
        self.assertEqual((pointer / "marker").read_text(), "working runtime")
        self.assertEqual(list((checkout / ".tkstack/runtime/versions").iterdir()), [previous])
        old_file, new_file = checkout / "old-skill", checkout / "new-skill"
        old_file.write_text("old")
        new_file.write_text("new")
        destination, added_link, stale = (self.target / name for name in ("existing", "added", "stale"))
        destination.symlink_to(old_file)
        stale.symlink_to(old_file)
        config = self.target / "instructions"
        config.write_text("before")
        plan = [(new_file, destination), (new_file, added_link)]
        edits = [(config, "before", "after")]
        state = updater.SimpleNamespace(source_generation=reselection, runtime_generation=previous, applied=True)
        with self.assertRaisesRegex(OSError, "simulated write failure"):
            with updater.apply_transaction(checkout, state, plan, [stale], edits,
                                           install.target_setup.instructify(ROOT).atomic_write):
                install.apply(plan, migrations={destination: old_file})
                install.remove_stale([stale])
                install.target_setup.apply_instructions(edits)
                updater.publish(checkout / ".tkstack/cache/upstreams/current", reselection)
                raise OSError("simulated write failure")
        self.assertEqual(destination.resolve(), old_file)
        self.assertEqual(stale.resolve(), old_file)
        self.assertFalse(added_link.exists() or added_link.is_symlink())
        self.assertEqual(config.read_text(), "before")
        self.assertEqual((checkout / ".tkstack/cache/upstreams/current").resolve(), updated)
        self.assertFalse(state.applied)
        state.applied = True
        with self.assertRaisesRegex(ValueError, "could not restore"):
            with updater.apply_transaction(checkout, state, plan, [], [],
                                           install.target_setup.instructify(ROOT).atomic_write):
                install.apply(plan, migrations={destination: old_file})
                destination.unlink()
                destination.write_text("user changed this")
                raise OSError("simulated concurrent edit")
        self.assertEqual(destination.read_text(), "user changed this")
        self.assertTrue(state.applied)
        missing = {"upstreams": str(checkout / ".tkstack/cache/upstreams/missing/sources"),
                   "runtime": str(checkout / ".tkstack/runtime/versions/missing")}
        args = updater.SimpleNamespace(dry_run=False, check=False, status=False, uninstall=False)
        with patch.dict(os.environ, {"TKSTACK_OFFLINE": "0"}), \
             patch.object(updater, "prepare_sources", return_value=updated), \
             patch.object(updater, "prepare_runtime", return_value=previous):
            with updater.installation(checkout, self.target, "home", missing, args, lambda root: None,
                                      lambda path, root: None) as recovered:
                self.assertEqual(recovered.upstreams, updated / "sources")
                self.assertEqual(recovered.runtime, previous)

    def test_latest_python_packages_choose_compatible_interpreters(self):
        updater = load("latest_python_test", ROOT / "integrations/latest.py")
        uv = self.target / "uv"
        uv.write_text("""#!/usr/bin/env python3
import json, os, sys
action = sys.argv[2]
if action == 'list':
    versions = ['3.14.8', '3.13.16'] if '<3.15' in sys.argv[-1] else ['3.15.1', '3.14.8']
    print(json.dumps([{'version': v, 'implementation': 'cpython', 'variant': 'default'} for v in versions]))
elif action == 'install':
    with open(os.environ['INSTALL_LOG'], 'a') as f: f.write(sys.argv[-1] + '\\n')
elif action == 'find':
    print('/managed/python-' + sys.argv[-1])
""")
        uv.chmod(0o755)
        log = self.target / "installed"
        def metadata(url):
            name = url.split('/')[-2]
            required = '>=3.11,<3.15' if name in ('graphifyy', 'serena-agent') else '>=3.11'
            return json.dumps({'info': {'version': '9.9.0', 'requires_python': required}}).encode()
        with patch.object(updater, 'get', side_effect=metadata):
            releases = updater.current_python(self.target, uv, {**os.environ, 'INSTALL_LOG': str(log)})
        self.assertEqual(releases['graphify']['version'], '3.14.8')
        self.assertEqual(releases['serena']['version'], '3.14.8')
        self.assertEqual(releases['headroom']['version'], '3.15.1')
        self.assertEqual(releases['graphify']['requirements'], ['graphifyy[mcp]==9.9.0'])
        self.assertCountEqual(log.read_text().splitlines(), ['3.14.8', '3.15.1'])

    @unittest.skipUnless((ROOT / ".tkstack/runtime/current/bin/landmines").is_file(),
                         "Provision the Landmines runtime to test native linting")
    def test_landmines_runs_in_an_external_project(self):
        managed = ROOT / ".tkstack/runtime/current"
        command = [str(managed / "bin/landmines"), "--format=json", "--threads=1"]
        fixtures = {
            "bad.test.ts": "import { test } from 'vitest';\ntest('waits', async () => { await new Promise(resolve => setTimeout(resolve, 100)); });\n",
            "transfer.test.ts": "import { test } from 'vitest';\n// This comment should be removed.\ntest('waits again', async () => { await new Promise(resolve => globalThis.setTimeout(resolve, 100)); });\n",
            "good.test.ts": "import { test, expect } from 'vitest';\n// WARNING: Stable public behavior is under test.\ntest('returns', () => { expect(1 + 1).toBe(2); });\n",
            "typed.ts": "export function value(): number { return 1; }\n",
            "misnamed.spec.ts": "import { test, expect } from 'vitest';\ntest('works', () => { expect(1).toBe(1); });\n",
        }
        for name, content in fixtures.items():
            (self.target / name).write_text(content)
        linted = subprocess.run(command + list(fixtures), cwd=self.target, text=True, capture_output=True, timeout=30)
        self.assertEqual(linted.returncode, 1, linted.stderr)
        report = json.loads(linted.stdout)
        self.assertEqual(report["number_of_files"], len(fixtures))
        self.assertEqual({(item["filename"], item["code"]) for item in report["diagnostics"]}, {
            ("bad.test.ts", "landmines-testing(no-fixed-sleep)"),
            ("transfer.test.ts", "landmines-testing(no-fixed-sleep)"),
            ("transfer.test.ts", "landmines-style(no-comments)"),
            ("typed.ts", "landmines-types(no-explicit-return-types)"),
            ("misnamed.spec.ts", "landmines-structure(test-file-names)"),
        })
        clean = subprocess.run(command + ["good.test.ts"], cwd=self.target, text=True, capture_output=True, timeout=30)
        self.assertEqual(clean.returncode, 0, clean.stderr)
        self.assertEqual(json.loads(clean.stdout)["number_of_files"], 1)
        self.assertEqual(json.loads(clean.stdout)["diagnostics"], [])

    def test_install_preserves_references_and_is_repeatable(self):
        self.assertEqual(install.apply(self.plan), self.expected_links)
        self.assertEqual(install.apply(self.plan), 0)
        for source, destination in self.plan:
            self.assertTrue(install.matches(destination, source))
        reference = self.target / ".cursor/skills/create-verification-skill/references/feature-map-example/README.md"
        self.assertTrue(reference.is_file())
        script = self.target / ".cursor/skills/show-me-your-work/scripts/log.sh"
        self.assertTrue(script.stat().st_mode & 0o111)
        installed_sdlc = self.target / '.agents/skills/sdlc'
        self.assertEqual(installed_sdlc.resolve(), ROOT / 'skills/sdlc')
        for document in (installed_sdlc / 'SKILL.md',
                         installed_sdlc / 'references/operating-guide.md'):
            links = re.findall(r'\]\(([^)]+)\)', document.read_text())
            measured = [link for link in links if link.endswith('measured-feature-work.md')]
            self.assertEqual(len(measured), 1, str(document))
            self.assertTrue((document.parent / measured[0]).is_file(), str(document))

    def test_skills_install_into_the_directory_matching_their_origin(self):
        by_directory = {}
        for _, destination in self.plan:
            by_directory.setdefault(destination.parent.relative_to(self.target), set()).add(destination.name)
        shared, claude, cursor = (by_directory[Path(p)] for p in
                                  (".agents/skills", ".claude/skills", ".cursor/skills"))
        developed = {path.name for path in (ROOT / "skills").iterdir() if (path / "SKILL.md").is_file()}
        self.assertLessEqual(developed, shared & claude & cursor)
        # Learn's packaged subskills are subcommands, not separately installed skills.
        for name in ("codify", "flowify", "hookify", "instructify", "lintify", "reusify", "skillify", "testify", "evalify"):
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
        self.assertEqual(install.expand_harnesses(ROOT, ["t3code"]),
                         ["claude", "codex", "cursor", "copilot", "grok"])
        self.assertEqual(
            install.expand_harnesses(ROOT, ["t3code", "claude", "muse"]),
            ["claude", "codex", "cursor", "copilot", "grok", "muse"],
        )
        self.assertEqual(
            install.expand_harnesses(ROOT, [*install.SKILL_PATHS, "t3code"]),
            list(install.SKILL_PATHS),
        )
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

    def test_t3code_installs_delegate_placements_and_uninstalls_them(self):
        holding = tempfile.TemporaryDirectory()
        self.addCleanup(holding.cleanup)
        broken = Path(holding.name)
        (broken / "skills").mkdir()
        (broken / "skills" / "skills.json").write_text(
            '{"delegates": {"t3code": ["claude", "nope"]}}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "delegates must name"):
            install.expand_harnesses(broken, ["t3code"])
        env = _env_without_uv()
        base = [sys.executable, str(ROOT / "scripts/install.py"), "--target", str(self.target), "--harness", "t3code", "--profile", "catalog"]
        preview = subprocess.run(base + ["--dry-run", "--scope", "project"],
                                 capture_output=True, text=True, env=env)
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
        for relative in (".github/skills", ".claude/skills", ".agents/skills", ".cursor/skills", ".grok/skills", ".cursor/rules"):
            self.assertIn(str(self.target / relative), preview.stdout)
        self.assertNotIn(str(self.target / ".copilot/skills"), preview.stdout)
        self.assertNotIn(".kimi/skills", preview.stdout)
        self.assertNotIn("t3code", preview.stdout)
        self.assertEqual(list(self.target.iterdir()), [])
        installed = subprocess.run(base + ["--scope", "home"], capture_output=True, text=True, env=env)
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        self.assertTrue((self.target / ".copilot/skills/learn").is_symlink())
        self.assertTrue((self.target / ".claude/skills/graphify").is_symlink())
        self.assertFalse((self.target / ".grok/skills/graphify").exists())
        self.assertFalse((self.target / ".github/skills").exists())
        self.assertNotIn("t3code", {path.name for path in self.target.iterdir()})
        receipt = self.target / ".tkstack/install.json"
        saved = json.loads(receipt.read_text())
        vanished_source = ROOT / ".tkstack/cache/upstreams/generation-removed/sources"
        vanished_runtime = ROOT / ".tkstack/runtime/versions/generation-removed"
        saved.update(upstreams=str(vanished_source), runtime=str(vanished_runtime))
        old_tool = vanished_runtime / "bin/landmines"
        owned_tool = self.target / ".tkstack/bin/landmines"
        owned_tool.parent.mkdir(parents=True, exist_ok=True)
        owned_tool.symlink_to(old_tool)
        foreign_tool = self.target / ".local/bin/landmines"
        foreign_tool.parent.mkdir(parents=True, exist_ok=True)
        foreign_tool.write_text("user command")
        saved["links"].update({".tkstack/bin/landmines": str(old_tool), ".local/bin/landmines": str(old_tool)})
        receipt.write_text(json.dumps(saved))
        dry_remove = subprocess.run(
            [sys.executable, str(ROOT / "scripts/install.py"), "--dry-run", "--uninstall", "--target", str(self.target)],
            capture_output=True, text=True, env=env)
        self.assertEqual(dry_remove.returncode, 0, dry_remove.stdout + dry_remove.stderr)
        self.assertIn(f"Would remove: {self.target / '.copilot/skills/learn'}", dry_remove.stdout)
        self.assertTrue((self.target / ".copilot/skills/learn").is_symlink())
        removed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/install.py"), "--uninstall", "--target", str(self.target)],
            capture_output=True, text=True, env=env)
        self.assertEqual(removed.returncode, 0, removed.stdout + removed.stderr)
        self.assertFalse((self.target / ".copilot/skills/learn").exists())
        self.assertFalse(owned_tool.exists() or owned_tool.is_symlink())
        self.assertEqual(foreign_tool.read_text(), "user command")
        self.assertFalse((self.target / ".claude/skills/learn").exists())

    def test_uninstall_succeeds_when_delegates_are_broken(self):
        install.apply(self.plan)
        owned = self.target / ".claude" / "skills" / "learn"
        self.assertTrue(owned.is_symlink())
        placement = ROOT / "skills" / "skills.json"
        original = placement.read_bytes()
        needle = b'"t3code": ["claude", "codex", "cursor", "copilot", "grok"]'
        self.assertIn(needle, original)
        self.addCleanup(placement.write_bytes, original)
        command = [
            sys.executable, str(ROOT / "scripts/install.py"),
            "--uninstall", "--target", str(self.target),
        ]
        env = _env_without_uv()
        for replacement in (b'"t3code": []', b'"t3code": ["claude", "nope"]'):
            placement.write_bytes(original.replace(needle, replacement, 1))
            if not owned.is_symlink():
                install.apply(self.plan)
            completed = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertNotIn("delegates must name", completed.stderr)
            self.assertFalse(owned.exists() or owned.is_symlink())

    def test_invalid_parent_stops_before_creating_other_links(self):
        parent = self.plan[-1][1].parent
        parent.parent.mkdir(parents=True, exist_ok=True)
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
        alias = project / ".agents/skills/my-learn"
        alias.parent.mkdir(parents=True)
        alias.symlink_to(owned.resolve())
        shared = alias.with_name("learn")
        shared.symlink_to(owned.resolve())
        stale = install.stale_links(ROOT, project, list(install.SKILL_PATHS), [], None)
        self.assertCountEqual(stale, [owned, shared])
        install.remove_stale(stale)
        self.assertTrue(alias.is_symlink())

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

    def test_reinstall_migrates_former_cursor_rule_links(self):
        names = ("graphify.mdc", "tkstack-steering.mdc")
        for name in names:
            destination = self.target / ".cursor" / "rules" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(ROOT / "harnesses" / "cursor" / name)
        env = _env_without_uv()
        command = [
            sys.executable, str(ROOT / "scripts/install.py"),
            "--target", str(self.target), "--harness", "cursor", "--profile", "catalog",
        ]
        preview = subprocess.run(command + ["--dry-run"], capture_output=True, text=True, env=env)
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
        for name in names:
            self.assertIn(f"Would migrate: {self.target / '.cursor' / 'rules' / name}", preview.stdout)
            self.assertEqual(
                os.readlink(self.target / ".cursor" / "rules" / name),
                str(ROOT / "harnesses" / "cursor" / name),
            )
        installed = subprocess.run(command, capture_output=True, text=True, env=env)
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        for name in names:
            link = self.target / ".cursor" / "rules" / name
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), (ROOT / ".cursor" / "rules" / name).resolve())

    def test_uninstall_removes_former_cursor_rule_links(self):
        for name in ("graphify.mdc", "tkstack-steering.mdc"):
            destination = self.target / ".cursor" / "rules" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(ROOT / "harnesses" / "cursor" / name)
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/install.py"), "--uninstall", "--target", str(self.target)],
            capture_output=True, text=True, check=False, env=_env_without_uv(),
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        for name in ("graphify.mdc", "tkstack-steering.mdc"):
            link = self.target / ".cursor" / "rules" / name
            self.assertFalse(link.exists() or link.is_symlink())

    def test_owned_cursor_rules_link_elsewhere_and_stay_files_in_the_checkout(self):
        rules = sorted((ROOT / ".cursor/rules").glob("*.mdc"))
        owned = [path for path in rules if not path.is_symlink()]
        self.assertEqual(sorted(path.name for path in owned), ["graphify.mdc", "tkstack-steering.mdc"])
        plan = install.link_plan(ROOT, self.target, ["cursor"])
        for rule in owned:
            matches = [destination for source, destination in plan if source == rule.resolve()]
            self.assertEqual(matches, [self.target / ".cursor/rules" / rule.name])
        destinations = {destination.resolve() for _, destination in install.link_plan(ROOT, ROOT, ["cursor"])}
        for rule in owned:
            self.assertNotIn(rule.resolve(), destinations)

    def test_install_into_own_checkout_preserves_portable_instruction_sources(self):
        checkout = self.target / 'self checkout'
        checkout.mkdir()
        for directory in ('vendor', 'scripts', 'src', 'skills', 'integrations'):
            shutil.copytree(ROOT / directory, checkout / directory, symlinks=True,
                            ignore=shutil.ignore_patterns('__pycache__', 'node_modules'))
        for name in ('sources.lock.json', 'AGENTS.md', 'CLAUDE.md'):
            shutil.copy2(ROOT / name, checkout / name)
        before = {name: (checkout / name).read_bytes() for name in ('AGENTS.md', 'CLAUDE.md')}
        command = [sys.executable, str(checkout / 'scripts/install.py'), '--target', str(checkout),
                   '--harness', 'codex', '--harness', 'claude']
        installed = subprocess.run(command, capture_output=True, text=True, timeout=60, env=_env_without_uv())
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

    def test_external_target_initializes_local_state_launcher_and_instructions_and_check_detects_drift(self):
        target = self.target / 'workspace with spaces'
        target.mkdir()
        subprocess.run(['git', '-C', str(target), 'init', '-q'], check=True, capture_output=True)
        (target / 'AGENTS.md').write_text('Keep my project rules.\n')
        (target / 'CLAUDE.md').write_text('Keep my Claude rules.\n')
        command = [str(ROOT / 'install.sh'), '--target', str(target)]
        env = _env_without_uv()
        def invoke(*args, expected=0):
            result = subprocess.run([*command, *args], cwd=self.target, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            return result
        invoke('--check', expected=1)
        invoke('--dry-run')
        self.assertFalse((target / '.tkstack').exists())
        invoke()
        invoke('--check')
        self.assertEqual(json.loads((target / '.tkstack/install.json').read_text())['profile'], 'catalog')
        self.assertTrue((target / '.cursor/skills/architect/SKILL.md').is_file())
        instructions = (target / 'AGENTS.md').read_text()
        self.assertIn('scratch skill', instructions)
        self.assertIn('Never commit scratch', instructions)
        self.assertTrue((target / '.tkstack/.scratch').is_dir())
        self.assertIn('/.scratch/', (target / '.tkstack/.gitignore').read_text().splitlines())
        self.assertTrue((target / '.agents/skills/scratch/SKILL.md').is_file())
        scratch = target / '.tkstack/.scratch'
        scratch.rmdir()
        self.assertIn('Scratch directory needs setup', invoke('--check', expected=1).stderr)
        invoke()
        ignore_policy = target / '.tkstack/.gitignore'
        ignore_policy.write_text(ignore_policy.read_text().replace('/.scratch/\n', ''))
        self.assertIn('State ignore policy needs setup', invoke('--check', expected=1).stderr)
        invoke()
        self.assertIn('/.scratch/', ignore_policy.read_text().splitlines())
        task = scratch / 'active-task'
        task.mkdir()
        (task / 'draft.txt').write_text('retain until reviewed')
        excludes = subprocess.check_output(['git', '-C', str(target), 'check-ignore', '-v', '.tkstack/.gitignore'], text=True)
        self.assertIn('/.tkstack/', excludes)
        self.assertEqual((target / '.agents/steering').resolve(), target / '.tkstack/steering')
        self.assertEqual((target / '.agents/skills/constrain').resolve(), ROOT / 'skills/constrain')
        result = subprocess.run([str(target / '.tkstack/tkstack'), 'skills', 'constrain', '--', 'native', 'check', '--repo', '.'], cwd=target,
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('Missing constraint input: .constrain/config.json', result.stderr)
        before = (target / 'AGENTS.md').read_bytes()
        inventory = {p.relative_to(target): os.readlink(p) for p in target.rglob('*') if p.is_symlink()}
        invoke()
        self.assertEqual((task / 'draft.txt').read_text(), 'retain until reviewed')
        self.assertEqual({p.relative_to(target): os.readlink(p) for p in target.rglob('*') if p.is_symlink()}, inventory)
        self.assertIn(Path('.cursor/rules/tkstack-steering.mdc'), inventory)
        untracked = subprocess.check_output(['git', '-C', str(target), 'ls-files', '--others', '--exclude-standard'], text=True)
        self.assertEqual(set(untracked.splitlines()), {'AGENTS.md', 'CLAUDE.md'})
        invoke('--adopt', '--constraint-hook')
        policy = target / '.constrain/config.json'
        subprocess.run(['git', '-C', str(target), 'add', '.constrain'], check=True)
        gate = target / '.git/hooks/pre-commit'
        passed = subprocess.run([str(gate)], cwd=target, env=env, capture_output=True, text=True)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        policy.write_text('{}')
        subprocess.run(['git', '-C', str(target), 'add', '.constrain/config.json'], check=True)
        failed = subprocess.run([str(gate)], cwd=target, env=env, capture_output=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(policy.read_text(), '{}')

        self.assertEqual((target / 'AGENTS.md').read_bytes(), before)
        self.assertIn('Keep my project rules.', before.decode())
        link = target / '.agents/skills/constrain'
        link.unlink()
        invoke('--check', expected=1)
        invoke()
        subprocess.run(['git', '-C', str(target), 'config', 'core.hooksPath', 'team-hooks'], check=True)
        invoke('--uninstall')
        self.assertFalse(gate.exists())
        self.assertEqual(subprocess.check_output(['git', '-C', str(target), 'config', 'core.hooksPath'], text=True).strip(), 'team-hooks')
        self.assertEqual((target / 'AGENTS.md').read_text(), 'Keep my project rules.\n')
        self.assertEqual((target / 'CLAUDE.md').read_text(), 'Keep my Claude rules.\n')
        self.assertFalse(gate.exists())
        self.assertTrue(policy.exists())
        self.assertFalse((target / '.tkstack/tkstack').is_symlink())
        self.assertTrue((ROOT / 'skills/constrain/SKILL.md').is_file())

    def test_fresh_checkout_installs_without_a_preexisting_alias_view(self):
        checkout = self.target / "checkout"
        checkout.mkdir()
        for directory in ("vendor", "scripts", "src", "skills", "integrations"):
            shutil.copytree(ROOT / directory, checkout / directory, symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        shutil.copy2(ROOT / "sources.lock.json", checkout / "sources.lock.json")
        target = self.target / "installation"
        command = [sys.executable, str(checkout / "scripts/install.py"),
                   "--target", str(target), "--profile", "catalog"]
        env = _env_without_uv()
        subprocess.run(command + ["--dry-run"], check=True, capture_output=True, env=env)
        self.assertFalse((checkout / ".tkstack").exists())
        self.assertFalse(target.exists())
        subprocess.run(['git', '-C', str(checkout), 'init', '-q'], check=True)
        subprocess.run(['git', '-C', str(checkout), 'config', 'core.hooksPath', 'team-hooks'], check=True)
        installed = subprocess.run(command, check=True, capture_output=True, text=True, env=env)
        self.assertTrue((target / ".agents/skills/matt-tdd/SKILL.md").is_file())
        self.assertTrue((target / ".agents/steering").is_symlink())
        again = subprocess.run(command, check=True, capture_output=True, text=True, env=env)
        self.assertIn("0 link(s) changed.", again.stdout)
        subprocess.run(command + ['--uninstall'], check=True, capture_output=True, env=env)
        self.assertEqual(subprocess.check_output(['git', '-C', str(checkout), 'config', 'core.hooksPath'], text=True).strip(), 'team-hooks')

    @unittest.skipUnless(shutil.which("codex"), "native Codex CLI unavailable")
    def test_home_defaults_loaded_from_unrelated_git_project(self):
        home = self.target / "home"
        project = self.target / "work"
        project.mkdir()
        home.mkdir()
        profile = home / "custom-codex"
        env = {**os.environ, "HOME": str(home), "CODEX_HOME": str(profile), "TKSTACK_OFFLINE": "1"}
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        setup = [str(ROOT / "install.sh")]
        subprocess.run(setup, cwd=project, env=env, check=True, capture_output=True)
        prompt = subprocess.check_output(["codex", "debug", "prompt-input", "offline discovery"],
                                        cwd=project, env=env, text=True, timeout=30)
        self.assertIn(str(home / ".agents/principles/SKILL.md"), prompt)
        self.assertIn("constrain/SKILL.md", prompt)
        self.assertIn("scratch/SKILL.md", prompt)
        self.assertNotIn("testify/SKILL.md", prompt)
        self.assertNotIn("codify/SKILL.md", prompt)
        self.assertLessEqual({"constrain", "investigate", "learn", "tkstack-principles", "matt-tdd", "caveman"},
                             {p.name for p in (home / ".agents/skills").iterdir()})
        self.assertTrue((home / ".cursor/skills/architect/SKILL.md").is_file())
        self.assertTrue((home / ".claude/CLAUDE.md").is_file())
        subprocess.run(setup + ["--uninstall"], cwd=project, env=env, check=True, capture_output=True)
        self.assertFalse((profile / "AGENTS.md").exists())



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
        path = self.base / "uv.tar.gz"
        arch = {"x86_64": "x86_64", "amd64": "x86_64", "arm64": "aarch64", "aarch64": "aarch64"}[platform.machine().lower()]
        system = "unknown-linux-gnu" if platform.system() == "Linux" else "apple-darwin"
        content = _UV_STUB.encode()
        with tarfile.open(path, "w:gz") as archive:
            member = tarfile.TarInfo(f"uv-{arch}-{system}/uv")
            member.size, member.mode = len(content), 0o755
            archive.addfile(member, io.BytesIO(content))
            extra = tarfile.TarInfo("../unexpected")
            extra.size = 1
            archive.addfile(extra, io.BytesIO(b"x"))
        return path

    def _pinned_checkout(self):
        checkout = self.base / "checkout"
        (checkout / "scripts").mkdir(parents=True)
        text = (ROOT / "install.sh").read_text()
        script = checkout / "install.sh"
        script.write_text(text)
        script.chmod(0o755)
        (checkout / "scripts" / "install.py").write_text("raise SystemExit(0)\n")
        return script

    def _run(self, script, path, *arguments, extra=None):
        environment = self._env(path)
        if "git" not in {p.name for d in path.split(os.pathsep) for p in Path(d).glob("git")}:
            # Freeze the test archive before the installer reads the supplied digest.
            fixture = self.base / "fixture.tar.gz"
            supplied = (extra or {}).get("BAD_TAR")
            if supplied:
                fixture = Path(supplied)
            elif not fixture.exists():
                with tarfile.open(fixture, "w:gz") as archive:
                    for name, content in (("scripts/install.py", b"print(1)"), ("install.sh", b'#!/bin/sh\necho "local-install $*" >> "$INSTALL_LOG"\n')):
                        member = tarfile.TarInfo("tkstack-main/" + name)
                        member.size, member.mode = len(content), 0o755
                        archive.addfile(member, io.BytesIO(content))
            environment.update(BAD_TAR=str(fixture), TKSTACK_TARBALL_SHA256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
                               TKSTACK_REV="a" * 40)
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
        self.assertIn("python install 3", log)
        self.assertIn("run --python 3 --no-project -- python -B ", log)
        self.assertIn(str(ROOT / "scripts" / "install.py"), log)
        self.assertIn("--dry-run", log)
        self.assertNotIn("requires Python 3.11+", result.stderr)
        self.assertFalse(self.curl_log.exists())

    def test_missing_python_and_uv_bootstraps_the_current_uv_release(self):
        body = self._installer_body()
        path = _stub_path(self.base / "bins", ("python", "uv"), {"curl": _CURL_UV})
        poison = self.base / "poison-bin"
        script = self._pinned_checkout()
        result = self._run(
            script, path, "--dry-run", "--target", str(self.base / "target"),
            extra={"UV_INSTALLER_FILE": str(body), "UV_INSTALL_DIR": str(poison)},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("https://github.com/astral-sh/uv/releases/latest/download/", self.curl_log.read_text())
        self.assertIn(" -o ", " " + self.curl_log.read_text())
        log = self.uv_log.read_text()
        self.assertIn("python install 3", log)
        self.assertIn("run --python 3", log)
        installed = self.home / ".local" / "bin" / "uv"
        self.assertTrue(installed.is_file())
        self.assertFalse(poison.exists())
        self.assertNotIn("requires Python 3.11+", result.stderr)

    def test_uv_installer_sha256_mismatch_does_not_run_it(self):
        body = self._installer_body()
        path = _stub_path(self.base / "bins", ("python", "uv"), {"curl": _CURL_UV, "sh": "#!/bin/sh\nprintf '%s\\n' ran-sh >> \"$UV_LOG\"\nexit 0\n"})
        script = self._pinned_checkout()
        result = self._run(script, path, extra={"UV_INSTALLER_FILE": str(body), "UV_DIGEST_OVERRIDE": "0" * 64})
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
        self.assertIn("https://codeload.github.com/Tyler-R-Kendrick/tkstack/tar.gz/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", self.curl_log.read_text())
        self.assertIn("local-install --dry-run", self.install_log.read_text())
        checkout = self.home / ".local" / "share" / "tkstack"
        self.assertTrue((checkout / "install.sh").is_file())
        receipt = (checkout / ".tkstack" / "source-receipt.txt").read_text()
        self.assertIn("kind=tarball", receipt)
        mismatch = self._run(script, path, "--check", extra={"TKSTACK_TRUST_HOME": "1", "TKSTACK_TARBALL_SHA256": "0"*64})
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("sha256 mismatch", mismatch.stderr)
        (checkout / ".tkstack" / "keep").write_text("state\n")
        refused = self._run(script, path, "--check")
        self.assertNotEqual(refused.returncode, 0, refused.stdout + refused.stderr)
        self.assertIn("Refusing to run it", refused.stderr)
        self.assertIn("TKSTACK_TRUST_HOME", refused.stderr)
        self.assertEqual(self.curl_log.read_text().count("codeload.github.com"), 2)
        self.assertNotIn("local-install --check", self.install_log.read_text())
        self.assertEqual((checkout / ".tkstack" / "keep").read_text(), "state\n")
        again = self._run(script, path, "--check", extra={"TKSTACK_TRUST_HOME": "1"})
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertIn("frozen", again.stderr)
        self.assertEqual(self.curl_log.read_text().count("codeload.github.com"), 3)
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
            "url=https://codeload.github.com/Tyler-R-Kendrick/tkstack/tar.gz/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
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

    def test_uv_archive_extracts_only_the_expected_executable(self):
        body = self._installer_body()
        path = _stub_path(self.base / "bins-chatty", ("python", "uv"), {"curl": _CURL_UV})
        script = self._pinned_checkout()
        result = self._run(script, path, "--dry-run", "--target", str(self.base / "target"), extra={"UV_INSTALLER_FILE": str(body)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        log = self.uv_log.read_text()
        self.assertIn("python install 3", log)
        self.assertFalse((self.base / "unexpected").exists())


class SerenaInstallTests(unittest.TestCase):
    def test_native_server_and_index_select_the_requested_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            binary = base / "serena"
            binary.write_text("#!/bin/sh\nprintf '%s\\n' \"$PWD\" \"$@\" > invocation\n")
            binary.chmod(0o755)
            env = {**os.environ, "PATH": str(base) + os.pathsep + os.environ["PATH"]}
            env["HOME"] = str(base)
            env["TKSTACK_SERENA"] = str(binary)
            for target_args in ([], ["--target", str(base)]):
                result = subprocess.run([sys.executable, str(ROOT / "scripts/install.py"), "--scope", "project",
                                         "--index-serena", *target_args], env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("external --target", result.stderr)
                self.assertFalse((base / "invocation").exists())
            for name in ("project one", "project two"):
                project = base / name
                project.mkdir()
                cmd = [sys.executable, str(ROOT / "scripts/install.py"), "--target", str(project)]
                config = json.loads(subprocess.check_output(cmd + ["--serena-command"], env=env))
                self.assertEqual(config["args"], ["start-mcp-server", "--project", str(project)])
                subprocess.run(cmd + ["--index-serena"], cwd=base, env=env, check=True)
                self.assertEqual((project / "invocation").read_text().splitlines(),
                                 [str(project), "project", "index", str(project)])
