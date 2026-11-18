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

Prepare reviewed authored cases for the current agent with:

```sh
python3 skills/learn/scripts/evolve.py learn --dry-run
python3 skills/learn/scripts/evolve.py constrain
```

This validates case shape and pinned inputs without invoking a model or launching
another harness. The current agent performs any semantic evaluation in its
existing conversation. Cases and labels it can see are not independent holdouts.
The old separate-backend results below are historical and do not authorize
replaying another model or agent.

## All 19 owned skills

Every owned skill now has a reviewed `evals/<skill>/tasks.json`. The driver accepts
all actual owned names. The original four-case learn/SDLC suites are retained;
the other 17 have authored train/validation/test policy scenarios. Current-source
real handoff results are recorded in
[the 2026-10-31 aggregate](results/2026-10-31-owned-skills.json). Every strict gate
rejected a perfect tie; no arbitrary optimizer edit was adopted. These narrow
policy cases complement actual compiler/native/report behavior tests, rather
than replacing full skill outcomes or creative/provider execution.

Constrain's authored decisions include test overlap, mutation survivors,
boundary protection and agent outcomes. The replay supplies the target
`SKILL.md` text, so these multiple-choice cases do not by themselves exercise
the linked test-value reference or demonstrate a working portfolio review.
Measuring that procedure requires representative repository tasks, actual
runner traces and independently reviewed outcomes; a mock run checks wiring only.
Evalify's authored decisions and local fixture-judge integration similarly do
not establish a calibrated live judge or a measured skill-quality gain.

## Host-bound testing improvements

The [2026-11-17 measured record](results/2026-11-17-host-bound-hill-climb.md)
documents repeated local regression scenarios, superseded attempts, and the
limits of same-conversation model evaluation.

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

The [rubric anchors](repo-quality/rubrics.md) can be reviewed by the invoking
agent in its current conversation. They do not launch a separate model or
harness, and a same-context review is not an independent benchmark.
