# Native adapters and activation

The bundled adapter supports Claude Code **PreToolUse** and **Stop** command
hooks. `emit --rules <file>` emits a settings fragment with command entries,
absolute quoted interpreter/script/policy paths, and a five-second timeout.
The emitted command uses POSIX shell quoting; Windows/native-shell bindings
need their own verified quoting rather than assuming this fragment is portable.
Only events with enabled rules are registered; a separate registered callback
is not inferred from an example or generated on each model decision.

PreToolUse maps to `before-tool` with the original JSON fields (including
`tool_name` and `tool_input`). No-match returns `{}`; warning returns
`systemMessage`; a block returns `hookSpecificOutput` with `hookEventName`,
`permissionDecision: deny`, and an explanation. Edit and Write have different
input shapes: author conditions against the actual field (`new_string` versus
`content`). No normalization silently substitutes one for another.
`systemMessage` is a user-facing message; do not claim the agent received or
obeyed the warning without an appropriate context channel and actual evidence.

Stop maps to `before-stop`, requires the actual boolean `stop_hook_active`,
and uses a top-level `decision: block`/`reason` response when continuation is
requested. Reentry returns `{}` without blocking again. Do not claim a Stop
reminder proves successful tests or prevents all completion paths.

Protocol decisions use exit 0 with JSON. Runtime errors with a valid
`failure_mode: warn` return a warning at exit 0. A block-mode error or unreadable/
invalid policy emits stderr and exit 2, the blocking-error behavior for these
Claude events. Other nonzero errors/unsupported events must not be mistaken for
a completed verdict. `run --adapter portable` always returns explicit decision
data on valid evaluation; its caller must enforce it.

Settings must be merged at their owned boundary. This package emits a fragment
and does not mutate project/home configuration itself. Within tkstack, standing
hook registration belongs in `scripts/setup_integrations.py` and its existing
ownership-aware install/uninstall path. In another repository, use its native
project configuration and retain exact added entries for safe rollback.

Claude hook configuration/loading behavior is version dependent. Verify the
installed version and reload/restart when required. Rule files are re-read per
invocation once registration is loaded; initial registration is not automatically
active just because a policy exists. Test harmless positive/negative events and
check actual native output when the CLI exists. Offline contract tests are
reported separately from live-host testing.

No bundled native Codex or Cursor adapter is claimed. Their event/input/output
and blocking semantics must be checked before binding the portable engine.
The skill itself is installed in all three harnesses, so it can author a
verified custom adapter using that host's current capabilities when requested.

Literal inspection of a tool command is not a shell parser, permission sandbox,
or complete restriction on file mutation. Another tool can perform a similar
effect. Enforce actual security boundaries in native permissions or the
resource owner; use hooks for the specific observable project policy they test.
