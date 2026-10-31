# Put enforcement where the fact is known

Start from an explicit invariant and actual execution boundary. Prefer a type,
parser, linter, repository check, or native permission when it sees the whole
fact more reliably than a command hook. A pre-commit hook is convenience; CI
is the shared gate when bypass prevention is part of the requirement.

For a native CLI file/artifact detector, use `lintify` when available. A command
hook can invoke the established lint entrypoint at its supported event boundary.

For Git protection, distinguish read-only commands, ordinary writes, rewrites,
deletion, and publication. Parse the real command structure where feasible;
aliases, shell operators, quoted strings, and wrappers defeat naive substring
tests. If the policy engine cannot express the invariant, use a proper boundary
or report the limitation. Do not represent literal matching as a shell sandbox.

Preserve existing hooks and configuration. Do not auto-install a demonstration
policy or a package-manager toolchain merely because an example uses it. Test
an allowed case, the actual forbidden action, a legitimate exception, and the
configured failure behavior through the real adapter when claiming activation.

An authorization denial is not a reason to try another interpreter or encoding
to execute the same prohibited action. Preserve required permission checks and
use allowed read-only work while resolving the actual blocker.
