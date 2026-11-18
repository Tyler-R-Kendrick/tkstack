# Profile-guided binary size experiments

When a shipped native binary's size is in scope, identify the actual artifact,
target architecture, release mode, toolchain and build configuration. Measure
its deployed bytes and, where relevant, compressed bytes separately. Keep the
same measurement and correctness, runtime performance, startup, memory and
security guardrails across builds. Record reproducibility and build variance;
debug symbols or stripped distributions must be compared consistently.

Use representative training workloads to collect a compiler-supported profile,
then build a profile-guided candidate using the toolchain's documented profile
generation, merging and use options. Profile data must match the relevant code,
target and compiler; detect missing, stale, partial or mismatched profiles and
fail the comparison rather than silently accepting a fallback. Hold independent
workloads out for confirmation. Compare the size-optimized baseline with the
size-optimized PGO candidate, changing one lever at a time; include any other
release settings only as separately measured candidates. PGO may increase or
reduce size and may trade size against speed, so retain it only if the requested
size improvement clears the declared threshold and all guardrails pass. Preserve
profile provenance, commands, artifacts, results and rejected attempts. If the
toolchain lacks suitable PGO support or representative workloads, report that
and use a separately measured size optimization without calling it PGO.
