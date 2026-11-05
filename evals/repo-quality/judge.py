#!/usr/bin/env python3
"""Headless judge for the repo-quality promptfoo exec provider.

Promptfoo passes the rendered grading prompt as argv[1], then provider options
and call context as further arguments. Only argv[1] is the prompt. This process
prints the model text on stdout and nothing else. Environment variables and
secrets are never printed. The repository root is this file's parent directory
when a caller needs it; the judge itself does not read the working directory.

The default command is:
  grok -p <prompt> -m grok-4.7 --output-format plain --disable-web-search

When CURSOR_API_KEY is set and REPO_QUALITY_JUDGE is unset:
  cursor-agent -p --model composer-2.5 <prompt>
REPO_QUALITY_CURSOR_MODEL replaces composer-2.5.

REPO_QUALITY_JUDGE replaces the whole command. Put the token {prompt} where
the prompt argument belongs. When that token is absent, the prompt is appended.
"""

import errno
import os
import shlex
import subprocess
import sys


TIMEOUT_SECONDS = 300


def judge_command(prompt):
    override = os.environ.get("REPO_QUALITY_JUDGE", "").strip()
    if override:
        return _apply_prompt(shlex.split(override), prompt)
    if os.environ.get("CURSOR_API_KEY"):
        model = os.environ.get("REPO_QUALITY_CURSOR_MODEL", "composer-2.5").strip() or "composer-2.5"
        return ["cursor-agent", "-p", "--model", model, prompt]
    return [
        "grok", "-p", prompt, "-m", "grok-4.7",
        "--output-format", "plain", "--disable-web-search",
    ]


def _apply_prompt(parts, prompt):
    if not parts:
        raise SystemExit("REPO_QUALITY_JUDGE is empty")
    if any(part == "{prompt}" for part in parts):
        return [prompt if part == "{prompt}" else part for part in parts]
    return [*parts, prompt]


def main(argv):
    # Extra promptfoo arguments (options JSON, context JSON) stay unused.
    if len(argv) < 2 or argv[1] == "":
        sys.stderr.write("judge.py expects the prompt as argv[1]\n")
        return 2
    prompt = argv[1]
    command = judge_command(prompt)
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write("judge timed out\n")
        return 124
    except OSError as error:
        if error.errno == errno.E2BIG:
            sys.stderr.write("judge prompt exceeds the command-argument limit\n")
        else:
            sys.stderr.write(f"judge executable not found: {command[0]}\n")
        return 127
    sys.stdout.write(completed.stdout)
    if completed.stdout and not completed.stdout.endswith("\n"):
        sys.stdout.write("\n")
    if completed.returncode != 0:
        # Child stderr can echo credentials. Report only the status.
        sys.stderr.write(f"judge exited {completed.returncode}\n")
        return completed.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
