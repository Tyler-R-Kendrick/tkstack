# Inspect and refine the actual surface

Build around the important user action and information hierarchy. Use restrained
and consistent spacing/type scales, readable measure, clear navigation, and
content-driven layout. Novelty should support the brief; avoid adding eyebrows,
badges, cards, gradients, or decoration just to fill space.

Preserve accessible semantics, keyboard order, visible focus, usable labels,
contrast, target sizes, and motion preferences. Cover loading, empty, error,
long-content, localization, and narrow/wide layouts as relevant to the workload.
Use project tokens/components before introducing a second design vocabulary.

Inspect the rendered result in batches at the sizes and states that matter.
Fix what one inspection reveals before taking another capture. Record matched
before/after conditions for a refinement; a redesign is judged against its new
brief rather than requiring accidental pixel parity with the rejected look.

Use scoped browser/terminal/native inspection available in the harness. Do not
assume a named CDP tool, hardcoded port, or unavailable proprietary renderer.
BDD/contracts remain the behavioral acceptance strategy when SDLC is active;
screenshots support visual acceptance without imposing E2E tests.

Return the artifact or actual preview link, observed checks, and concrete
remaining limits. Apply current `unslop` criteria when available; those criteria
do not authorize erasing a legitimate design choice or accessible status cue.
