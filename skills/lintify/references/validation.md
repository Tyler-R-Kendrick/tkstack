# Prove the check, then integrate it

Use the native parser/compiler and CLI, not a homemade approximation of its
format. Record engine/version, config, active rule IDs, source selection, and
observed diagnostics/exit codes. A file can be valid without being discovered
or enabled. A zero-file run or ignored fixture must not become a clean result.

Include at least the meaningful cases for this contract:

- A real violating input with the expected rule ID and source location.
- A corrected input that passes for the intended reason.
- A distinct transfer case that exercises the same mechanism in another shape.
- A legitimate exception and unrelated content the rule should leave alone.
- Malformed source/config, unsupported syntax, or missing context as applicable.

Run the bad case before fixing it. Then run the fixed case and relevant existing
checks. Keep actual false-positive/negative observations. Do not hardcode fixture
answers into a rule or recompute expected diagnostics with the detector itself.
For semantic rules, repeat uncached cases against the actual model configuration
and preserve cost/usage evidence; parsing a prompt does not test its judgment.

Prefer a single clearly named CLI/script in the project's existing lint pipeline.
Keep editor/pre-commit convenience separate from the shared CI gate. Preserve
existing config ownership and dependency locks. Do not edit home config or start
a hook, scheduled model job, paid run, or broad autofix incidentally.

Establish the actual exit-code policy. Linters differ: a process error may share
an exit code with findings, and warnings may exit zero. With ESLint, verify the
`--max-warnings` and error distinction when they matter. For other engines inspect
the pinned implementation/help and record real observations. Unexpected exits,
timeouts, parse failures, and empty discovery remain failures/unknowns, not passes.

Autofix is opt-in and needs a semantics-preserving transformation with before/
after, repeated-application, and conflict checks. A semantic prompt does not
justify silently rewriting source. Suppressions need narrow scope and a real
reason; do not baseline away the newly demonstrated violation to make CI green.

Deliver the native rule/config, command, fixtures, actual evidence, and scope.
Use an existing SDLC workload/contract/evidence process when explicitly active.
Linting complements BDD and real contract tests; it does not replace behavior
proof or justify adding an E2E suite.
