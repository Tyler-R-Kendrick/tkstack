# Compile prompts into executable artifacts

`codify` owns prompt/Markdown-to-workflow compilation and the reusable engine
extracted from Skillify. An agent resolves meaning once into actual native code;
the deterministic compiler verifies that implementation and freezes it into
`*.lock.json`. Subsequent runs execute the frozen code rather than reinterpreting
Markdown. A generated lock alone cannot make arbitrary natural language
unambiguous or eliminate required semantic inference.

```sh
python3 skills/learn/skills/codify/scripts/codify.py scaffold /repo/procedure.md --target /repo/workflow
# Implement scripts/workflow.py and author actual contract cases.
python3 skills/learn/skills/codify/scripts/codify.py compile /repo/workflow/PROMPT.md \
  --entrypoint /repo/workflow/scripts/run.py --cases /repo/workflow/cases.json \
  --output /repo/workflow/scripts/workflow.lock.json
python3 skills/learn/skills/codify/scripts/codify.py run /repo/workflow/scripts/workflow.lock.json --input input.json
```

The executable lock contains exact code/resource bytes, hashes, source/case
provenance, a native entrypoint, declared inference profiles, and contract-check
results. It is an authored deliverable that can be versioned with its source.
Private staging and publication locks stay inside `.tkstack/` and are ignored.
`check` and `compile --dry-run` remain read-only. The runner rejects stale inputs;
it never silently compiles, forwards the Markdown to a model, or substitutes a
provider. The complete source tree remains necessary for freshness checks.

Compilation requires positive and rejection cases; deterministic successes run
twice. Verification uses bounded parallel workers with isolated working copies.
A failed build preserves the previous lock. Concurrent publication uses one
cooperative writer per artifact, with stale-source/output checks. Runtime
execution materializes the frozen code in a private directory, invokes the native
interpreter, enforces a deadline, and cleans up on ordinary exit/failure.
Case checks are evidence, not semantic equivalence proofs. This is trusted code
execution with normal process authority, not a sandbox or hermetic build system.

Skillify retains skill packaging, progressive disclosure, metadata validation,
and original skill-source preservation. Its `compile` command invokes Codify's
engine to produce `scripts/workflow.lock.json`. A generated release copy keeps
standalone Skillify installations usable without sibling plugins:

Markdown-defined nullable string CLI flags accept ordinary paths/text, explicit
`null`, or a JSON-quoted string; other non-string parameters use JSON syntax.
See [the shared command contract](../skills/learn/skills/codify/references/command-definitions.md).

```sh
python3 scripts/sync_codify.py
python3 scripts/sync_codify.py --check
python3 skills/learn/skills/skillify/scripts/skillify.py compile /repo/skills/my-tool --cases /repo/skills/my-tool/cases.json
```

Doctor checks that release against canonical Codify source. There is no reverse
Codify-to-Skillify dependency. Flowify still owns MAF/Rhai authoring/native host
validation; its definitions and actual host bindings can be included in a lock.
The version-pinned Vercel AI SDK runtime now lives at
`skills/learn/skills/codify/scripts/ai-runtime/`. Providers/models, chat/Responses, native
Decisions, and harness definitions remain explicit and configurable. Pure
Python runs need no model or dependency installation. Node runs use explicitly
supplied installed dependencies from `npm ci` against the frozen package lock;
execution never downloads them. No-inference mode is a reviewed declaration,
not a universal static/network isolation guarantee.

The complete [normalization example](../skills/learn/skills/codify/examples/normalize-labels/PROMPT.md)
has seven contract cases and a built
[lock artifact](../skills/learn/skills/codify/examples/normalize-labels/scripts/workflow.lock.json).
Its transfer/boundary cases include Unicode, empty input, wrong types, missing
fields, and extra fields. More complex conversions need their own domain cases
and real output/effect review.

See [the skill index](../skills/learn/skills/codify/SKILL.md),
[tool interface](../skills/learn/skills/codify/references/commands.md),
[artifact contract](../skills/learn/skills/codify/references/artifact.md), and
[primary-source comparison](../skills/learn/skills/codify/references/sources.md).

## Commands from Markdown tool signatures

Codify owns the shared schema, safe YAML reader, parameter validation, API
export, and CLI/tool-call dispatch used by Skillify. Each `commands/*.md` contains
a strict OpenAI Responses function tool plus separate local CLI/artifact bindings.
Chat exports use the native nested function envelope. JSON Schema is preserved;
aliases and flags never leak into API tool definitions.

```sh
python3 scripts/tool.py codify commands skills/learn/skills/codify/examples/normalize-labels --format responses
python3 scripts/tool.py codify invoke skills/learn/skills/codify/examples/normalize-labels -- labels normalize -l '[" b ","a","a"]'
python3 scripts/tool.py codify invoke skills/learn/skills/codify/examples/normalize-labels --call /path/to/tool-call.json
```

The real example returns `{"labels":["a","b"]}`. The same lock accepts Responses,
Chat, and direct function-call input through `--call`. Signatures are snapshotted
into the artifact automatically; edits require explicit recompilation. Default
help and exports are read-only and work before compilation. The profile validates
typed arguments before effects, refuses unsafe bindings and unsupported schema
features, and executes no shell text or implicit inference. See
[the full format, supported schema profile, and dependency setup](../skills/learn/skills/codify/references/command-definitions.md).

Skillify supplies reserved help/version definitions from this runtime. Help is
the default subcommand and generates a man-page model with deterministic console
rendering; `help --format man` emits escaped man(1) source. Version reads declared
package metadata without running code. Both CLI and API work before compilation;
older command packages receive missing defaults when their catalog is read.
The legacy topic-only help tool remains supported. See
[reserved commands and output contracts](../skills/learn/skills/codify/references/command-definitions.md#reserved-help-and-version).

## Shared normalized skill runtime

Codify owns `package_runtime.py` and `json_contract.py`, reused by Skillify's
normalizer and all 19 owned skill cores. The compiler, command protocol and
contract runtime share strict duplicate/non-finite JSON handling. Native helper
bindings preserve typed input validation, actual stdout/exit behavior, scoped
paths and existing model/provider configuration. Their effects remain those
of the explicitly selected helper/code, not an implicit inference fallback.

Self-hosted packages can include draft templates as resources; unresolved
adjacent executable workflows still cannot compile. Snapshots track executable
status in a Git-portable way, so private checkout umasks do not invalidate
identical source. [Normalization](normalization.md) distinguishes mechanical
coverage, real policy evaluations and remaining semantic/native execution work.
