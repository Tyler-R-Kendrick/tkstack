"""Deterministic repo-quality checks and the promptfoo eval config."""

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
EVAL_YAML = ROOT / "evals" / "repo-quality" / "eval.yaml"
PROMPTFOO_PACKAGE = "promptfoo@0.125.1"
METRICS = (
    "conventions",
    "minimal_setup",
    "minimal_code",
    "cross_harness",
    "marketplace_install",
    "direct_install",
    "state_of_the_art",
    "documentation",
    "developer_experience",
    "dotfiles",
)


def load_checks():
    path = ROOT / "evals" / "repo-quality" / "checks.py"
    spec = importlib.util.spec_from_file_location("repo_quality_checks", path)
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


def _metric_scores(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    scores = {}
    for row in data["results"]["results"]:
        named = row.get("namedScores") or {}
        if named:
            scores.update(named)
            continue
        grading = row.get("gradingResult") or {}
        for component in grading.get("componentResults") or []:
            metric = (component.get("assertion") or {}).get("metric")
            if metric:
                scores[metric] = component.get("score")
    return scores


def failure_message(result):
    evidence = result["evidence"]
    if not isinstance(evidence, str):
        evidence = "\n".join(str(item) for item in evidence)
    return result["explanation"] + "\n" + evidence


def load_eval_config(path):
    text = path.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError:
        return _parse_yaml_subset(text)
    return yaml.safe_load(text)


class _YamlSubset:
    """Parse the eval config subset. Promptfoo's YAML is authoritative when PyYAML exists."""

    def __init__(self, text):
        self.lines = text.splitlines()
        self.index = 0

    def parse(self):
        value = self._parse_block(0)
        return {} if value is None else value

    def _done(self):
        return self.index >= len(self.lines)

    def _line(self):
        return self.lines[self.index]

    def _skip_noise(self):
        while not self._done():
            stripped = self._line().strip()
            if stripped and not stripped.startswith("#"):
                return
            self.index += 1

    def _indent(self, line):
        return len(line) - len(line.lstrip(" "))

    def _parse_block(self, indent):
        self._skip_noise()
        if self._done():
            return None
        line = self._line()
        current = self._indent(line)
        if current < indent:
            return None
        if line.lstrip().startswith("- "):
            return self._parse_list(current)
        mapping = {}
        self._fill_map(mapping, current)
        return mapping

    def _parse_list(self, indent):
        items = []
        while not self._done():
            self._skip_noise()
            if self._done():
                break
            line = self._line()
            if self._indent(line) != indent or not line.lstrip().startswith("- "):
                break
            payload = line.lstrip()[2:]
            self.index += 1
            if payload == "":
                items.append(self._parse_block(indent + 2))
                continue
            if re.match(r"^[A-Za-z0-9_-]+:( |$)", payload):
                key, raw = self._split_key(payload)
                item = {key: self._value(raw, indent + 2)}
                self._fill_map(item, indent + 2)
                items.append(item)
            else:
                items.append(self._scalar(payload))
        return items

    def _fill_map(self, mapping, indent):
        while not self._done():
            self._skip_noise()
            if self._done():
                break
            line = self._line()
            if self._indent(line) != indent or line.lstrip().startswith("- "):
                break
            key, raw = self._split_key(line.strip())
            self.index += 1
            mapping[key] = self._value(raw, indent + 2)

    def _split_key(self, text):
        name, _, raw = text.partition(":")
        return name.strip(), raw.strip()

    def _value(self, raw, child_indent):
        if raw == "|":
            return self._block(child_indent)
        if raw == "":
            block = self._parse_block(child_indent)
            return {} if block is None else block
        return self._scalar(raw)

    def _block(self, child_indent):
        collected = []
        base = None
        while not self._done():
            line = self._line()
            if line.strip() == "":
                collected.append("")
                self.index += 1
                continue
            if self._indent(line) < child_indent:
                break
            if base is None:
                base = self._indent(line)
            collected.append(line[base:])
            self.index += 1
        while collected and collected[-1] == "":
            collected.pop()
        return "\n".join(collected)

    def _scalar(self, raw):
        if raw in ("true", "false"):
            return raw == "true"
        if raw in ("null", "~"):
            return None
        if re.fullmatch(r"-?\d+", raw):
            return int(raw)
        if re.fullmatch(r"-?\d+\.\d+", raw):
            return float(raw)
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
            body = raw[1:-1]
            if raw[0] == '"':
                body = body.replace('\\"', '"').replace("\\\\", "\\")
            return body
        return raw


def _parse_yaml_subset(text):
    return _YamlSubset(text).parse()


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
            root = Path(temporary)
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
            result = checks.scripts_loc(root)
            evidence = "\n".join(result["evidence"])
            self.assertIn("skills/demo/scripts/hidden.py: 20 non-blank lines", evidence)
            self.assertNotIn("owned.py", evidence)
            self.assertNotIn("engine.py", evidence)
            self.assertIn("SKILL.md", result["explanation"])
            self.assertIn("references", result["explanation"])
            self.assertIn("workflow", result["explanation"])
            self.assertEqual(result["value"], 1 + 2 + 20)
            self.assertTrue(result["pass"], evidence)

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

    @GATE
    def test_harness_coverage(self):
        self.assert_check(checks.harness_coverage(ROOT))

    @GATE
    def test_install_flags(self):
        self.assert_check(checks.install_flags(ROOT))

    @GATE
    def test_top_level_files(self):
        self.assert_check(checks.top_level_files(ROOT))

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
        self.assertIn("[download record omitted]", text)
        for relative in (
            ".claude-plugin/marketplace.json",
            ".claude-plugin/plugin.json",
            "harnesses/skills.json",
            "harnesses/integrations.json",
        ):
            self.assertIn(relative, text)
        home = str(Path.home())
        if len(home) > 1:
            self.assertNotIn(home, text)

    def test_snapshot_encoded_size_fits_exec_argv(self):
        text = snapshot.snapshot()
        self.assertLess(len(text.encode()), 100_000)

    def test_generated_lock_json_is_summarized(self):
        self.assertTrue(snapshot._is_lockfile("skills/sdlc/scripts/workflow.lock.json"))
        self.assertTrue(snapshot._is_lockfile("harnesses/openwiki/package-lock.json"))
        self.assertTrue(snapshot._is_lockfile("harnesses/graphify/requirements.lock"))
        self.assertFalse(snapshot._is_lockfile("harnesses/integrations.json"))
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
            (root / "harnesses").mkdir()
            (root / "harnesses" / "muse").mkdir()
            (root / "harnesses" / "muse" / "README.md").write_text("docs only\n", encoding="utf-8")
            (root / "harnesses" / "skills.json").write_text(
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
            self.assertFalse(any("harnesses/muse" in line for line in covered["evidence"]))

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
            (root / "harnesses").mkdir()
            (root / "harnesses" / "skills.json").write_text(
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
            (root / "harnesses").mkdir()
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
            skills = root / "harnesses" / "skills.json"
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

    def test_judge_prompt_is_argv1_with_extra_args(self):
        script = ROOT / "evals" / "repo-quality" / "judge.py"
        environment = os.environ.copy()
        environment.pop("CURSOR_API_KEY", None)
        environment["REPO_QUALITY_JUDGE"] = (
            f"{sys.executable} -c \"import sys; sys.stdout.write(sys.argv[1])\""
        )
        completed = subprocess.run(
            [sys.executable, str(script), "GRADE-PROMPT", "{\"options\":true}", "{\"context\":true}"],
            cwd=tempfile.gettempdir(),
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
        self.assertEqual(completed.stdout.strip(), "GRADE-PROMPT")

    def test_failed_judge_does_not_emit_its_stdout(self):
        script = ROOT / "evals" / "repo-quality" / "judge.py"
        environment = os.environ.copy()
        environment.pop("CURSOR_API_KEY", None)
        environment["REPO_QUALITY_JUDGE"] = (
            f"{sys.executable} -c \"import sys; sys.stdout.write('SECRET-GRADE'); sys.exit(1)\""
        )
        completed = subprocess.run(
            [sys.executable, str(script), "GRADE-PROMPT", "{\"options\":true}", "{\"context\":true}"],
            cwd=tempfile.gettempdir(),
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("SECRET-GRADE", completed.stdout)
        self.assertNotIn("SECRET-GRADE", completed.stderr)
        self.assertIn("judge provider: REPO_QUALITY_JUDGE", completed.stderr)

    def _judge_module(self, name):
        path = ROOT / "evals" / "repo-quality" / "judge.py"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_judge_timeout_is_900_seconds_and_retries_once(self):
        module = self._judge_module("repo_quality_judge_timeout")
        self.assertEqual(module.TIMEOUT_SECONDS, 900)
        self.assertEqual(module.TIMEOUT_ATTEMPTS, 2)
        saved = os.environ.copy()
        try:
            os.environ.pop("CURSOR_API_KEY", None)
            os.environ["REPO_QUALITY_JUDGE"] = f"{sys.executable} -c \"import sys; sys.exit(0)\""
            attempts = {"n": 0}

            def once(command, **kwargs):
                attempts["n"] += 1
                self.assertEqual(kwargs["timeout"], 900)
                if attempts["n"] == 1:
                    raise subprocess.TimeoutExpired(command, 900)
                return subprocess.CompletedProcess(command, 0, stdout="grade\n", stderr="")

            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.object(module.subprocess, "run", once), \
                    mock.patch.object(module.sys, "stdout", stdout), \
                    mock.patch.object(module.sys, "stderr", stderr):
                code = module.main(["judge.py", "GRADE-PROMPT"])
            self.assertEqual(code, 0, stderr.getvalue())
            self.assertEqual(attempts["n"], 2)
            self.assertEqual(stdout.getvalue(), "grade\n")
            self.assertIn("retrying once", stderr.getvalue())
            self.assertNotIn("GRADE-PROMPT", stdout.getvalue() + stderr.getvalue())

            def always(command, **kwargs):
                raise subprocess.TimeoutExpired(command, kwargs.get("timeout"))

            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.object(module.subprocess, "run", always), \
                    mock.patch.object(module.sys, "stdout", stdout), \
                    mock.patch.object(module.sys, "stderr", stderr):
                code = module.main(["judge.py", "GRADE-PROMPT"])
            self.assertEqual(code, 124)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("judge timed out; retrying once\n", stderr.getvalue())
            self.assertIn("judge timed out\n", stderr.getvalue())
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def test_default_grok_judge_uses_prompt_file(self):
        path = ROOT / "evals" / "repo-quality" / "judge.py"
        spec = importlib.util.spec_from_file_location("repo_quality_judge", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        saved = os.environ.copy()
        try:
            os.environ.pop("CURSOR_API_KEY", None)
            os.environ.pop("REPO_QUALITY_JUDGE", None)
            argv, _environment, stdin, provider = module.judge_invocation(
                "SECRET-PROMPT", "prompt.txt"
            )
        finally:
            os.environ.clear()
            os.environ.update(saved)
        self.assertEqual(provider, "grok")
        self.assertIsNone(stdin)
        self.assertIn("--prompt-file", argv)
        self.assertIn("prompt.txt", argv)
        self.assertNotIn("SECRET-PROMPT", argv)
        self.assertNotIn("-p", argv)

    def test_eval_yaml_structure(self):
        config = load_eval_config(EVAL_YAML)
        self.assertEqual(config["providers"], ["exec:python3 snapshot.py"])
        self.assertEqual(
            config["defaultTest"]["options"]["provider"],
            "exec:python3 judge.py",
        )
        tests = config["tests"]
        self.assertEqual(len(tests), 10)
        metrics = []
        for test in tests:
            assertions = test["assert"]
            self.assertEqual(len(assertions), 1)
            item = assertions[0]
            self.assertEqual(item["type"], "llm-rubric")
            self.assertEqual(item["threshold"], 1.0)
            self.assertIn(item["metric"], METRICS)
            metrics.append(item["metric"])
            rubric = item["value"]
            for anchor in ("10:", "7:", "5:", "3:", "0:"):
                self.assertIn(anchor, rubric)
            self.assertIn('{"pass": bool, "score": 0..1, "reason": "..."}', rubric)
            self.assertIn("file paths", rubric)
        self.assertEqual(metrics, list(METRICS))

    @unittest.skipUnless(os.environ.get("RUN_JUDGE") == "1", "set RUN_JUDGE=1 to run promptfoo")
    def test_judge_eval(self):
        output = ROOT / "evals" / "repo-quality" / "results" / "latest.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            [
                "npx", "-y", PROMPTFOO_PACKAGE, "eval",
                "-c", "evals/repo-quality/eval.yaml",
                "--no-cache", "-o", "evals/repo-quality/results/latest.json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
        detail = (completed.stdout + "\n" + completed.stderr)[-4000:]
        self.assertTrue(output.is_file(), detail)
        scores = _metric_scores(output)
        for metric in METRICS:
            self.assertIn(metric, scores, detail)
            self.assertEqual(scores[metric], 1.0, detail)
        self.assertEqual(completed.returncode, 0, detail)


if __name__ == "__main__":
    unittest.main()
