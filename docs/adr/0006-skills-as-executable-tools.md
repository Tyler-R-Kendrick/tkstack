# Compile skills into executable tools with explicit inference boundaries

Status: accepted. Date: 2026-10-30.

The user wants skillify to turn skills into deterministic workflow definitions
in each skill's `scripts/` directory. The skill is an intermediary code-mode
prompt, not the main executable. Its main Markdown remains an invocation and
topic/feature/subcommand/parameter index through progressive disclosure.

Implement facts, algorithms, control/data flow, policy gates, retries, ownership,
and completion in executable code. Preserve an existing suitable native engine;
flowify remains the owner of MAF/Rhai DSL authoring. Simple pure workflows can
use ordinary Python; TypeScript workflows use the version-pinned Vercel AI SDK
boundary for residual language, Decisions, or harness calls. The SDK is neither
a deterministic model nor a durable workflow scheduler.

Keep explicit provider/model/API profiles separate from harness configuration.
Use actual native Chat Completions, Responses, and Decisions interfaces; never
silently substitute structured chat for a decision API. Harnesses use official
adapters and explicit model/auth/tool/sandbox settings. Profiles contain
environment-variable references, not credentials, and no implicit provider
fallback or per-request global-provider mutation. Calls share bounded capacity
and native cancellation/deadlines. Final policy gates stay in code.

The packaging tool scaffolds or seeds safe conversions; it does not automatically
transpile arbitrary prose correctly. Preserve source provenance and licenses,
respect preview/audit scope, reject collisions, complete actual behavior, and
verify native I/O and effects before delivery. A no-op or prompt-forwarding
wrapper is not complete. Packaging/type/HTTP-fixture validation is distinct from
semantic equivalence, calibrated decision quality, and live harness execution.

This specializes the deterministic-first and reuse decisions in ADRs 0004/0005.
User preference evidence remains in the shared learn ledger; no second authority
store or edit to immutable vendor sources is introduced.
