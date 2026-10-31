# 0013: Enforce reviewed documentation at completion and commit

Status: accepted, 2026-10-30.

The user requested an installation/use README plus repository and Git hooks
that keep docs current. A long feature history obscured onboarding, and a
plain Markdown touch would not establish that source changes were reviewed.

Make README the install/use entrypoint with focused links. Bootstrap profile
JSON and toolchain pins generate its managed factual block; setup and the
renderer share profile validation. A source-to-doc policy and versioned review
ledger compare content and modes, detecting additions, deletions, and drift.
Refresh is explicit, with a reason; unchanged documentation for an internal-only
source change needs a stated no-doc-impact exception. Checks never auto-refresh.

One standard-library checker supports worktree and Git-index snapshots. The
pre-commit path reads staged blobs/policy/docs, so unstaged fixes cannot pass.
Sparse worktree checks fall back to index data only for skipped paths. Normalize
the installer-owned steering block in root AGENTS.md to avoid clone-path noise;
authored instructions and renderer changes remain covered.

Register source-project completion adapters for Codex, Claude Code, and Cursor
through the existing native installer. They share the checker, ignore other
repositories, and cap continuation at one attempt. Git remains the commit-time
gate. Install an owned Git dispatcher that preserves/chains a predecessor and
leaves other hooks/configuration alone; preserve external hook-manager setups.

Hashes and structural checks establish drift and review provenance, not semantic
completeness. Engineers still verify instructions and actual examples. Native
registration/replay is distinct from host activation/trust. Git's normal hook
override mechanisms are not server-side enforcement. This task adds no CI or
automatic inference/document rewriting.
