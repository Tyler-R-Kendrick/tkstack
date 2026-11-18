"""Deterministic repository quality checks."""

import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent


def load_checks():
    path = ROOT / "evals" / "repo-quality" / "checks.py"
    spec = importlib.util.spec_from_file_location("repo_quality_checks", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_agent_plugins():
    path = ROOT / "evals" / "repo-quality" / "agent_plugins.py"
    spec = importlib.util.spec_from_file_location("repo_quality_agent_plugins", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_snapshot():
    path = ROOT / "evals" / "repo-quality" / "snapshot.py"
    spec = importlib.util.spec_from_file_location("repo_quality_snapshot", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checks = load_checks()
snapshot = load_snapshot()



def failure_message(result):
    evidence = result["evidence"]
    if not isinstance(evidence, str):
        evidence = "\n".join(str(item) for item in evidence)
    return result["explanation"] + "\n" + evidence


def write_glue_and_skill_scripts(root):
    """scripts/, src/, one root-only skill script, and one the skill names."""
    root = Path(root)
    (root / "scripts").mkdir()
    (root / "src").mkdir()
    (root / "scripts" / "glue.py").write_text("print('glue')\n", encoding="utf-8")
    (root / "src" / "gate.py").write_text(
        "load('hidden', 'skills/demo/scripts/hidden.py')\n"
        "load('owned', 'skills/demo/scripts/owned.py')\n",
        encoding="utf-8",
    )
    skill = root / "skills" / "demo"
    (skill / "scripts").mkdir(parents=True)
    (skill / "references").mkdir()
    (skill / "SKILL.md").write_text(
        "Run scripts/owned.py for the skill's own engine.\n",
        encoding="utf-8",
    )
    (skill / "references" / "guide.md").write_text(
        "The workflow calls scripts/owned.py.\n",
        encoding="utf-8",
    )
    (skill / "scripts" / "workflow.lock.json").write_text(
        '{"files": {"scripts/owned.py": {}}}\n',
        encoding="utf-8",
    )
    (skill / "scripts" / "hidden.py").write_text(
        "".join(f"value_{index} = {index}\n" for index in range(20)),
        encoding="utf-8",
    )
    (skill / "scripts" / "owned.py").write_text(
        "".join(f"kept_{index} = {index}\n" for index in range(15)),
        encoding="utf-8",
    )
    (skill / "scripts" / "engine.py").write_text("print('skill engine')\n", encoding="utf-8")
    return root




GATE = unittest.skipUnless(
    os.environ.get("REPO_QUALITY_GATE") == "1",
    "set REPO_QUALITY_GATE=1 to enforce repo-quality ceilings",
)


class RepoQualityTests(unittest.TestCase):
    def assert_check(self, result):
        for key in ("name", "metric", "pass", "value", "limit", "explanation", "evidence"):
            self.assertIn(key, result)
        self.assertIsInstance(result["pass"], bool)
        self.assertIsInstance(result["explanation"], str)
        self.assertTrue(result["pass"], failure_message(result))

    @GATE
    def test_scripts_loc(self):
        self.assert_check(checks.scripts_loc(ROOT))

    def test_scripts_loc_counts_root_only_skill_scripts_not_skill_owned_ones(self):
        with tempfile.TemporaryDirectory(prefix="repo-quality-loc-") as temporary:
            root = write_glue_and_skill_scripts(temporary)
            result = checks.scripts_loc(root)
            evidence = "\n".join(result["evidence"])
            self.assertIn("skills/demo/scripts/hidden.py: 20 non-blank lines", evidence)
            self.assertNotIn("skills/demo/scripts/owned.py: 15 non-blank lines", evidence)
            self.assertNotIn("engine.py", evidence)
            self.assertIn("SKILL.md", result["explanation"])
            self.assertIn("references", result["explanation"])
            self.assertIn("workflow", result["explanation"])
            self.assertEqual(result["value"], 1 + 2 + 20)
            self.assertTrue(result["pass"], evidence)

    def test_scripts_loc_relative_root_matches_resolved_root(self):
        with tempfile.TemporaryDirectory(prefix="repo-quality-loc-") as temporary:
            root = write_glue_and_skill_scripts(temporary)
            absolute = checks.scripts_loc(root)
            previous = os.getcwd()
            try:
                os.chdir(root.parent)
                from_parent = checks.scripts_loc(Path(root.name))
                os.chdir(root)
                from_dot = checks.scripts_loc(Path("."))
                os.chdir(root / "scripts")
                from_parent_dir = checks.scripts_loc(Path(".."))
            finally:
                os.chdir(previous)
            self.assertEqual(absolute["value"], 1 + 2 + 20)
            self.assertIn(
                "skills/demo/scripts/owned.py: excluded because the skill mentions it",
                absolute["evidence"],
            )
            for relative in (from_parent, from_dot, from_parent_dir):
                self.assertEqual(relative["value"], absolute["value"])
                self.assertEqual(relative["evidence"], absolute["evidence"])

    def test_scripts_loc_lists_reached_skill_scripts_the_skill_mentions(self):
        with tempfile.TemporaryDirectory(prefix="repo-quality-loc-") as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "src").mkdir()
            (root / "scripts" / "glue.py").write_text("print('glue')\n", encoding="utf-8")
            (root / "src" / "gate.py").write_text(
                "load('hidden', 'skills/demo/scripts/hidden.py')\n"
                "load('owned', 'skills/demo/scripts/owned.py')\n"
                "load('also', 'skills/demo/scripts/also.py')\n",
                encoding="utf-8",
            )
            skill = root / "skills" / "demo"
            (skill / "scripts").mkdir(parents=True)
            (skill / "references").mkdir()
            (skill / "SKILL.md").write_text(
                "Run scripts/owned.py for the skill's own engine.\n"
                "scripts/also.py is also part of the skill.\n"
                "scripts/quiet.py is documented but root code never calls it.\n",
                encoding="utf-8",
            )
            (skill / "references" / "guide.md").write_text(
                "The workflow calls scripts/owned.py.\n",
                encoding="utf-8",
            )
            (skill / "scripts" / "workflow.lock.json").write_text(
                '{"files": {"scripts/owned.py": {}}}\n',
                encoding="utf-8",
            )
            (skill / "scripts" / "hidden.py").write_text(
                "".join(f"value_{index} = {index}\n" for index in range(20)),
                encoding="utf-8",
            )
            (skill / "scripts" / "owned.py").write_text(
                "".join(f"kept_{index} = {index}\n" for index in range(15)),
                encoding="utf-8",
            )
            (skill / "scripts" / "also.py").write_text(
                "".join(f"also_{index} = {index}\n" for index in range(4)),
                encoding="utf-8",
            )
            (skill / "scripts" / "engine.py").write_text("print('skill engine')\n", encoding="utf-8")
            (skill / "scripts" / "quiet.py").write_text("print('unreached')\n", encoding="utf-8")
            result = checks.scripts_loc(root)
            excluded = [
                line for line in result["evidence"]
                if line.endswith(": excluded because the skill mentions it")
            ]
            self.assertEqual(
                excluded,
                [
                    "skills/demo/scripts/also.py: excluded because the skill mentions it",
                    "skills/demo/scripts/owned.py: excluded because the skill mentions it",
                ],
            )
            evidence = "\n".join(result["evidence"])
            self.assertNotIn("quiet.py", evidence)
            self.assertNotIn("engine.py", evidence)
            self.assertNotIn("hidden.py: excluded", evidence)
            self.assertEqual(result["value"], 1 + 3 + 20)

    def test_named_skill_engines_are_not_repo_glue(self):
        reached = [path for path, _count in checks.reached_skill_scripts(ROOT)]
        for name in ("codify.py", "skillify.py", "evolve.py", "sync_codify.py", "routing_inventory.py"):
            self.assertFalse(any(path.endswith("/" + name) or path.endswith(name) for path in reached), reached)

    @GATE
    def test_quickstart_commands(self):
        self.assert_check(checks.quickstart_commands(ROOT))

    @GATE
    def test_marketplace_manifests(self):
        self.assert_check(checks.marketplace_manifests(ROOT))

    def test_checkout_matches_agent_plugins(self):
        self.assert_check(checks.agent_plugins_conformance(ROOT))

    def test_agent_plugins_rejects_secret_env_and_unknown_skill_fields(self):
        plugins = _load_agent_plugins()
        with tempfile.TemporaryDirectory(prefix="agent-plugins-") as temporary:
            root = Path(temporary)
            plugin = {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                "name": "example.plugin",
            }
            (root / "plugin.json").write_text(json.dumps(plugin) + "\n", encoding="utf-8")
            servers = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
            servers["mcpServers"]["firecrawl"]["env"] = {"FIRECRAWL_API_KEY": "fc-secretvalue"}
            (root / "mcp.json").write_text(json.dumps(servers) + "\n", encoding="utf-8")
            skill = root / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill.\ndisable-model-invocation: true\n---\n\nBody.\n",
                encoding="utf-8",
            )
            problems = plugins.conformance_problems(root)
            text = "\n".join(problems)
            self.assertIn("known credential pattern", text)
            self.assertIn("disable-model-invocation", text)

    def test_agent_plugins_leaves_foreign_placeholders_literal(self):
        plugins = _load_agent_plugins()
        with tempfile.TemporaryDirectory(prefix="agent-plugins-env-") as temporary:
            root = Path(temporary)
            (root / "plugin.json").write_text(
                (ROOT / "plugin.json").read_text(encoding="utf-8"), encoding="utf-8"
            )
            servers = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
            servers["mcpServers"]["firecrawl"]["env"] = {"FIRECRAWL_API_KEY": "${FIRECRAWL_API_KEY}"}
            (root / "mcp.json").write_text(json.dumps(servers) + "\n", encoding="utf-8")
            problems = plugins.conformance_problems(root)
            self.assertFalse(any("FIRECRAWL_API_KEY" in item for item in problems), problems)
            directory = str(ROOT / "evals" / "repo-quality")
            if directory not in sys.path:
                sys.path.insert(0, directory)
            import repo_mcp_policy
            policy = repo_mcp_policy.policy_problems(root)
            self.assertTrue(any("would overlay" in item for item in policy), policy)

    def test_absent_mcp_json_is_policy_not_spec(self):
        plugins = _load_agent_plugins()
        with tempfile.TemporaryDirectory(prefix="agent-plugins-absent-") as temporary:
            root = Path(temporary)
            (root / "plugin.json").write_text(
                (ROOT / "plugin.json").read_text(encoding="utf-8"), encoding="utf-8"
            )
            problems = plugins.conformance_problems(root)
            self.assertFalse(any("missing mcp.json" in item for item in problems), problems)
            directory = str(ROOT / "evals" / "repo-quality")
            if directory not in sys.path:
                sys.path.insert(0, directory)
            import repo_mcp_policy
            self.assertIn("missing mcp.json", repo_mcp_policy.policy_problems(root))

    def test_folded_skill_description_parses(self):
        plugins = _load_agent_plugins()
        with tempfile.TemporaryDirectory(prefix="agent-plugins-yaml-") as temporary:
            root = Path(temporary)
            skill = root / "skills" / "demo"
            skill.mkdir(parents=True)
            text = (
                "---\n"
                "name: demo\n"
                "description: >\n"
                "  Folded line one\n"
                "  folded line two\n"
                "---\n\n"
                "Body.\n"
            )
            (skill / "SKILL.md").write_text(text, encoding="utf-8")
            fields, errors = plugins.parse_frontmatter(text)
            self.assertEqual(errors, [])
            self.assertIn("Folded line one", fields["description"])
            self.assertIn("folded line two", fields["description"])
            self.assertEqual(plugins.skill_document_errors(skill, text), [])

    def test_cwd_escape_is_a_spec_error(self):
        plugins = _load_agent_plugins()
        document = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
        document["mcpServers"]["playwright"]["cwd"] = "${PLUGIN_ROOT}/../outside"
        escaped = plugins.mcp_semantic_errors(document, ROOT)
        self.assertTrue(any("cwd resolves outside" in item for item in escaped), escaped)
        document["mcpServers"]["playwright"]["cwd"] = "./."
        self.assertFalse(any("cwd" in item for item in plugins.mcp_semantic_errors(document, ROOT)))

    def test_in_root_skill_symlink_stays_conformant(self):
        plugins = _load_agent_plugins()
        with tempfile.TemporaryDirectory(prefix="agent-plugins-link-") as temporary:
            base = Path(temporary)
            root = base / "plugin"
            payload = root / "payload" / "demo"
            payload.mkdir(parents=True)
            (payload / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill.\n---\n\nBody.\n",
                encoding="utf-8",
            )
            (root / "plugin.json").write_text(
                (ROOT / "plugin.json").read_text(encoding="utf-8"), encoding="utf-8"
            )
            skills = root / "skills"
            skills.mkdir()
            (skills / "demo").symlink_to(payload, target_is_directory=True)
            problems = plugins.conformance_problems(root)
            self.assertFalse(any("outside" in item or "symlink" in item for item in problems), problems)
            outside = base / "outside"
            outside.mkdir()
            (outside / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill.\n---\n\nBody.\n",
                encoding="utf-8",
            )
            (skills / "demo").unlink()
            (skills / "demo").symlink_to(outside, target_is_directory=True)
            escaped = plugins.conformance_problems(root)
            self.assertTrue(any("outside the plugin root" in item for item in escaped), escaped)

    def test_extension_keys_must_be_reverse_domain_namespaces(self):
        plugins = _load_agent_plugins()
        with tempfile.TemporaryDirectory(prefix="agent-plugins-ext-") as temporary:
            root = Path(temporary)
            plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
            plugin["extensions"] = {"com.example.client": {"setting": True}}
            (root / "plugin.json").write_text(json.dumps(plugin), encoding="utf-8")
            self.assertFalse(any("extensions" in item for item in plugins.conformance_problems(root)))
            plugin["extensions"] = {"claude": {}, "Com.Example": {}}
            (root / "plugin.json").write_text(json.dumps(plugin), encoding="utf-8")
            bad = plugins.conformance_problems(root)
            self.assertTrue(any("claude" in item and "reverse-domain" in item for item in bad), bad)
            self.assertTrue(any("Com.Example" in item for item in bad), bad)
            plugin.pop("extensions")
            (root / "plugin.json").write_text(json.dumps(plugin), encoding="utf-8")
            self.assertFalse(any("extensions" in item for item in plugins.conformance_problems(root)))

    @GATE
    def test_harness_coverage(self):
        self.assert_check(checks.harness_coverage(ROOT))

    @GATE
    def test_install_flags(self):
        self.assert_check(checks.install_flags(ROOT))

    @GATE
    def test_top_level_files(self):
        self.assert_check(checks.top_level_files(ROOT))

    def test_no_harnesses_directory_fails_when_the_directory_exists(self):
        with tempfile.TemporaryDirectory(prefix="repo-quality-harnesses-") as temporary:
            root = Path(temporary)
            nested = root / "harnesses"
            nested.mkdir()
            (nested / "skills.json").write_text("{}\n", encoding="utf-8")
            found = checks.no_harnesses_directory(root)
            self.assertFalse(found["pass"])
            self.assertEqual(found["metric"], "conventions")
            self.assertEqual(found["value"], 1)
            self.assertEqual(found["limit"], 0)
            self.assertIn("harnesses/ exists", found["evidence"])
            self.assertIn("harnesses/skills.json", found["evidence"])
            for child in nested.iterdir():
                child.unlink()
            nested.rmdir()
            elsewhere = root / "notes"
            elsewhere.mkdir()
            (root / "harnesses").symlink_to(elsewhere, target_is_directory=True)
            via_link = checks.no_harnesses_directory(root)
            self.assertFalse(via_link["pass"])
            self.assertIn("harnesses/ exists", via_link["evidence"])
            (root / "harnesses").unlink()
            absent = checks.no_harnesses_directory(root)
            self.assertTrue(absent["pass"], absent["evidence"])
            self.assertEqual(absent["value"], 0)
            self.assertEqual(absent["evidence"], ["absent: harnesses/"])

    def test_no_harnesses_directory(self):
        self.assert_check(checks.no_harnesses_directory(ROOT))

    def test_snapshot_ignores_extra_args_from_any_directory(self):
        script = ROOT / "evals" / "repo-quality" / "snapshot.py"
        outputs = []
        temporary = tempfile.mkdtemp(prefix="repo-quality-cwd-")
        try:
            for cwd in (script.parent, ROOT, Path(temporary)):
                completed = subprocess.run(
                    [
                        sys.executable, str(script), "PROMPTFOO-ARGV-PROBE",
                        "{\"config\":true}", "{\"vars\":{}}",
                    ],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
                self.assertNotIn("PROMPTFOO-ARGV-PROBE", completed.stdout)
                outputs.append(completed.stdout)
        finally:
            os.rmdir(temporary)
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0], outputs[2])
        self.assertIn("## File tree", outputs[0])
        self.assertIn("## README.md", outputs[0])
        self.assertLess(outputs[0].index("## README.md"), outputs[0].index("## File tree"))

    def test_snapshot_stays_within_limit_and_keeps_evidence(self):
        text = snapshot.snapshot()
        self.assertLessEqual(len(text), snapshot.LIMIT)
        self.assertIn("## README.md", text)
        self.assertIn("## File tree", text)
        self.assertLess(text.index("## README.md"), text.index("## File tree"))
        self.assertIn("## SKILL.md frontmatter", text)
        self.assertIn("## docs/skill-marketplace.md", text)
        self.assertIn("## install.sh", text)
        self.assertIn("## LOC per top-level directory", text)
        self.assertIn("## Docs", text)
        self.assertIn("docs/unslop.md —", text)
        self.assertIn("## Install options", text)
        self.assertIn("--uninstall", text)
        self.assertIn("## Source pins", text)
        self.assertIn("name version revision", text)
        self.assertRegex(text, r"(?m)^ponytail \S+ [0-9a-f]{40}$")
        self.assertIn("skills/learn/skills/codify/SKILL.md", text)
        self.assertIn('main "$@"', text)
        self.assertIn("npx skills add", text)
        for relative in (
            ".claude-plugin/marketplace.json",
            ".claude-plugin/plugin.json",
            "skills/skills.json",
            "docs/harnesses.md",
            "docs/t3code.md",
        ):
            self.assertIn(relative, text)
        harnesses = text.split("## docs/harnesses.md\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("delegate harnesses' placements", harnesses)
        self.assertIn("./install.sh --harness t3code", harnesses)
        self.assertIn("| t3code |", harnesses)
        t3code = text.split("## docs/t3code.md\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("T3 Code is an orchestrator", t3code)
        self.assertIn("delegate", t3code)
        self.assertIn("./install.sh --harness t3code", t3code)
        readme = text.split("## README.md\n", 1)[1].split("\n## install.sh\n", 1)[0]
        self.assertIn("--target /absolute/project --check", readme)
        self.assertNotIn("[truncated docs/t3code.md]", t3code)
        home = str(Path.home())
        if len(home) > 1:
            self.assertNotIn(home, text)

    def test_snapshot_encoded_size_fits_exec_argv(self):
        text = snapshot.snapshot()
        self.assertLess(len(text.encode()), 100_000)

    def test_generated_lock_json_is_summarized(self):
        self.assertTrue(snapshot._is_lockfile("skills/sdlc/scripts/workflow.lock.json"))
        self.assertTrue(snapshot._is_lockfile("package-lock.json"))
        self.assertTrue(snapshot._is_lockfile("requirements.lock"))
        self.assertFalse(snapshot._is_lockfile("skills/skills.json"))
        lockfile = json.dumps({
            "name": "demo",
            "lockfileVersion": 3,
            "packages": {".": {"integrity": "sha512-abc"}},
        })
        summarized = snapshot._compact_json(lockfile)
        self.assertIn("lockfile omitted", summarized)
        self.assertNotIn("packages", summarized)
        manifest = json.dumps({
            "tools": {
                "rtk": {
                    "version": "1.1.0",
                    "platforms": {
                        "linux-x86_64": {
                            "url": "https://example.invalid/rtk.tar.gz",
                            "sha256": "ab" * 32,
                            "archive_member": "rtk",
                        }
                    },
                }
            }
        })
        compacted = snapshot._compact_json(manifest)
        self.assertIn("[download record omitted]", compacted)
        self.assertNotIn("sha256", compacted)
        self.assertIn("1.1.0", compacted)

    def test_quickstart_requires_exactly_one_command(self):
        with tempfile.TemporaryDirectory(prefix="repo-quality-readme-") as temporary:
            root = Path(temporary)
            readme = root / "README.md"
            readme.write_text("# Title\n\n## Install\n\nNo commands here.\n", encoding="utf-8")
            empty = checks.quickstart_commands(root)
            self.assertFalse(empty["pass"])
            self.assertEqual(empty["value"], 0)
            readme.write_text(textwrap.dedent("""\
                ## Uninstall

                ```sh
                rm -rf /
                ```

                ## Install

                ```text
                $ ./install.sh && echo done
                ```

                ```sh
                echo "keep && this"; true
                ```
                """), encoding="utf-8")
            counted = checks.quickstart_commands(root)
            self.assertEqual(counted["value"], 4, counted["evidence"])
            self.assertFalse(counted["pass"])

    def test_invalid_utf8_manifest_does_not_crash(self):
        with tempfile.TemporaryDirectory(prefix="repo-quality-json-") as temporary:
            path = Path(temporary) / "plugin.json"
            path.write_bytes(b"\xff\xfe not utf-8")
            loaded, detail = checks._json_object(path)
            self.assertIsNone(loaded)
            self.assertEqual(detail, "invalid UTF-8")

    def test_harness_coverage_ignores_prose_mentions(self):
        with tempfile.TemporaryDirectory(prefix="repo-quality-harness-") as temporary:
            root = Path(temporary)
            docs = root / "docs"
            docs.mkdir()
            (docs / "story.md").write_text(
                "The muse and kimi and grok and opencode and t3code are named here.\n",
                encoding="utf-8",
            )
            (root / "notes" / "muse").mkdir(parents=True)
            (root / "notes" / "muse" / "README.md").write_text("docs only\n", encoding="utf-8")
            (root / "skills").mkdir()
            (root / "skills" / "skills.json").write_text(
                '{"placement": {"default": ["codex"], "experimental": ["muse"]}}\n',
                encoding="utf-8",
            )
            (root / "scripts").mkdir()
            (root / "scripts" / "harness_paths.py").write_text(
                "from pathlib import Path\n"
                "SKILL_DIRECTORIES = {'codex': Path('.agents/skills')}\n"
                "DELEGATED_HARNESSES = {}\n"
                "def skill_directory(harness, scope='home'):\n"
                "    if harness in DELEGATED_HARNESSES or harness not in SKILL_DIRECTORIES:\n"
                "        return None\n"
                "    return SKILL_DIRECTORIES[harness]\n",
                encoding="utf-8",
            )
            covered = checks.harness_coverage(root)
            self.assertEqual(covered["value"], 1, covered["evidence"])
            self.assertFalse(covered["pass"])
            self.assertIn("muse: experimental, not counted", covered["evidence"])
            self.assertFalse(any("notes/muse" in line for line in covered["evidence"]))

    def test_counted_harnesses_are_directories_the_installer_links(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import install
        covered = checks.harness_coverage(ROOT)
        counted = [line.split(":", 1)[0] for line in covered["evidence"] if "installer links " in line]
        orchestrators = [line.split(":", 1)[0] for line in covered["evidence"] if "orchestrator; skills.json delegates" in line]
        self.assertEqual(covered["value"], len(counted) + len(orchestrators))
        self.assertEqual(
            counted,
            ["claude", "codex", "cursor", "copilot", "grok", "kimi", "muse", "opencode"],
        )
        self.assertEqual(covered["value"], 9)
        self.assertTrue(covered["pass"], covered["evidence"])
        self.assertIn("t3code: orchestrator; skills.json delegates to ", covered["evidence"][-1])
        self.assertIn("which are linked", covered["evidence"][-1])
        self.assertFalse(any("experimental" in line for line in covered["evidence"]))
        target = Path("/tmp/tkstack-coverage-target")
        parents = {
            destination.parent.relative_to(target)
            for _, destination in install.link_plan(ROOT, target, list(install.SKILL_PATHS), "home")
        }
        for line in covered["evidence"]:
            if "installer links " not in line:
                continue
            linked = Path(line.split("installer links ", 1)[1])
            self.assertIn(linked, parents)

    def test_harness_coverage_parses_installer_code_and_does_not_execute_it(self):
        with tempfile.TemporaryDirectory(prefix="repo-quality-parse-") as temporary:
            root = Path(temporary)
            (root / "skills").mkdir()
            (root / "skills" / "skills.json").write_text(
                '{"placement": {"default": ["codex"]}}\n',
                encoding="utf-8",
            )
            (root / "scripts").mkdir()
            marker = root / "executed"
            payload = root / "scripts" / "harness_paths.py"
            payload.write_text(
                "import os\n"
                f"os.system('touch {marker}')\n"
                "from pathlib import Path\n"
                "SKILL_DIRECTORIES = {'codex': Path('.agents/skills')}\n"
                "def skill_directory(harness, scope='home'):\n"
                "    return SKILL_DIRECTORIES.get(harness)\n",
                encoding="utf-8",
            )
            covered = checks.harness_coverage(root)
            self.assertFalse(marker.exists())
            self.assertEqual(covered["value"], 0, covered["evidence"])
            self.assertIn("codex: no skills.json placement path the installer links", covered["evidence"])

    def test_orchestrator_counts_only_when_every_delegate_is_linked(self):
        with tempfile.TemporaryDirectory(prefix="repo-quality-orchestrator-") as temporary:
            root = Path(temporary)
            (root / "skills").mkdir()
            (root / "scripts").mkdir()
            (root / "scripts" / "harness_paths.py").write_text(
                "from pathlib import Path\n"
                "SKILL_DIRECTORIES = {\n"
                "    'claude': Path('.claude/skills'),\n"
                "    'codex': Path('.agents/skills'),\n"
                "}\n"
                "def skill_directory(harness, scope='home'):\n"
                "    if harness not in SKILL_DIRECTORIES:\n"
                "        return None\n"
                "    return SKILL_DIRECTORIES[harness]\n",
                encoding="utf-8",
            )
            skills = root / "skills" / "skills.json"
            skills.write_text(
                '{"delegates": {"t3code": ["claude", "codex"]}, '
                '"placement": {"default": ["claude", "codex"]}}\n',
                encoding="utf-8",
            )
            covered = checks.harness_coverage(root)
            t3 = next(line for line in covered["evidence"] if line.startswith("t3code:"))
            self.assertIn("orchestrator", t3)
            self.assertIn("which are linked", t3)
            skills.write_text(
                '{"delegates": {"t3code": ["claude", "grok"]}, '
                '"placement": {"default": ["claude", "codex"]}}\n',
                encoding="utf-8",
            )
            partial = checks.harness_coverage(root)
            missed = next(line for line in partial["evidence"] if line.startswith("t3code:"))
            self.assertIn("unlinked", missed)
            self.assertNotIn("which are linked", missed)
            skills.write_text('{"placement": {"default": ["claude", "codex"]}}\n', encoding="utf-8")
            absent = checks.harness_coverage(root)
            plain = next(line for line in absent["evidence"] if line.startswith("t3code:"))
            self.assertIn("no skills.json placement path", plain)
            malformed = {
                "list": '{"delegates": ["claude", "codex"], "placement": {"default": ["claude", "codex"]}}\n',
                "empty": '{"delegates": {"t3code": []}, "placement": {"default": ["claude", "codex"]}}\n',
                "number": '{"delegates": {"t3code": ["claude", 1]}, "placement": {"default": ["claude", "codex"]}}\n',
                "blank": '{"delegates": {"t3code": [""]}, "placement": {"default": ["claude", "codex"]}}\n',
            }
            for label, body in malformed.items():
                skills.write_text(body, encoding="utf-8")
                covered = checks.harness_coverage(root)
                line = next(item for item in covered["evidence"] if item.startswith("t3code:"))
                self.assertIn("no skills.json placement path", line, label)
                self.assertNotIn("which are linked", line, label)
                self.assertNotIn("orchestrator", line, label)



if __name__ == "__main__":
    unittest.main()
