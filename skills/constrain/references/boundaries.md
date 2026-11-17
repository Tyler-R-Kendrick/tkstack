# Interfaces, state, and effects

Parse external data once into a constrained representation; prefer compiler or
static types for impossible states, and retain checks at actual runtime trust
boundaries. Public contracts also include errors, timing, ownership, state
transitions and compatibility. Keep one source for shared policy and expose only
necessary commands.

`boundaries` configures exact Python syntactic checks over declared glob scopes:
forbidden imported module prefixes and direct call spellings. It fails when an
expected scope has no files. This prevents known patterns but is not dataflow,
a sandbox, name-resolution analysis or proof that indirect dynamic effects are
absent. Use language-native types/lints for stronger guarantees and actual
behavioral tests for runtime effects, state ownership, and concurrency.
Dotfiles setup must inspect and initialize the requested workspace, never infer
success from a source-checkout update; verify destination links and state.
