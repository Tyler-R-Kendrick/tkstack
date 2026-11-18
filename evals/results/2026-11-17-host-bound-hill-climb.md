# Host-bound testing improvement evidence

This run improved concrete repository behavior in Learn, Constrain, Hill-climb
and their supporting execution code. The current agent performed the work in
its existing conversation; no separate model or agent harness was invoked.
The detailed [machine-readable record](2026-11-17-host-bound-hill-climb.json)
contains plans, runner sources and hashes, repetitions, representative logs,
and the same-conversation Evalify smoke test.

The rows below are authored regression scenarios, not a count of independent
risks or a proof that each test has unique value. Before the corresponding
change its target failed in all three repetitions; after the change it passed
in all three. A separate existing behavioral guard passed in all three runs
before and after. The [follow-up value review](2026-11-18-mutation-test-value.md)
groups overlapping risks, identifies the scratch-only checks, and measures a
sample of real faults against individual tests.

| Scenario | Before | After |
| --- | ---: | ---: |
| Direct-workflow timing cannot be hidden by payload names | 0/3 | 3/3 |
| Different test fixtures/decorators are not declared duplicates | 0/3 | 3/3 |
| Borderline large-sample gains use conservative t intervals | 0/3 | 3/3 |
| Generated test deadlines stop ordinary POSIX descendants | 0/3 | 3/3 |
| Model-based comparisons require repetition and nonzero noise | 0/3 | 3/3 |
| Evalify rejects a selected external executable | 0/3 | 3/3 |
| Evolution rejects an alternate backend selector | 0/3 | 3/3 |
| Offline framework scores retained host judgments | 0/3 | 3/3 |
| The runner rejects a separate model profile | 0/3 | 3/3 |
| Codify rejects a separate agent-runtime scaffold | 0/3 | 3/3 |
| Compilation freezes the inventory freshness checking expects | 0/3 | 3/3 |
| Calibration separates false positives from false negatives | 0/3 | 3/3 |
| Timing summaries retain missing observations as unknown | 0/3 | 3/3 |
| Extreme durations fail cleanly before analysis | 0/3 | 3/3 |

Three earlier scenarios concerned a provider-capable Evalify adapter or an
older evolution interface. They remain in the detailed history but were
superseded by the user's host-only correction and are not counted above.
On the final adapter, concurrent-path reservation and ordinary descendant
cleanup each passed three additional stability runs without a before/after
claim. The t critical-value table was independently cross-checked against
SciPy; that checks the numeric table, not the independence of cases.

The final merged stack passed 590 unittest cases, with 10 skipped, including
the deterministic repository-quality gate and real offline Promptfoo
assertions. Its 349.770-second suite runtime is a verification observation,
not a performance benchmark.

These cases and expected outcomes were authored in the same session as the
changes. They are targeted correctness evidence, not an independent holdout or
a measured improvement in model judgment. The Evalify smoke used the current
agent's own judgments and self-authored labels; all host judgment durations were
unknown. Promptfoo scored the retained labels without calling a model.

The original summary also counted a scratch check for the absence of a
`CommandProvider` symbol. That structural probe has been removed from the
highlighted set: the permanent proposer test checks the stronger behavior that
an alternative provider is rejected before the ledger reserves anything. The
machine-readable historical run is retained as provenance, not as a separate
claim of independent regression value.

The shared runner records local timing for compiled operations. Direct helpers
and MCP calls made by other hosts do not automatically pass through it, and
host-reported model identity or durations are not authenticated by these
records. A timeout does not prove remote cancellation or a latency SLO.
