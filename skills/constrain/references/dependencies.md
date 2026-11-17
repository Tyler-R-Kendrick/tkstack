# Dependencies and supply-chain constraints

A GitOps-style desired state is reviewed in Git and consumed reproducibly. An
exact version alone is not artifact integrity: enforce a content digest with a
lock and use the package manager's hash-verifying installation command. Commit
and review lock changes with their direct dependency changes. A digest binds
bytes to the lock; it does not establish that the original package is benign,
that a publisher is trustworthy, or that untested platforms use the same bytes.

The built-in dependency linter discovers tracked/unignored `package.json` and
`requirements.lock` outside `vendor/`, GitHub workflow/composite-action YAML,
and `.devcontainer/devcontainer.json`. It rejects absent npm locks, lock/manifest
drift, absent direct package entries, and installed packages without a decoded
SHA-256/384/512 SRI digest; each locked pip requirement needs `==` and SHA-256.
It parses YAML with PyYAML's safe loader, rejects duplicate keys and requires
remote actions/reusable workflows at full Git commits and Docker actions at OCI
SHA-256. Devcontainer image/feature references need SHA-256 OCI digests. Git
commit IDs pin source identity; they are not npm archive integrity hashes.

Use `npm ci` with the checked-in lock and `pip install --require-hashes -r
<lock>`; checking that a digest is present is not verification of downloaded
bytes. Ensure the installer actually consumes the checked lock. The linter
reports unlocked `npx`/`uvx` MCP runtime fetches and Dockerfile builds as warnings:
they are not protected by the npm/pip source-lock checks. Resolve the runtime
launch with a reproducible transitive lock before claiming supply-chain coverage;
reports do not convert warnings into verified dependencies. Add
`--strict-dependencies` to treat discovered unchecked runtime fetches as blocking
violations; enable that gate wherever the project requires a fully locked runtime. The scanner also reports this repository's recognized Serena uvx installer
launch and mutable bootstrap archive fallback. These are narrow AST/text
patterns, not general Python dataflow or a shell parser; externally installed
CLIs, hosted-runner images, and other host-provided tools remain outside discovery. `sources.lock.json`
uses Git blob identities, checked separately by the installer; this is not a
SHA-256 release archive or provenance signature.

Explicit `--category dependencies` and the default source gate use the same
checks; malformed/missing inputs fail. YAML checks need PyYAML from the existing
hash-locked command-schema environment; missing PyYAML fails closed. Local
workspace links and local actions follow different ownership rules from remote
artifacts; inspect their content and containing repository. Git ignores, nested
Dockerfiles, dynamically generated dependencies and remote service behavior
remain outside this scanner's claims. Avoid catch-all waivers or re-baselining
hashes merely to clear a failure.

Recognized unsupported lock formats (including npm shrinkwrap, Yarn, pnpm, Poetry, uv, Cargo,
Go, Composer and Bundler) fail closed until a verified native adapter exists.
Detection does not cover every package ecosystem or every inline shell fetch.
