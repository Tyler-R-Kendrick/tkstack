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
python3 scripts/evolve.py learn --backend mock --dry-run
python3 scripts/evolve.py learn
python3 scripts/evolve.py sdlc
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
