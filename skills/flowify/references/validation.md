# Validation levels and execution evidence

The helper separates source inspection from native checks. Both require an
explicit backend and file; neither discovers private workflows or starts a
model automatically.

| Operation | Evidence | What remains |
| --- | --- | --- |
| `scaffold` | Owned native sources and invocation files created without overwriting a directory | Actual requested logic, dependency lock, native validation, real cases |
| `inspect --backend maf` | Hash, safe YAML parsing, duplicate-key/cycle rejection, explicit action IDs and basic nested action structure | Full native schema/expressions, bindings, graph semantics and execution |
| `inspect --backend rhai` | UTF-8 source and hash only | Rhai syntax, metadata, host integration and execution |
| `check --backend maf` | The real installed MAF factory built the graph from the recorded source snapshot | Project binding readiness, actual inputs, failure/effect behavior and outcomes |
| `check --backend rhai --grok-source <checkout>` | Real Rust/Grok validator result with a validator-source hash | Real input/effect/agent behavior; the upstream validator uses a stub host |

The YAML inspection profile is deliberately limited. It accepts the documented
top-level or trigger action forms and walks common nested action lists. It does
not certify every current/future MAF action schema, expression, tool binding,
agent configuration, or reference. Unsupported profile constructs need direct
native validation rather than rewriting their semantics to appease this checker.
Aliases/cycles and non-JSON YAML scalar types are excluded from this profile.
Scaffolds retain this package's MIT license with its independently written
template code. Preserve applicable additional licenses when adapting other sources.

Exit codes: **0** means the requested operation succeeded at its stated level;
**1** means invalid input or a load/compile/timeout error; **2** means the native
Rhai validator returned failure; **3** means a required direct runtime/source
is unavailable. `native_validated` and `executed` are explicit result fields.
Source inspection never sets them true. Native graph/mock-host validation does
not set `executed` true for production execution. Missing runtime is not a pass.

Native checks can import/compile/instantiate trusted project code and its runtime;
they are not passive sandboxing. Rhai checking uses this actual command:

```sh
cargo run --offline --locked --manifest-path /path/to/grok-build/Cargo.toml \
  -p xai-workflow --example validate < workflow.rhai
```

The helper requires explicit Grok source, cached dependencies, and Cargo; it
never fetches a checkout or dependencies during this command. Compilation and
validation are capped at 60 seconds. Use an appropriate native validation host
for larger builds rather than assuming the helper can provision one.

Upstream `examples/validate.rs` calls `validate_script(script, None)`, which
uses default probe arguments. Its host returns stub successful agent results,
template content and budget responses. It can accept a pause as a valid outcome.
Therefore a passing native probe is not completion on the workflow's actual
inputs. Use the native API with explicit arguments or the real host for those
tests, and preserve their actual receipts.

## Meaningful local and native cases

For a generated workflow, test required behavior at public seams:

- A positive request and distinct transfer input produce independently specified
  artifacts/values, not copied current output.
- Missing/invalid inputs, failed tool results, absent evidence and unknown
  decisions prevent dependent effects or success claims.
- Independent operations overlap within the configured limit and produce stable
  results even when completion order changes. Use events/barriers for the test.
- Cancellation, retry, partial failure, restart, or replay obey the exact promised
  contract. Do not infer exactly-once effects from a journal or a success flag.

The starter's Python binding uses streaming file hashes, a bounded semaphore,
thread-backed reads and stable `gather` order. Paths resolve within an explicit
project, aliases to the same canonical input are rejected, and child reads are
joined before returning failure/cancellation. Input bytes must remain stable;
this is not a filesystem snapshot. Its tests establish those binding mechanics
without claiming that MAF ran. Native runtime checks are recorded separately.

Retain definition hash, effective runtime/version and dependency lock, input
identity, invoked commands/bindings, errors and retries, outputs, and appropriate
artifacts. For UI/media, include actual renders/recordings where they matter.
Do not use a mock binding, an LLM attestation, or JSON shape alone as execution
evidence. Keep secret values out of committed definitions and public logs.
