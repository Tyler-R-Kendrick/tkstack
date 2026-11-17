# Measured feature work within SDLC

During implementation planning, identify a new feature or an improvement where
the requested outcome has an observable quality difference. Quality can be
qualitative, such as clarity, usability, maintainability, or relevance. Apply
this procedure as part of the SDLC lifecycle without requiring a separate
user invocation. Record the reason when a task does not qualify. A routine
fix with a clear pass/fail regression, a documentation-only edit, or a scoped
review can use its existing evidence plan.

This decision requires interpreting the request and its real context. The
helper can validate recorded facts, but cannot determine intent or whether a
rubric captures user-perceived quality. Do not invent a numeric score as
proof of a semantic judgment.

## Set up the task-scoped harness

Before substantial implementation, record in the workload and task-scoped
harness brief:

- The desired user outcome, relevant scenarios, mandatory behavior, and
  baseline. For a new feature, use an honest minimal reference or mark the
  missing baseline explicitly.
- A metric or anchored qualitative rubric with examples of poor and good
  outcomes, evidence required, acceptance or improvement threshold, and
  an inconclusive outcome. Compare against the same contract and evaluator.
- The required integration target and affected paths. Exercise only the
  toolchains and cross-component boundaries the changed behavior needs, plus
  repository-required checks. A language's presence does not schedule it.
- The evaluator, owner, independent calibration examples, baseline and
  candidate revisions, allowed changes, task budget, and stop rule. Start
  with one incumbent and one bounded challenger when sufficient.

Use the installed `hill-climb` Git-backed task experiments for the private
experiment repository, branch arms, result records, and comparison. Its task
harness brief and native experiment command define the current executable
contract. Follow its host isolation requirements and retain the authoritative
evaluator outside agent-writable code. If that skill or a needed runtime is
unavailable, use an equivalent local task-scoped harness and record the gap.
Do not expand the experiment to unrelated targets or make new paid calls
without an established budget.

## Improve the feature and the harness

Compare the baseline and candidate under the same frozen criteria. Record all
assigned attempts, missing evidence, errors, and measured costs. Required
gates cannot be traded for a higher aggregate. If evidence is insufficient,
leave the comparison inconclusive rather than claiming an improvement.

Capture user feedback with the original observation and a concrete example.
Consider whether it reveals a product defect or a change to the harness:
policies and constraints, metrics, rubric anchors, evaluator, scenarios,
selected skills, context, or workflow. Record the interpretation and revise
the affected harness as well as the feature when evidence calls for it.

For an evaluator or rubric change, validate independently labeled good and
defective examples and regrade both saved candidates under each evaluator
when possible. If the accepted outcome changes, version the contract and
rebaseline. For a workflow, context, or skills change, run fresh matched
trials from the same starting revision under the same relevant budget.
A change affecting both measurement and workflow requires both checks.
Preserve prior revisions and decisions. The proposer cannot make its own
revised evaluator authoritative merely by awarding a higher score.

Use development cases to iterate and hold confirmation cases outside the
proposer's working context. A measured result does not grant publication or
merge authority. SDLC still owns the workload graph, shared scope, evidence,
review, and the authorized delivery boundary. Preserve durable regression
checks and useful evidence while retiring disposable trial workspaces. Use the installed hill-climb skill’s `native experiment` handoff action to
transfer a promoted private champion to an owned SDLC worktree. It checks the
staged tree against the evaluated tree before normal review and delivery.
