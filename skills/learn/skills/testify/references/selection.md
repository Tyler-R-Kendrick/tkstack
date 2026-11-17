# Choose and verify the test

1. State a concrete realistic regression, affected contract, independent
   observation, and why retained checks do not already catch it. Inspect code
   and existing test layers. Keep the existing test when it covers the same
   fault; add a case to it rather than another file where practical.
2. At external boundaries, parse untrusted values into constrained representations
   once. Prefer a type, exhaustive match, compiler, schema or native static
   rule when it makes the invalid state unrepresentable. Static types do not
   parse runtime JSON or establish behavior of a database, network or process.
3. Select the cheapest level that exercises the actual contract: pure unit for
   distinct core logic; contract plus simulated timeouts/malformed and partial
   dependency failures at integration boundaries; a small functional flow for
   cross-boundary behavior. Use property/fuzzing for broad inputs and independent
   invariants, not random examples against the same implementation. Use Lean for
   qualifying core/high-risk security invariants and TLA+ for consequential
   interleavings, with explicit assumptions and implementation correspondence.
   Live E2E and performance tests need a distinct risk, realistic workload,
   budget and a reason simulation cannot cover it.
4. Assert externally meaningful values/effects, rejection and recovery. Prefer
   real local implementations, temporary files, deterministic clocks and fakes
   only at actual dependency boundaries. Avoid tests of source spelling, mocks'
   call choreography, incidental formatting, and hand-picked coverage targets.
5. Run the native test in its intended environment. In an isolated copy, inject
   a plausible fault and show the retained test fails; restore and show it passes.
   Run relevant surrounding checks. Document unknowns and update the repository's
   constraint review record only after inspecting the changed suite.

Testify's deterministic generator only supports Python subprocess CLI contracts.
Its typed case schema and success exit do not establish an independent oracle,
verify semantic value, or safely execute arbitrary untrusted code. Other kinds
need actual project tools and observable native evidence, not relabeling.
