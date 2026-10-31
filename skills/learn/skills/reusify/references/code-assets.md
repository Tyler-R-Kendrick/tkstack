# Snippets, modules, libraries, and components

An existing suitable asset wins before a new abstraction. Search both local
code and actual installed dependencies. Read usage, contract, version, tests,
and limits instead of assuming a similar name provides the required behavior.

## Snippets

Use native editor formats for small editable source forms: VS Code/TextMate
snippets, Visual Studio snippets, or the target editor's verified format.
Keep prefix, language/file scope, placeholder semantics, and required imports
explicit. The package contains a native [C# partial-record snippet](../examples/snippets/csharp.code-snippets).
Validate expansion in the actual editor before claiming integration; JSON
syntax and a copied file do not establish loading or placeholder behavior.

An expansion is an independent source copy. Fixes to the snippet do not update
old expansions. If the repeated behavior must stay consistent, use a shared
module or a tracked generator rather than proliferating snippets of business logic.

## Shared code

Design the interface from the three real callers and their legitimate variation.
The shared invariant should have one owner. Keep internal details, error handling,
state lifetimes, and types behind the smallest useful public surface. Parameterize
actual differences; do not replace duplication with many mode flags and branches.

A reusable module can stay in the repository. Create a package/library only
when the actual consumers, versioning, dependency, distribution, or ownership
boundaries need it. Do not publish a registry package incidentally. Preserve
licensing and dependency constraints.

For a UI component, identify stable responsibilities, input/props, events,
state ownership, theme/token integration, accessibility, and supported states.
Do not duplicate a component merely to change copy or spacing, and do not merge
visually similar surfaces that have different behavioral contracts.

Keep shared code safe for concurrent callers. Pure transformations should remain
simple and composable; stateful services need explicit ownership, lifetimes,
capacity, synchronization, and cancellation. A singleton is not a reuse strategy
when it introduces cross-request mutable state.

Migrate all in-scope callers and verify their public behavior. Tests should
exercise the shared interface and a distinct variation, not copy implementation
logic into expected values. Preserve supported compatibility; delete dead copies
when migration is complete. For mechanical migrations, prefer existing native
codemods over another round of model-authored edits.
