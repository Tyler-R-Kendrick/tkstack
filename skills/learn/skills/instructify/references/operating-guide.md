# Instructify

Turn a stated expectation into concise, scoped guidance that the intended
agent can actually discover. Apply tkstack's deterministic-first and concurrency
principles when available. Instructions guide residual judgment; enforce
objective invariants in code at their owning boundary.

## 1. Resolve the requested outcome and scope

| Request | Work |
| --- | --- |
| `/instructify <expectation>` or "put this in agent instructions" | Create or update the smallest applicable instruction source |
| A named instruction file or external source | Adapt/update the stated owned target, preserving provenance and applicable license |
| Audit, report, review, or draft only | Inspect precedence/conflicts and return findings or a plan without changing active instructions |
| Remove a specified owned instruction | Remove only that owned section and preserve other guidance |

Inspect current instructions, imports, scoped rules, and canonical source files
before drafting. Use explicit user intent and visible evidence first. Existing
authorization covers the requested local change; do not ask again for the rule
the user just clearly stated. Uncertain extrapolations stay candidates outside
active instructions, not inferred personal policy.

Use only visible conversation, supplied material, relevant repository contracts,
and explicitly scoped learning evidence. Preserve actual corrections through
`learn` when available; do not invent quotes or mine unrelated private history.
Reference evidence rather than copying private conversations into startup text.

Determine whether the instruction belongs to the user, repository, directory,
file pattern, or particular agent role. Do not silently broaden repository
conventions into global preferences. This package's helper writes explicit
**project scopes**; global/home instruction changes require an explicit target
and the actual harness's configuration route.

## 2. Choose the durable layer

| Need | Preferred layer |
| --- | --- |
| Stable context, decision boundary, working convention, or role expectation | `instructify` at the narrowest applicable instruction scope |
| Reusable multi-step procedure | `skillify`; keep a short instruction pointer if needed |
| Reusable executable orchestration | `flowify`; reference its real invocation instead of restating control flow |
| Mechanically detectable rule or invariant | Type/schema, linter, test, CI, native permission, or `hookify` |
| Correction history or uncertain reasoning rule | `learn` evidence/candidate store |
| Temporary fact or single-task checklist | Task context rather than permanent instructions |

For a decision, resolve facts and explicit rules in code first; use a constrained
decision service/model next and an LLM/agent only for the unresolved judgment.
Do not add prose reminders for checks that can be enforced directly, and do
not claim instruction text creates a permission or execution guarantee.

## 3. Write concrete, nonduplicated instructions

For each instruction, specify when it applies, the action it changes, what
evidence verifies the outcome, its boundary/exception, and its actual source.
Prefer explicit tool/command or canonical-file references over restating a
changing source. Use real names and supported APIs; omit unsupported claims
and vague rules such as "follow best practices."

Read surrounding and inherited guidance. Reconcile actual contradictions with
the current request and authority; report a conflict you cannot resolve instead
of silently changing precedence. Update a fitting existing section rather than
making a second contradictory version. Keep unmodified text, frontmatter,
imports, tool/model settings, and other owners' managed sections intact.

When changing a manifest's scope, targets, ID, or source location, plan and
remove its old bindings first, then publish the new manifest and bindings.
The helper has no hidden registry of old destinations; changing only the
manifest must not leave stale guidance active in its previous scope.

Prefer one shared `AGENTS.md` for compatible hosts and a Claude import when
appropriate. Native Cursor or Copilot rules are useful when their particular
scope/loading behavior is needed; don't generate duplicate context everywhere
by default. Read [harness discovery and scope](../references/harnesses.md) before
selecting bindings. For custom agent profiles, preserve the actual host's
required metadata and capabilities; the helper does not rewrite arbitrary
agent-definition schemas or grant permissions.

## 4. Preview and apply safely

The optional helper takes the [manifest contract](../references/manifest.md) and
generates owned sections with source-based ownership and content hashes.
The [example manifest](../examples/manifest.json) is a demonstration, not an
automatically enabled preference. Copy/adapt it into an owned source directory
such as `harnesses/instructions/` here; never write into a plugin cache.

```sh
python3 <instructify-directory>/scripts/instructify.py plan \
  --project /repo --input /repo/harnesses/instructions/expectations.json > /repo/.tkstack/instructify/plan.json
python3 <instructify-directory>/scripts/instructify.py apply \
  --project /repo --plan /repo/.tkstack/instructify/plan.json --dry-run
python3 <instructify-directory>/scripts/instructify.py apply \
  --project /repo --plan /repo/.tkstack/instructify/plan.json
python3 <instructify-directory>/scripts/instructify.py check \
  --project /repo --input /repo/harnesses/instructions/expectations.json
```

Inspect the actual plan/diff before applying it. This is a review step the agent
can perform within the established request, not a mandatory new user approval.
Report/draft-only work stops at the requested read-only artifact. Removal uses
`plan --remove` followed by the same apply path. Rerunning a fresh aligned plan
is a no-op; an old plan is rejected after inputs change.

Plan independent scopes/read-only inspection concurrently when useful. Writes
to one project's instruction files use a single writer with preflight snapshots,
hash checks, and atomic per-file publication. Keep separate branches/worktrees
for independently authored changes. The helper refuses stale/tampered plans,
symlinked targets, foreign ownership, edited managed content, and collisions
with dedicated native rule files. Follow [operational limits](../references/manifest.md)
for external writers, crash recovery, and rollback; do not describe a batch as
a filesystem transaction.

In tkstack, existing installer-owned startup blocks remain controlled by
`scripts/steering_adapter.py`; Cursor's standing rule is sourced in `harnesses/`.
Change those sources for their content, rather than adding a competing generated
section or patching ignored installation outputs. Never edit vendor snapshots.

## 5. Verify discovery, meaning, and delivery

Run structural checks, inspect the rendered native format, and test apply/update/
remove behavior when modifying the helper. Check a positive case, a transfer
case, and a legitimate negative/boundary case against the intended instruction.
These clarify meaning; they do not prove a model complied.

Verify the actual discovery chain and active source, including Codex override
files, Claude imports, directory inheritance, native globs, and host-specific
limits. A correct filename or aligned hash proves neither loading nor behavior.
Use a harmless native smoke test when the host is available and within scope;
otherwise report file-level checks and the remaining runtime uncertainty.
Keep current higher-priority instructions and task scope authoritative.

When distribution is requested, retain the canonical package, refresh catalog/
inventory, install through the repository's normal route, and verify actual
links. Apply `unslop` to the prose when available. An active `sdlc` workflow still
owns BDD/contracts, isolation, evidence, and stacked delivery. Automatic revision
search uses the existing `learn improve`/SkillOpt gate when real cases apply.

Finish with instruction/source paths, exact scope and loading route, what changed,
actual checks, observed activation if tested, and removal/rollback instructions.
Continue any original task after encoding its durable guidance.
