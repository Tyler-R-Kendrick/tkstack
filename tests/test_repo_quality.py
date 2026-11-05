"""Deterministic repo-quality checks and the promptfoo eval config."""

import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVAL_YAML = ROOT / "evals" / "repo-quality" / "eval.yaml"
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


checks = load_checks()


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
        completed = subprocess.run(
            [sys.executable, "snapshot.py", "PROMPTFOO-ARGV-PROBE", "{\"config\":true}", "{\"vars\":{}}"],
            cwd=script.parent,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
        self.assertIn("## README.md", completed.stdout)
        self.assertIn("## install.sh", completed.stdout)
        self.assertNotIn("PROMPTFOO-ARGV-PROBE", completed.stdout)

    def test_judge_prompt_is_argv1_with_extra_args(self):
        script = ROOT / "evals" / "repo-quality" / "judge.py"
        environment = os.environ.copy()
        environment.pop("CURSOR_API_KEY", None)
        environment["REPO_QUALITY_JUDGE"] = (
            f"{sys.executable} -c \"import sys; sys.stdout.write(sys.argv[1])\""
        )
        completed = subprocess.run(
            [sys.executable, str(script), "GRADE-PROMPT", "{\"options\":true}", "{\"context\":true}"],
            cwd="/tmp",
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
        self.assertEqual(completed.stdout.strip(), "GRADE-PROMPT")

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
                "npx", "-y", "promptfoo@latest", "eval",
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
        self.assertEqual(completed.returncode, 0, detail)
        self.assertTrue(output.is_file(), detail)


if __name__ == "__main__":
    unittest.main()
