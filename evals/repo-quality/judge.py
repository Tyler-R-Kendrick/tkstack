#!/usr/bin/env python3
"""Headless judge for the repo-quality promptfoo exec provider.

Promptfoo passes the rendered grading prompt as argv[1], then provider options
and call context as further arguments. Only argv[1] is the prompt. This process
prints model text on stdout only when the judge exits 0. Environment variables
and secrets are never printed. The judge does not resolve a repository root
and does not read the working directory. The snapshot provider resolves the
checkout as parents[2] of its own file.

The default command writes the prompt to a temp file and runs:
  grok --prompt-file <file> -m grok-4.7 --output-format plain --disable-web-search
The prompt is not a grok argument. The child cwd is that temp directory and
its environment is limited to path, home, locale, and temp variables.

When CURSOR_API_KEY is set and REPO_QUALITY_JUDGE is unset, the judge is
cursor-agent. That CLI has no prompt-file flag, so the prompt is its stdin,
not an argument:
  cursor-agent -p --model composer-2.5
REPO_QUALITY_CURSOR_MODEL replaces composer-2.5. CURSOR_API_KEY is the only
extra environment variable forwarded.

REPO_QUALITY_JUDGE replaces the whole command. Put {prompt} where the prompt
argument belongs, or {prompt_file} where the file path belongs. When neither
token is present, the prompt is appended.
"""

import errno
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


TIMEOUT_SECONDS = 300
_ENV_KEYS = (
    "PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE",
    "TMPDIR", "TMP", "TEMP", "SYSTEMROOT", "PATHEXT",
)


def _minimal_env(extra=None):
    environment = {key: os.environ[key] for key in _ENV_KEYS if os.environ.get(key)}
    environment.setdefault("LANG", "C.UTF-8")
    if extra:
        environment.update(extra)
    return environment


def judge_invocation(prompt, prompt_file):
    """Return argv, env, stdin text, and a provider name safe to log."""
    override = os.environ.get("REPO_QUALITY_JUDGE", "").strip()
    if override:
        return _apply_prompt(shlex.split(override), prompt, prompt_file), _minimal_env(), None, "REPO_QUALITY_JUDGE"
    if os.environ.get("CURSOR_API_KEY"):
        model = os.environ.get("REPO_QUALITY_CURSOR_MODEL", "composer-2.5").strip() or "composer-2.5"
        environment = _minimal_env({"CURSOR_API_KEY": os.environ["CURSOR_API_KEY"]})
        return ["cursor-agent", "-p", "--model", model, "--trust"], environment, prompt, "cursor-agent"
    return [
        "grok", "--prompt-file", prompt_file, "-m", "grok-4.7",
        "--output-format", "plain", "--disable-web-search",
    ], _minimal_env(), None, "grok"


def _apply_prompt(parts, prompt, prompt_file):
    if not parts:
        raise SystemExit("REPO_QUALITY_JUDGE is empty")
    if any(part in ("{prompt}", "{prompt_file}") for part in parts):
        replaced = []
        for part in parts:
            if part == "{prompt}":
                replaced.append(prompt)
            elif part == "{prompt_file}":
                replaced.append(prompt_file)
            else:
                replaced.append(part)
        return replaced
    return [*parts, prompt]


def main(argv):
    # Extra promptfoo arguments (options JSON, context JSON) stay unused.
    if len(argv) < 2 or argv[1] == "":
        sys.stderr.write("judge.py expects the prompt as argv[1]\n")
        return 2
    prompt = argv[1]
    with tempfile.TemporaryDirectory(prefix="repo-quality-judge-") as temporary:
        prompt_path = Path(temporary) / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        command, environment, stdin_text, provider = judge_invocation(prompt, str(prompt_path))
        sys.stderr.write(f"judge provider: {provider}\n")
        run = {
            "cwd": temporary,
            "env": environment,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": TIMEOUT_SECONDS,
            "check": False,
        }
        if stdin_text is None:
            run["stdin"] = subprocess.DEVNULL
        else:
            run["input"] = stdin_text
        try:
            completed = subprocess.run(command, **run)
        except subprocess.TimeoutExpired:
            sys.stderr.write("judge timed out\n")
            return 124
        except OSError as error:
            if error.errno == errno.E2BIG:
                sys.stderr.write("judge prompt exceeds the command-argument limit\n")
            else:
                sys.stderr.write(f"judge executable not found: {command[0]}\n")
            return 127
    if completed.returncode != 0:
        # Child stderr and a failed stdout can echo credentials or look like a grade.
        sys.stderr.write(f"judge exited {completed.returncode}\n")
        return completed.returncode
    sys.stdout.write(completed.stdout)
    if completed.stdout and not completed.stdout.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
