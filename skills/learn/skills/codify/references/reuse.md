# Ownership and reuse

Codify owns `scripts/workflow_authoring.py`, `templates/python/`,
`templates/ai-sdk/`, `templates/tool.md.tmpl`, and `scripts/ai-runtime/`.
These assets were extracted from Skillify; Codify does not import Skillify.
The generic compiler/runner is `scripts/codify.py`.
Codify also owns `scripts/command_schema.py`, `scripts/command.schema.json`,
the command templates, dependency recipe, and command-definition reference.
Skillify's generated release and authored packages carry copies of those assets;
edit the canonical sources and regenerate rather than maintaining new parsers.

Skillify retains skill-specific metadata/portable-package checks, progressive
index generation, and preservation of existing skill source. It calls this
engine for workflow generation and artifact compilation. Flowify continues to
own native MAF/Rhai authoring/host validation; Codify can freeze its definitions
and native-host bindings. Reusify can register this library/compiler for other
callers without inventing a second implementation.

The Python interfaces are `authoring.workflow_files(backend, description)`,
`scaffold(source, target, backend)`,
`compile_workflow(source, entrypoint, cases, ...)`, `check(artifact)`, and
`invoke(lock, payload, project, ...)`. Prefer CLI argument arrays across process
boundaries; the native code modules are also importable. `check` supplies a
validated current lock to the runner; `invoke` is a lower-level trusted helper.
`invoke` accepts either a configuration Path or an already projected configuration
object, plus an optional independent child environment. Both use the same profile
declaration checks and native SDK boundary. The dotfiles `.tkstack/tkstack` runner
uses these interfaces and the shared `command_schema.bound_lock` check rather
than implementing another executor, signature format, or inference configuration.

For portable independent installation, Skillify carries a generated release
copy at `scripts/codify_runtime/`, including only compiler/template/runtime code
and license. It is not a separately maintained implementation. In this source
repository `python3 scripts/sync_codify.py` publishes the release;
`python3 scripts/sync_codify.py --check` and doctor reject drift. Edit canonical
Codify source first. The generated copy never imports the original repository
or assumes a sibling skill, plugin cache path, network, or home directory.

The tkstack state primitive remains repository-owned with identical per-skill
copies. Retain MIT notices and the pinned AI SDK package lock when distributing
this engine. Authored package contracts and native test evidence remain required.
