# Experiment controller model

Run `python3 skills/hill-climb/formal/model_check.py` from the checkout and
`python3 -m unittest discover -s tests -p test_experiment_model.py -v` for the
independent regression checks. The program breadth-first enumerates all states
reachable under the finite transitions in `model_check.py`, including crashes,
reconciliation and external ref writes. It prints state counts and shortest
counterexamples for deliberately weakened transitions. A successful command
means the declared properties hold within this model and both weakened examples
fail. It does not model check the implementation.

## Bounds and assumptions

- Budget model: two workers, one resource unit and one-unit attempts. Each
  worker checks, reserves, dispatches and can lose a response. Settlement uses
  at most the reservation. A lost response remains charged. Cancellation after
  dispatch is allowed only on a true externally confirmed non-execution.
  The finite model uses unit reservation and does not cover provider-specific
  token accounting or settlement amounts.
- Promotion model: one eligible decision, one controller write, one reference,
  three possible reference values and at most three reference writes. External
  actors may write the same value or move away and back. A crash can occur after
  recording the intent and before acknowledgement. The model records the value
  and generation observed at write and models a reference generation and writer
  marker that change atomically with the ref. This is an **abstract assumption**,
  not a Git feature. Plain `git update-ref` compares an object ID, not a
  generation or writer marker, and thus does not prevent an ABA change. The
  local controller uses a generation ref and receipt ref in a guarded Git
  transaction and assumes the controller is their sole writer. Direct ref
  changes can bypass the generation protocol. A crash may leave a mismatch
  between refs; recovery treats such states as unresolved. Never infer that
  this bounded model authenticates an actual Git write.
- An intent is eligible when recorded. The state machine does not model how
  evidence becomes eligible, workflow compilation, file isolation, cleanup,
  held-out evaluations, or provider behavior. It checks safety, not liveness.
  Fairness, durable storage and honest verifier observations are assumptions,
  not proved properties.

## Invariants and induction

Budget conservation states `settled + reserved + unknown <= 1`. It holds in the
initial state. The atomic reservation checks this bound and changes the state in
one transition. Dispatch and unknown outcomes retain their charge, settlement
retains the charge, and verified cancellation removes it. Therefore every modeled
transition preserves the invariant. The broken transition permits two workers to
read capacity before either writes and then reserve from stale observations.

Guarded promotion records the value and generation of the eligible decision.
The controller write is enabled only when both still match, and the recorded
write origin is therefore the expected pair. External writes cannot change that
historical origin. Recovery commits only when its assumed owner marker and
expected next generation identify the controller's write; otherwise it retries
only an unchanged pair or quarantines. Disabling the guard exposes a shortest
counterexample with a same-value external write between intent and promotion.
The marker assumption matters: two independently authorized processes writing
identical Git object IDs cannot be distinguished from SHA values alone.

Run integration tests against actual SQLite transactions and the deployed Git
coordinator in addition to this model. Match those transitions and assumptions
to the real implementation before making a promotion-integrity claim.

## TLA+ and TLC

`Budget.tla` and `Promotion.tla` are independent TLA+ specifications of the
bounded reservation and promotion state machines. The `.cfg` files provide a
safe configuration and deliberately weakened configurations. `run_tlc.py`
runs all five in isolated temporary directories and rejects unexpected errors,
missing violations, and an unrecognized JAR. The tests run these models only
when `TLAPLUS_JAR` is set. They otherwise report an explicit skip.

Download the official [TLA+ v1.8.0 release asset](https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar)
and verify it before execution. The upstream [release notes](https://github.com/tlaplus/tlaplus/releases/tag/v1.8.0)
publish SHA-1 `c6b8b312cc68d83fa3513c6cf331a1b125a09011` for the JAR. The
SHA-256 calculated from those verified bytes is
`7e53aa636dac8a3cb0533f343115c0548e03fc0ce5edc7739becf58d3d0fb84f`.
The artifact is not included in this package. A Java runtime is required.

```sh
sha256sum /path/to/tla2tools.jar
python3 skills/hill-climb/formal/run_tlc.py --jar /path/to/tla2tools.jar
TLAPLUS_JAR=/path/to/tla2tools.jar python3 -m unittest discover -s tests -p test_experiment_model.py -v
```

Observed with this JAR and Java 21: `BudgetSafe` checked 33 distinct states and
`PromotionSafe` checked 123 distinct states. TLC produced the expected
`BudgetSafe` counterexample with the stale reservation, and `OriginSafe`
counterexamples when the promotion guard is disabled or an external writer
moves the ref away and back without advancing the generation. TLC uses state
fingerprints, which have a small collision probability. These counts and claims
cover the configured finite bounds only. The budget model assumes provider
settlement never exceeds the reservation. Actual overruns must be recorded and
stop further spending; they do not satisfy that hard-ceiling assumption.

The TLA+ promotion model assumes every ref writer advances the shared generation
in the same atomic transaction, and that the operation marker, generation and
ref update are mutually visible for recovery. The controller can implement a
multi-ref `update-ref` transaction, but an external process that writes only the
integration ref violates this assumption. Protect the private Git directory and
quarantine ambiguous recovery. Evidence validity, multiple independent
operations, real filesystem permissions, and Git backend crash guarantees are
outside the finite specification. `OriginSafe` and `CommitSafe` validate the
modeled guarded origin and acknowledgement, not arbitrary user authorization or
the content of evaluation evidence.
