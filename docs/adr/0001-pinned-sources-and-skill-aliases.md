# Pin upstream snapshots and adapt names in generated views

Status: accepted. Date: 2026-10-29.

## Context

Pstack, Tstack, and Matt Pocock's skills must coexist in one dotfiles setup.
Pstack also calls skills from Cursor Team Kit. Pstack and Matt both define
`tdd`, and Matt's other skills invoke its own TDD workflow.

## Decision

Vendor all four packages with their licenses and supporting files. Pin upstream
commits, Git blob hashes, symlink targets, and executable modes. Install their
skills offline into Codex, Claude Code, and Cursor, including Matt's misc and
beta buckets. Keep Pstack's engineering entry point as the preferred default.

Export Pstack's TDD skill as `tdd` and Matt's as `matt-tdd`. Generate Matt's skill
tree under `.tkstack/`, renaming the declaration and invocation references while
preserving relative file links and invocation-policy metadata. Keep the rule
in `harnesses/skills.json`. Link agents into Claude Code and Cursor and native
Cursor rules into Cursor.

## Consequences

Upstream files remain byte-for-byte reviewable and updates are explicit.
Installed links depend on keeping this checkout in place. A new checkout must
run the installer to create its generated views and links. Changes to alias
rules should be preceded by uninstalling the old layout. Installation does
not create model access or reproduce a harness's native runtime features.
