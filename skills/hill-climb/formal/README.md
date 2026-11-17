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

## Lean proof and implementation correspondence

`Budget.lean` proves three statements over unbounded natural numbers:

- `reservation_preserves` proves that an accepted reservation results in
  reserved plus settled usage at or below the limit.
- `bounded_settlement_preserves` proves that replacing held tokens with no more
  than the held amount preserves an already valid ceiling.
- `overrun_blocks_reservation` proves that settling more than was held sets an
  overrun state in which every later reservation is refused.

The checker audits theorem dependencies and permits only Lean's kernel axioms
`propext`, `Quot.sound`, and `Classical.choice`. `sorryAx`, undeclared result
axioms, compiler warnings, and an unrecognized Lean version fail the bridge.
For this proof Lean actually reports `propext` and `Quot.sound` for the first
two theorems and `propext` for the third. The specification assumes an atomic
check-and-reserve and truthful provider usage. It does not prove SQLite,
filesystem durability, trial-unit/proposal limits, or provider-side hard caps.
An actual provider overrun is recorded and blocks later reservations; the first
ceiling claim assumes no such overrun.

`lean_bridge.py` executes the proved Lean definitions to obtain oracle cases,
then exercises the real SQLite `Ledger` against 175 reservation and 175
settlement cases within values zero through four. It includes zero amounts,
exact-boundary admissions, release, and overrun blocking. The accompanying tests
verify that a ledger mutant which ignores active token reservations disagrees
with the oracle and that replacing a proof with `sorry` is rejected. This is
finite behavioral correspondence evidence, not a proof of the Python program
for every integer or interleaving. The real concurrent admission test exercises
SQLite's `BEGIN IMMEDIATE` boundary separately. The TLA+ model checks bounded
interleavings and does not establish Lean-to-Python equivalence.

Run with the official Lean 4.19.0 Linux x86-64 release binary:

```sh
LEAN_BIN=/path/to/lean-4.19.0-linux/bin/lean \
  python3 -B -m unittest discover -s tests -p test_experiment_lean.py -v
```

The existing CI job downloads
`https://github.com/leanprover/lean4/releases/download/v4.19.0/lean-4.19.0-linux.tar.zst`
and checks SHA-256 `6fe3ce97a58f44e2b3567d455b994eacec5bfe9ae7774f2a573444480ba813fe`
before extraction. The hash was calculated from the downloaded official
release asset; it is a reproducibility pin, not an independent attestation.
The checker also verifies the compiler identifies itself as Lean 4.19.0, commit
`6caaee842e94`. The normal offline suite explicitly skips this bridge if
`LEAN_BIN` is unavailable. The CI job always runs it.

## Proposal attempt count

The Lean `proposal_start_preserves` theorem proves that a successful fresh
proposal admission cannot exceed its limit. `proposal_trace_preserves` proves
by induction that any finite accepted sequence of fresh admissions and
completions remains within the limit, from a state already within the limit.
`proposal_finish_keeps_count` and
`proposal_finish_does_not_restore_capacity` establish that completion neither
refunds the attempt nor reopens exhausted capacity. The proof covers all natural
numbers and all finite accepted action sequences. It assumes that the limit is
immutable, each authorized fresh start consumes exactly one attempt, and the
check and increment are one atomic transition. It does not prove external host
execution, cancellation truthfulness, token spending, isolation, database
implementation, or unique-key enforcement.

The Lean oracle also emits 14 cases spanning proposal limits one through four
and each valid prior attempt count. The SQLite bridge creates mixed host and
scripted proposal histories, marks host responses uncertain, finishes host
proposals, cancels scripted reservations, checks that none refund attempts,
and tests a fresh host admission against the Lean result. It also checks that a
host admission grants dispatch once and that reusing its key does not grant
another. The bridge reads the durable count directly from SQLite. A mutation
changing the real proposal guard from `>=` to `>` must fail this check. Another
mutation replaces the sequence theorem with an axiom, which the checker must
reject. These are finite implementation-correspondence tests, not a proof of
SQLite concurrency; the separate simultaneous-dispatch test exercises that
boundary. Host model token usage remains reported by the host or unknown and is
not covered by the local token-budget theorem.

## Launch admission

`launch_requires_registration` and `launch_respects_cancellation` prove the
Boolean admission decision cannot grant a launch unless the process identity is
registered and the cancellation flag is clear. The production POSIX launch
path invokes `launch_permitted` with an identity check and the current flag
while holding the cancellation-scope lock, immediately before writing the
staged child permit. The bridge checks all four Boolean inputs against the
checked Lean definition and detects mutations that ignore either input.

A real staged-process integration test observes the registered, uncancelled
inputs and confirms that replacing the production predicate with a denial
prevents the target from running. It also observes the registered, cancelled
inputs after pre-cancellation. Those tests establish that the helper participates
in the tested path. They do not prove all Python interleavings, lock behavior,
process identity reuse, signal delivery, reaping, host crashes, nested scopes,
remote jobs, or detached descendants. Those require the separate lifecycle,
concurrency, and provider-boundary checks. The Lean theorem assumes the Boolean
inputs faithfully represent state held under the shared lock and does not prove
that the process is ultimately terminated.
