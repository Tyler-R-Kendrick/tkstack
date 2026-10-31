# Native macros

Choose a macro when the host's syntax-level expansion fits the abstraction.
Prefer an ordinary function, generic, module, or constexpr-style construct when
it preserves the same semantics with a simpler interface. Macros are canonical
code assets, not instructions for an LLM to fill in.

Inspect repeated forms and specify accepted syntax/arguments, expansion, name
binding/hygiene, evaluation order, diagnostics, language/toolchain versions,
and ownership. Reuse the language's actual tooling; avoid a compiler plugin
when a small ordinary helper would remove the duplication.

For C/C++ preprocessor macros, inspect precedence, statement/expression context,
multiple argument evaluation, side effects, scope, and name collisions.
For Rust declarative/procedural macros, check hygiene, generics/where clauses,
path resolution, diagnostics, crate boundaries, and the supported toolchain.
Build-time procedural execution has a different contract from simple syntax
expansion; keep that dependency explicit.

Compile and consume expansions in the real native host. Include original uses,
a distinct variation, and malformed/boundary syntax. Expansion inspection is
weaker than compilation and runtime/contract proof. Keep output identifiers and
cache keys deterministic; isolate mutable output for parallel builds.

Register a `macro` asset with its source, guide, import/invocation, supported
syntax/toolchain, and proof. Missing native tooling is an explicit limit.
Installing this skill does not compile a macro or establish compiler evidence.
