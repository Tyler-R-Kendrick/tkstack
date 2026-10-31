# Primary sources and backend choice

Reviewed 2026-10-30. The exact checked source revisions are:

- **Microsoft Agent Framework:** `4d4e2168fe57ee20903e152928a61cf276372d29`.
  [Declarative package](https://github.com/microsoft/agent-framework/tree/4d4e2168fe57ee20903e152928a61cf276372d29/python/packages/declarative),
  [WorkflowFactory](https://github.com/microsoft/agent-framework/blob/4d4e2168fe57ee20903e152928a61cf276372d29/python/packages/declarative/agent_framework_declarative/_workflows/_factory.py),
  [tool executors](https://github.com/microsoft/agent-framework/blob/4d4e2168fe57ee20903e152928a61cf276372d29/python/packages/declarative/agent_framework_declarative/_workflows/_executors_tools.py),
  [declarative builder](https://github.com/microsoft/agent-framework/blob/4d4e2168fe57ee20903e152928a61cf276372d29/python/packages/declarative/agent_framework_declarative/_workflows/_declarative_builder.py).
  The package source reports version 1.4.1 and documents actual tool registration,
  YAML loading, graph construction, native dependencies, and stable workflow APIs.
- **Grok Build:** `2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8`.
  [xai-workflow manifest](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-workflow/Cargo.toml),
  [engine](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-workflow/src/engine.rs),
  [host requests](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-workflow/src/host.rs),
  [metadata](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-workflow/src/meta.rs),
  [native validator](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-workflow/src/validate.rs),
  [validator example](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-workflow/examples/validate.rs),
  and the [workspace Rhai dependency](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/Cargo.toml).
  The engine is **Rhai**, version family 1.25, with Grok-specific host calls and
  a journal. This directly identifies the Rust library mentioned by the user.
- Microsoft's [declarative overview](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/declarative-workflows),
  [advanced patterns](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/declarative-workflows/advanced-patterns),
  and [superstep execution model](https://learn.microsoft.com/en-us/agent-framework/concepts/workflows/builder-and-execution).
  Examples/documentation can trail current package APIs, so generated hosts use
  the checked source's direct `agent_framework_declarative` public export and
  `register_tool` for `InvokeFunctionTool`.

MAF YAML is the default because it can express tool/code actions without forcing
an agent runtime into deterministic work. Rhai is appropriate when Grok's actual
host is desired; a generic interpreter does not reproduce its host API. Existing
project engines remain valid when they fit better. The skill does not translate
between these formats with an invented intermediate workflow language.

PyPI's [published package metadata](https://pypi.org/pypi/agent-framework-declarative/json)
was checked separately: 1.4.0 is available, while the source tree's 1.4.1 is
not published. Generated requirements use the available 1.4.0 release rather
than an unsatisfiable source-version pin. Native verification must use the
installed package's actual API and report that runtime version.

The source files informed independently written scaffolds and helpers; no
upstream code snapshot was added or modified. The MAF scaffold includes direct
published-version requirements and a generated hash lock for CPython 3.12/Linux;
other target profiles need their own lock and verification.

MAF 1.4.0 was installed into an isolated ignored validation environment, along
with a local .NET 8.0.33 runtime verified against Microsoft's
[8.0 release metadata](https://builds.dotnet.microsoft.com/dotnet/release-metadata/8.0/releases.json).
Native graph construction and actual model-free positive/transfer/failure runs
were performed there. Their receipts are separate from binding unit tests.
Rust/Cargo and Grok remain unavailable here, so native Rhai compilation and
Grok-host execution are not claimed.
