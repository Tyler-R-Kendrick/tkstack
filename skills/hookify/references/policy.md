# Deterministic policy contract

Policy JSON has exactly `version: 1`, explicit `failure_mode: block|warn`, and
`rules`. Up to 128 rules are supported; each has exactly these fields:

```json
{
  "id": "warn-debug-write",
  "event": "before-tool",
  "enabled": true,
  "action": "warn",
  "conditions": [
    {"field": "tool_name", "operator": "equals", "value": "Write"},
    {"field": "tool_input.file_path", "operator": "ends_with", "value": ".ts"},
    {"field": "tool_input.content", "operator": "contains", "value": "console.log("}
  ],
  "message": "Check whether this debug log belongs in the shipped source."
}
```

This is a demonstration, not a universal ban on logging. Keep the user's real
exceptions and desired severity in the authored policy. IDs are unique
kebab-case. Events are `before-tool` and `before-stop`. Rules have 1–16 AND
conditions; messages are static policy text, not executable instructions.

Operators: `equals` (typed scalar equality), `one_of` (typed scalar alternatives),
`contains`, `starts_with`, `ends_with` (case-sensitive string literals), and
`exists` (boolean indicating field presence). `null` is a present scalar;
missing is different. `true` is not equal to `1`. Dot-separated object fields
are supported; array traversal and arbitrary code/regular expressions are not.
Use a custom parsed check when literals do not express the actual invariant.

Portable input is:

```json
{"event":"before-tool","fields":{"tool_name":"Write","tool_input":{"file_path":"src/app.ts","content":"console.log(value)"}}}
```

`run --adapter portable` consumes JSON on stdin and returns `decision`
(`allow|warn|block`), sorted matched IDs, policy messages, and reason codes.
Evaluations have no writes, model calls, subprocesses, or transcript reads.
A `block` result is data for a caller to enforce, not an automatic side effect.
Do not use the portable process's successful exit alone as an allow decision.

For `before-stop`, `fields.stop_hook_active: true` returns an explicit
`stop-reentry` allow result to prevent a hook-induced infinite continuation
loop. This means Stop rules are reminders/continuation gates, not immutable CI
enforcement. Verify actual completion in the owning deterministic workflow.

Both policy and event input are limited to 1 MiB. Invalid policy/operator/event
is an error, not a silently nonmatching rule. Runtime native failure handling
uses the explicit valid policy's mode; an unreadable/invalid policy cannot
reliably supply that mode and fails closed in the Claude adapter. Keep paths
and messages free of secrets. The runtime returns static explanations and IDs,
not entire event payloads.
Duplicate JSON object keys and non-finite numeric constants are rejected rather
than letting a parser silently choose a different policy value.

## Replay fixtures

A cases file is a JSON array of 1–128 objects:

```json
[{
  "id": "debug-write-warning",
  "input": {"event":"before-tool","fields":{"tool_name":"Write","tool_input":{"file_path":"src/app.ts","content":"console.log(value)"}}},
  "expected": {"decision":"warn","matches":["warn-debug-write"]}
}]
```

Use explicit expected decisions and exact sorted IDs derived from the desired
contract. `replay --jobs 4` uses bounded workers, read-only policy data, and a
stable case-ID output order. Exit 0 means all cases match; 2 means a contract
mismatch; 1 means invalid inputs. Results establish predicate/adapter behavior,
not that a model obeyed a warning or that a native registration was loaded.

Atomic publication prevents readers observing partial JSON; it does not resolve
competing policy authors. Keep one owner or use version/CAS/locking when several
writers must edit the same policy. Independent policy generation can happen in
separate files and merge at the owned publication boundary.
