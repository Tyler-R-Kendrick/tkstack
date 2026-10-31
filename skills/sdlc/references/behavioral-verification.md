# Verify behavior at meaningful seams

Start with the requirement and the public behavior or real contract being
proved. Reuse a runner that exercises that path. Preserve the intended red,
implement the smallest green, then refactor under the meaningful checks.
The user's BDD/contract strategy remains the acceptance policy.

Expected values come from a worked example, requirement, independently known
result, or reference implementation. Do not reimplement the production algorithm
inside an assertion, snapshot whatever happens to be produced, or check private
call ordering that has no public obligation. A passing test that cannot detect
the stated failure is not useful evidence.

Use the highest useful local seam that exercises the actual mechanism. An
integration test against an internal fake does not establish a real provider's
contract. Run both consumer and provider against the same pinned contract and
version matrix; name the boundaries a fixture does not cover.

For screenshots, match viewport, data, theme, state, and revision. Inspect the
images themselves. For a CLI/TUI, use the real terminal interface when terminal
behavior is the requirement. Capture HARs, traces, or recordings only when they
prove a relevant obligation; redact secrets and identify capture commands.
These captures complement BDD/contracts and do not require an E2E suite.

Distinguish a launcher failure, missing dependency, empty capture, skipped path,
or stale artifact from product failure or success. Re-read generated deliverables
and compare exact formats when the requirement makes those formats meaningful.

Use verified, contradicted, or inconclusive findings with their exact scope.
Compilation proves compilation. Mock-host validation proves that host's simulated
contract. Neither proves deployment, UI quality, model improvement, or a complete
workflow. Keep semantic inspection separate from mechanical receipt checks.
