# Vercel AI SDK profiles

Prefer the version-pinned Vercel AI SDK boundary in `scripts/ai-runtime/` when
an executable skill needs inference. Deterministic code remains the first tier;
specialized decision models/APIs are the next tier; LLMs and harness agents are
for residual work. Schema validation does not make a probabilistic answer true.

The scaffold copies a standalone runtime into the new skill's `scripts/`.
Its dependency/integrity lock pins `ai` **7.0.158**, OpenAI **4.0.106**, Gateway
**4.0.131**, TypeSafe **3.0.31**, Harness **1.0.169**, Codex harness **1.0.171**,
Claude Code harness **1.0.173**, Vercel sandbox **1.0.169**, and Zod **4.6.7**.
These are actual installed/version-checked APIs. Decisions and harnesses are
experimental and may change even in patch releases; upgrades need native
contract checks against the new package's bundled docs/types/source.

## Configuration

Configuration is data, not an executable workflow DSL. Default `profiles.json`
has no providers or profiles, so deterministic execution requires no API key.
Supply a chosen configuration through the generated CLI's `--config` or
programmatically to `createInference(configuration, services?)`.

```json
{
  "version": 1,
  "maxConcurrency": 4,
  "maxPending": 32,
  "providers": {
    "direct": {"kind": "openai", "apiKeyEnv": "MY_OPENAI_KEY"},
    "gateway": {"kind": "gateway", "apiKeyEnv": "MY_GATEWAY_KEY"},
    "specialized": {"kind": "typesafe", "apiKeyEnv": "MY_TYPESAFE_KEY"}
  },
  "profiles": {
    "chat": {"kind": "language", "provider": "direct", "api": "chat", "modelEnv": "MY_CHAT_MODEL"},
    "responses": {"kind": "language", "provider": "direct", "api": "responses", "modelEnv": "MY_RESPONSES_MODEL"},
    "classify": {"kind": "decision", "provider": "specialized", "modelEnv": "MY_DECISION_MODEL"}
  }
}
```

Provider kinds are `openai`, `gateway`, and `typesafe`. Each has an explicit
credential environment-variable reference and optional native `baseURL`.
Choose a configured `model` literal **or** `modelEnv`, never both. Model IDs
come from the selected deployment/provider, not a hardcoded SDK-wide default.
No secret values belong in a committed profile. Required variables resolve
lazily for the selected call. Unused profiles need no credentials.

Language profiles require `api: chat|responses|gateway`. OpenAI-compatible
providers support the first two; Gateway uses its own model transport. TypeSafe
is a decision provider, not a language transport. Language and decision profiles
can pass native `providerOptions`. Language output defaults to 1024 tokens;
range 1–32768. Retry count defaults to 0 and is explicitly bounded at 2.
Call timeout defaults to 30000 ms, range 1–300000. There is no temperature-zero
claim of determinism. The wrapper never substitutes another configured profile,
model, or transport; a selected provider/Gateway retains its own routing semantics.

```ts
const runtime = createInference(config);
const text = await runtime.language('responses', [
  { role: 'user', content: 'The bounded residual generation request.' },
]);
const decision = await runtime.decide('classify', { observedState }, {
  ready: { type: 'boolean', instructions: 'Does the state satisfy the stated criterion?' },
});
```

`decide` calls native `experimental_decide` with a decision-model instance;
it does not approximate Decisions through Chat Completions or Responses.
OpenAI uses `/decisions`; TypeSafe/Gateway use their native SDK transports.
Only those providers are bundled here. Anthropic/Google structured-output
decision adapters are not silently substituted. Calibrate task-specific
probability/abstention policy before allowing effects; P(true) is not an
independently calibrated confidence claim. Keep the deterministic adoption gate
in workflow code.

## Harness profiles

Harnesses are separate from model providers. Use `kind: harness` with
`harness: codex|claude-code`, a model/modelEnv, explicit `authEnv` mapping,
`permissionMode`, `activeTools`, and an explicit sandbox definition:

```json
{
  "kind": "harness",
  "harness": "claude-code",
  "modelEnv": "MY_CLAUDE_MODEL",
  "authEnv": {"ANTHROPIC_API_KEY": "MY_CLAUDE_KEY"},
  "permissionMode": "allow-reads",
  "activeTools": [],
  "maxSteps": 1,
  "sandbox": {"provider": "vercel", "runtime": "node24", "ports": [4000]}
}
```

`runtime.harness(profileName, prompt, abortSignal?)` creates the official
`HarnessAgent` and selected adapter, provisions the explicitly configured Vercel
sandbox, runs one scoped session, then destroys the session and sandbox in
`finally` blocks. Calls require actual sandbox/account/model access. Native
adapter permission limitations still apply: this Codex adapter currently
requires `allow-all` for native turns. Its profile validator rejects a narrower
permission mode before provisioning. Choose its permissions and active tools
explicitly for the intended sandbox; unsupported controls are not escalated
automatically. The example uses Claude Code's read permission mode.

Recognized auth targets are the adapter's direct-provider variables:
OpenAI/Codex key/base URL/organization/project, or Anthropic key/token/base URL.
Each target maps to a named source variable. The auth record isolates adapter
credential discovery rather than relying on auto/Gateway/subscription fallback.
Vercel sandbox infrastructure uses its normal explicitly configured deployment
credentials. Codex also accepts profile `reasoningEffort` and `webSearch`;
Claude's native max-turn option is tied to `maxSteps`. SDK step limits are not
a universal hard budget for internal harness/model activity. Provider/harness
selection never authorizes effects beyond the original task.

## Concurrency and evidence

One limiter per runtime shares capacity across language, decision, and harness
calls. Active concurrency is 1–16 (default 4); queued capacity is 0–64 (default
32). Overflow fails explicitly. Queued cancellation removes that request; a
released permit transfers to one waiting owner. Deadlines include queue time;
in-flight cancellation is propagated to the native SDK. Bound larger workflow
fan-out and retain results in input order. No per-call mutation of a global
default provider, process environment, or shared output directory is needed.

Run `npm ci`, `npm run check`, and `npm test` in the runtime package, or use
`npm --prefix <scripts-directory> ...` for a generated skill. Native SDK tests
use injected HTTP fixtures: they exercise real SDK request serialization,
response validation, transport selection, cancellation, and capacity handling.
They instantiate official harness adapters without starting a remote session.
These are not paid provider calls, calibrated decision quality, live harness
execution, or a demonstrated reduction in inference cost.

Primary references: [Decisions](https://ai-sdk.dev/docs/ai-sdk-core/decisions),
[Decisions reference](https://ai-sdk.dev/docs/reference/ai-sdk-core/decide),
[harnesses](https://ai-sdk.dev/providers/ai-sdk-harnesses),
[Codex adapter](https://ai-sdk.dev/providers/ai-sdk-harnesses/codex), and
[Claude Code adapter](https://ai-sdk.dev/providers/ai-sdk-harnesses/claude-code).
