---
name: sdlc
description: Run the BDD/contract lifecycle or scoped planning, architecture, verification, review, delivery, and handoff. Coordinate durable SQLite task DAGs with fenced leases and explicit development-to-requirements/ADR revisions. Full mode retains sparse COW worktrees, independent evidence review, and squash-merged stacked PRs.
disable-model-invocation: true
license: MIT
compatibility: "Python 3.11+ with SQLite and Git for deterministic task coordination. Typed commands use the shared installed Codify command runtime. Full lifecycle requires actual delegation/PR capabilities and a reflink-capable filesystem for strict COW. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.5.0"
---

# SDLC

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills sdlc -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Own the requirements-to-delivery outer loop and each worker's inner red/green
loop. Choose only the requested mode; installing this skill does not run it.

Invoke `.tkstack/tkstack skills sdlc -- help` for read-only command discovery.
Skillify supplies reserved default help and version: use `help --format man`
for generated man(1) source, or `version` for the package version.
Task coordination executes frozen code in `scripts/workflow.lock.json` without
inference. The full engineering lifecycle still needs the actual agents,
judgment, evidence, and authorized delivery described below.

| Request | Read before acting |
| --- | --- |
| Run durable task commands, recover workers, or revise requirements/ADRs | [Coordination and parameters](references/durable-task-graph.md) |
| Full implementation lifecycle | [Complete operating guide](references/operating-guide.md) |
| Plan or decompose only | [Requirements and planning](references/requirements-and-planning.md) |
| Architecture or refactor | [Interfaces and refactoring](references/architecture-and-refactoring.md) |
| Test or verify behavior | [Behavioral verification](references/behavioral-verification.md) |
| Review only | [Review findings](references/review-findings.md) |
| Deliver, modernize, babysit, or hand off | [Delivery and handoff](references/delivery-and-handoff.md) |

| Deterministic subcommand | Tool/flag definition |
| --- | --- |
| Default/help | [help](commands/help.md) |
| Declared package version | [version](commands/version.md) |
| Register initial workload and graph | [tasks init](commands/init.md) |
| Inspect graph, owners, issues, expiry | [tasks status](commands/status.md) |
| Lease ready work | [tasks claim](commands/claim.md) |
| Renew ownership | [tasks heartbeat](commands/heartbeat.md) |
| Submit proof or release stopped work | [tasks finish](commands/finish.md) |
| Acknowledge stopped writes | [tasks quiesce](commands/quiesce.md) |
| Coordinator recovery | [tasks recover](commands/recover.md) |
| Development finding → outer loop | [tasks issue](commands/issue.md) |
| Apply authorized workload/ADR revision | [tasks revise](commands/revise.md) |
| Original workload, amendments, events | [tasks history](commands/history.md) |
| Current task proof readiness | [tasks gate](commands/gate.md) |

Full mode requires the operating guide before implementation: freeze original
and branch workloads; build atomic leased DAGs; provision isolated sparse COW
worktrees with shared-safe caches; run bounded implementation/review/mitigation
workers; collect BDD and real contract evidence; reconcile exact-head artifacts
against the initial workload; deliver incremental commits and stacked PRs.
Use the existing deterministic helper, templates, and gates. Unsupported strict
COW or missing delegation is a real blocker unless the task permits a fallback.
Persist graph coordination in scoped `.tkstack/sdlc/`, outside temporary
sessions. Unexpected requirement, architecture, or cross-owner contract findings
pause affected branches and return to the outer loop. Preserve the original
workload; apply authorized amendments and ADR decisions before resuming.

Plan, review, and handoff modes do not dispatch the full swarm or publish PRs.
The requested effect boundary and existing authorization govern delivery.
Babysit authorized PRs, address every concern, keep CI green, and squash stacks
root first only within that boundary. Do not weaken checks or fabricate review
independence. Sources, preserved policies, and adaptations are in
[the distillation notes](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).
