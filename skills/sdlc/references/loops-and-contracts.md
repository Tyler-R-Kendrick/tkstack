# Development loops and contract evidence

Read this before choosing test seams or dispatching implementation work. Keep
the loop about observable behavior and the boundary at which it can be proved.

## Outer loop: deliver the right behavior

The coordinator owns this loop:

1. Freeze the initial workload: user requirements, acceptance examples,
   exclusions, compatibility obligations, and the evidence plan. Record its
   content hash and starting commit. Scope changes become explicit amendments;
   preserve the original definition.
2. Turn each requirement into BDD scenarios and identify the smallest public
   seams that can prove them. Specify producer/consumer contracts before
   parallel branches implement either side.
3. Decompose into independently verifiable deliverables and a dependency DAG.
   Dispatch ready nodes whose prerequisites and contract versions are available.
   One owner implements a node; separate reviewers challenge it.
4. Integrate green slices through incremental commits and stacked PRs. Re-run
   consumer/provider compatibility when a boundary or a stack parent changes.
5. Have an independent reviewer reconcile the latest branch evidence against
   its frozen initial workload and amendments. Required unmet or unproved
   behavior remains open work, even when every existing test passes.

An outer-loop discovery can change the graph or the design. It does not erase
an inconvenient requirement or retroactively redefine a failed scenario.
The loops have an explicit return edge: development may expose an impossible or
ambiguous requirement, a broken design assumption, an incompatible shared
contract, or a new dependency. Record the finding using
[durable coordination](durable-task-graph.md), pause affected descendants, stop
their writers, and return to requirements/architecture planning. Preserve the
initial workload; append an authorized amendment and an ADR when architecture
changes. Update scenarios, contract versions, graph ownership, and evidence
plans; invalidate affected proof before re-entering the inner loop. Unaffected
branches continue. Ordinary defects under the same acceptance remain inner-loop
work; environment failures remain blockers, not intended behavioral red proof.

## Inner loop: red, green, refactor

Each implementation owner repeats this loop inside its isolated task branch:

1. **Red:** select one scenario or contract obligation. Write the smallest
   executable example at its public seam and run it against the current
   implementation. Observe the intended failure. Capture the command, test
   identifier, input/fixture version, exit status, and relevant output.
   An import error, unavailable service, or invalid fixture is a harness failure,
   not evidence that the desired behavior is missing.
2. **Green:** implement only what makes that example pass. Run that example and
   the affected contract checks. Record the passing result against the exact
   code revision. Preserve validation, error handling, and existing obligations.
3. **Refactor:** improve structure under the passing tests and contracts. Keep
   changes inside the node's ownership boundaries; extend the graph before
   taking another branch's files or changing a shared contract.
4. **Commit:** commit the coherent behavior, its tests, and its evidence manifest.
   A published incremental commit should remain usable and green. Preserve red
   proof as an artifact tied to a reproduction revision or recorded test patch;
   a red test alone is not a completed deliverable.

Work vertically: one behavior, one failing observation, one minimal change, one
passing observation. A pure documentation or configuration task can use an
appropriate deterministic acceptance check instead of inventing a unit test.
Name the reason when a red reproduction cannot be obtained; do not claim TDD
was performed for that slice.

## BDD: examples define acceptance

Use the project's existing runner; BDD does not require installing a Gherkin
framework. A scenario has a stable ID, requirement IDs, a **Given** state,
one **When** action, and observable **Then** outcomes. Parameterize genuine
behavior variations rather than duplicating the implementation in assertions.

Include negative and boundary examples where the requirement needs them:
invalid input, authorization, absent data, retries, idempotency, partial failure,
ordering, and backward compatibility. Assertions should name behavior at a
public seam, not private method calls or the implementation's internal shape.

An example of an atomic slice:

```gherkin
Scenario: S-001, tied to R-001 and C-001
  Given a valid order exists and its version is 3
  When its owner requests cancellation with expected version 3
  Then the order becomes cancelled and version 4 is returned
  And repeating the same cancellation returns the same outcome
```

The state transition, response, and idempotency can be proved at the order
service boundary. A browser journey through every deployed service adds no
necessary acceptance condition to this scenario.

## Contract testing replaces E2E dependence

Select consumer-driven, provider-driven, or a shared contract explicitly. Record
the actual producers and consumers, their immutable revisions or artifact
digests, and the supported compatibility combinations. A contract covers the
observable request, response/event shape, and required semantics: error codes,
ordering, side effects, version negotiation, retries, or idempotency as relevant.

| Check | What it proves | What it cannot prove alone |
| --- | --- | --- |
| Consumer behavior against recorded contract examples | The consumer handles its declared interactions | The real producer can satisfy them |
| Provider verification using those same interactions against the real provider implementation | The producer meets the consumer's stated contract | The consumer implements its own behavior correctly |
| Schema or type validation | Structural compatibility | Required semantics, actual provider behavior, or every deployed combination |
| Narrow component/adapter integration with a real dependency | The selected boundary works, including relevant persistence or protocol semantics | The correctness of an entire production journey |

A stub or mock is useful in an inner loop. Its success becomes contract proof
only when its expectations are verified against the real producer. Verify both
sides before declaring a cross-branch boundary satisfied. For events, include
delivery/ordering and duplicate handling where required; for storage adapters,
exercise relevant constraints and transaction behavior against the actual
dependency or a faithful supported equivalent.

Publish the contract artifact first or place its owner ahead of consumers in
the DAG. Consumers may proceed against a pinned artifact once that dependency
is available; their branch stays blocked from integration until provider
verification covers the required version matrix. Treat a contract change as
a versioned deliverable with affected consumers, migration ordering, and fresh
verification rather than a shared-file edit by every worker.

Keep the acceptance suite at behavior, component, and contract boundaries.
Do not replace missing contract verification with an E2E run. Existing E2E
results may be additional observations if relevant, but do not make them the
acceptance strategy or add new E2E coverage to satisfy these requirements.

## Collect the evidence the requirement needs

Plan artifacts before work so the baseline can still be captured. Record their
requirement/scenario/contract IDs, commit, environment, fixture versions,
capture command or procedure, result, and content hash or durable artifact link.
Declare visual, network, and interaction evidence applicability for each
requirement in the workload; non-UI tasks do not need invented browser artifacts.

| Requirement | Appropriate evidence |
| --- | --- |
| API, protocol, or data-boundary behavior | Consumer and real-provider reports, version matrix, request/response examples; sanitized HAR when browser/network behavior matters |
| Visual change | Before/after screenshots at the same viewport, device scale, theme, state, and fixture; identify both build revisions |
| Interaction, animation, focus, or timing | A short recording from the scoped UI/component surface plus targeted behavior assertions |
| Performance | Comparable baseline/candidate traces and measurements with workload, environment, and sampling method |
| CLI or nonvisual behavior | Reproduction transcripts and deterministic check output with inputs and exit status |

Screenshots, recordings, and HAR captures are review artifacts, not a reason to
introduce a full-system E2E suite. A scoped preview may use verified contract
fixtures; label the fixture and retain separate real-provider verification.
Require matched before/after images for applicable visual comparisons. Choose
the side(s) of a HAR or video according to the requirement being demonstrated;
do not require universal pairs that add no evidence.
Scrub credentials, cookies, and private user data before attaching network or
visual artifacts. Keep a retrievable durable copy when CI or hosting artifacts
expire; a broken link cannot satisfy a requirement.

## Close the branch against its original workload

The final reviewer receives the frozen initial workload, its hash, authorized
amendments, the branch's assigned requirement subset, and the evidence index.
For every applicable requirement, compare expected behavior with observed
results; inspect artifacts rather than accepting an implementer's summary.
Record pass, fail, blocked, or a workload-supported not-applicable disposition,
with direct evidence references and an explanation.

Verify that the evidence covers the current head and its actual dependencies.
After a code or base change, repeat affected checks and recapture invalidated
artifacts. No stale green check or screenshot from a different revision proves
the latest branch. Mark missing evidence as missing, not passed. A generated
coverage matrix is a checklist; it cannot judge whether an image or a contract
report actually demonstrates the requirement.

Review findings become granular mitigation nodes with owners and reproduction
cases. Run red/green again for behavior fixes, collect fresh evidence, and have
an independent reviewer close each finding. The branch is ready only when its
required obligations and findings are reconciled against the workload.
