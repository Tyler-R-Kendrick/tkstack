# Custom skill evolution

`learn/tasks.json` and `sdlc/tasks.json` are small **author-created decision
regressions**, derived from the documented skill obligations. They are not
harvested user sessions, production workflow runs, or evidence of broad model
improvement. The target chooses an action in a read-only scenario. Real helper
behavior is tested separately in `tests/`.

Each file keeps training, validation, and final test scenarios separate. Only
training examples and their semantic feedback reach the optimizer. Validation
decides whether a candidate improves, with no individual regression allowed;
test scenarios provide a final measurement and never drive edits. Fixed tests
lose their novelty over repeated tuning; add genuinely new scenarios and retain
their provenance before claiming generalization.

Run the pinned SkillOpt-Sleep engine with:

```sh
python3 src/evolve.py learn --backend mock --dry-run
python3 src/evolve.py learn
python3 src/evolve.py sdlc
```

Default `handoff` runs return exit 3 while fresh-context model replies are
pending. Follow the [official handoff instructions](../vendor/skillopt/plugins/claude-code/commands/skillopt-sleep-handoff.md)
and repeat the identical command for each round. Do not answer from a context
that has seen the references or optimizer run. Completed proposals remain
staged for review; no live skill, memory, steering ledger, or upstream snapshot
is automatically changed. See [the evaluation and usage guide](../docs/skill-evolution.md).

## All 19 owned skills

Every owned skill now has a reviewed `evals/<skill>/tasks.json`. The driver accepts
all actual owned names. The original four-case learn/SDLC suites are retained;
the other 17 have authored train/validation/test policy scenarios. Current-source
real handoff results are recorded in
[the 2026-10-31 aggregate](results/2026-10-31-owned-skills.json). Every strict gate
rejected a perfect tie; no arbitrary optimizer edit was adopted. These narrow
policy cases complement actual compiler/native/report behavior tests, rather
than replacing full skill outcomes or creative/provider execution.

## Repository quality

`evals/repo-quality/` grades this checkout on Unix. `snapshot.py` prints a
bounded snapshot of git-tracked files (file tree, LOC, README, install.sh,
AGENTS.md, manifests, owned SKILL.md frontmatter, `docs/skill-marketplace.md`,
harness docs, and the docs list) with home paths and secret-like values
redacted. File excerpts are capped and generated lock JSON is summarized so
the snapshot stays under 100 KiB. Promptfoo passes that text inside one
grader argument, and a larger snapshot exceeds Linux's per-argument limit.
README.md is placed before the file tree. Without git, the walk
skips `.git`, `__pycache__`, `node_modules`, `.tkstack`, `.venv`, and `venv`.
`judge.py` is the
headless grader. `checks.py` applies deterministic limits and prints a JSON
array of check results.

From the repository root:

```sh
python3 evals/repo-quality/checks.py
python3 -m unittest tests.test_repo_quality -v
```

`checks.py` exits 1 when a limit fails. Ceiling tests stay out of the default
`python3 -m unittest discover` run. Set `REPO_QUALITY_GATE=1` to enforce them;
a failure's text is that check's explanation and evidence.

Promptfoo 0.125.1 grades ten `llm-rubric` metrics and passes only at score 1.0.
`defaultTest.options.provider` is the grader. The default judge writes the
prompt to a file and runs `grok --prompt-file <file> -m grok-4.7 --output-format
plain --disable-web-search`. When `CURSOR_API_KEY` is set, the judge is
`cursor-agent -p --model composer-2.5` with the prompt on stdin.
`REPO_QUALITY_CURSOR_MODEL` replaces that model id. `REPO_QUALITY_JUDGE`
replaces the whole command; put `{prompt}` or `{prompt_file}` where that value
belongs. The judge allows 900 seconds and retries once if that command times
out. The opt-in test requires every metric to score 1.0:

```sh
RUN_JUDGE=1 python3 -m unittest tests.test_repo_quality.RepoQualityTests.test_judge_eval -v
```

That executes `npx -y promptfoo@0.125.1 eval -c evals/repo-quality/eval.yaml --no-cache -o evals/repo-quality/results/latest.json`.
`latest.json` is gitignored.
