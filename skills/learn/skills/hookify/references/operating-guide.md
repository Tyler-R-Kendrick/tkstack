# Hookify

Replace a repeated instruction with a reliable mechanism at the right boundary.
Use explicit predicates and deterministic command hooks before considering a
decision service or model. The [source notes](../references/sources.md) identify
Anthropic's hookify/plugin-development tools and the Pstack structural-enforcement
principles that informed this independent implementation.

## 1. Identify the actual rule and its owner

Use the user's stated rule, visible corrections, and relevant actual artifacts.
If no rule was supplied, inspect only available conversation/learning evidence
and propose candidates. Do not silently activate a guessed prohibition or mine
unrelated transcript databases. Capture actual feedback through `learn` when
available; tool observations and inferred intent are not user authority.

Determine the desired observable behavior, scope, event, input fields, exact
predicate, warn/block effect, legitimate exceptions, and failure behavior.
Use an explicitly stated action. For unspecified action, default to a warning
and state that choice; don't escalate a preference into a new blocking policy.
Resolve genuine ambiguity while continuing independent work. Existing task
authorization covers implementing the concrete requested local rule.

## 2. Choose the strongest appropriate boundary

Standing context or expectations that genuinely need judgment belong in
`instructify` when available; reusable procedures belong in `skillify`.
Use a hook for the concrete event/predicate it can actually enforce.
A requested multi-step executable procedure belongs in `flowify` when available;
a hook can invoke its authorized deterministic entry point rather than interpret
the procedure or launch an agent by default.

Prefer a type/schema, linter, test, CI check, or native permission rule when it
can establish the invariant directly. A tool hook is appropriate for the event
it can actually observe. A pre-tool deny can prevent that tool operation;
a post-tool observation cannot undo an already completed side effect.

Use `lintify` when available to author a CLI source/artifact lint rule. Reuse
its validated native command from a requested hook instead of duplicating it.

Split objective checks from residual semantic judgment. Use a narrow decision
model/API only when the remaining decision cannot adequately be expressed in
code, then an LLM/agent as the last resort. Such integrations need their own
validated contract, budget/timeout, abstention behavior, and tests. The bundled
runtime is **code only** and never calls a model, executes payload commands,
reads transcripts, or follows event-supplied file paths.

Do not use “the transcript says tests passed” as a completion gate. Verify actual
command/evidence state bound to the current artifact through the owning workflow.
The bundled Stop adapter prevents reentry loops; it is not a universal proof of
completion. A mandatory invariant may belong in CI rather than a stop reminder.

## 3. Write the portable policy and fixtures

Read [the policy contract](../references/policy.md). Store owned policies in the
project's established source/config directory, such as `harnesses/hooks/` in
this dotfiles repository, or `.agents/hookify/` in another project. Never write
user rules into a skill/plugin cache. Preserve an existing policy's scope and
baseline, and publish complete JSON atomically so concurrent hooks cannot read
a half-written file.

Use exact fields and literal operators. All conditions in a rule are ANDed;
use separate explicitly scoped rules for alternatives. A missing field does not
accidentally satisfy a negative condition. Unknown operators/configuration fail
validation. Stable rule IDs determine output order, block wins over warn, and
disabled rules stay visible without affecting execution.

Include a positive reproduction, a real negative/exception case, an unrelated
tool/event, missing-field behavior, and repeatability cases. These are fixed
contract fixtures, not generated expected values copied from current output.
For input with semantic structure, use an actual parser/custom deterministic
check rather than claiming substring matching understands it.

```sh
python3 <hookify-directory>/scripts/hookify.py check --rules /repo/harnesses/hooks/policy.json
python3 <hookify-directory>/scripts/hookify.py replay \
  --rules /repo/harnesses/hooks/policy.json --cases /repo/harnesses/hooks/cases.json --jobs 4
```

The bundled [example policy](../examples/policy.json) and [cases](../examples/cases.json)
are runnable demonstrations, not automatically enabled personal rules.

## 4. Bind to the actual harness

Read [native adapter behavior](../references/adapters.md) before registration.
The bundled emitter produces a Claude Code settings fragment for enabled
PreToolUse/Stop command hooks:

```sh
python3 <hookify-directory>/scripts/hookify.py emit --rules /repo/harnesses/hooks/policy.json
```

Merge the reviewed entries into the requested project scope, preserving unrelated
hooks/settings and exact ownership of entries you add. Compare current bytes
with the inspected baseline before writing; serialize this shared configuration
update or use a transaction/lock. Do not replace the whole settings file with
the fragment. In this dotfiles repository, integrate standing registrations
through the canonical `scripts/setup_integrations.py` configuration path rather
than editing ignored installed settings as their source of truth.

For an update/remove request, remove only the exact owned entries/policy targeted
by the request. Preserve user edits and foreign registrations. Emit is read-only;
it does not activate or merge anything by itself. Creating this skill does not
enable the example policy.

Other harnesses can reuse the portable evaluator, but field names, hook events,
block semantics, lifecycle, and settings formats require a verified adapter.
Do not paste Claude JSON into Codex/Cursor or claim a registered warning blocks
an operation. Inspect the installed host/version and real documentation. If
native binding cannot be validated, deliver the portable policy, replay evidence,
and precise remaining binding work without claiming activation.

## 5. Verify behavior and report

Replay independently scoped fixtures with bounded concurrency and deterministic
result order. Runtime evaluations read immutable policy/event data and have no
shared write state. Keep dependent side effects or ordered gates within one
deterministic check; native hook callback order is not a sequencing guarantee.
Test malformed input/configuration, duplicates, no-match, warn/block precedence,
disabled rules, and Stop reentry where applicable. Inspect actual native JSON and
exit status. Diagnostics belong on stderr, not mixed with protocol JSON.

Validate native behavior with a harmless allowed/denied operation when the host
is available and within scope. New registrations may require a reload/restart;
rule edits are reread on the next invocation only after a working registration
exists. Never repeat an upstream “active immediately” claim without that context.
Report replayed, configured, and observed activation separately.

Finish with the mechanism chosen, policy/config paths, events/action and scope,
positive/negative results, actual activation state, and rollback instructions.
Keep hook changes reviewable and incremental; honor an explicitly active `sdlc`
workflow. Continue the original task after encoding its structural correction.
