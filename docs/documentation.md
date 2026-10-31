# Keep installation and usage documentation current

`README.md` is the install/use entrypoint. Focused pages in `docs/` own the
details. Documentation maintenance uses one deterministic checker, a reviewed
source/content ledger, repository completion hooks, and a Git pre-commit gate.
Checks use only Python's standard library and Git; they do not call a model,
rewrite docs, or automatically approve a new baseline.

## Review a source change

```sh
python3 scripts/check_docs.py check
python3 scripts/check_docs.py render
python3 scripts/check_docs.py refresh --area setup --reason 'Reviewed setup changes and updated install instructions'
python3 scripts/check_docs.py check
```

The policy in `docs/docs-policy.json` maps source paths to documentation owners.
The error identifies affected areas and pages. Compare the source change to
those pages, update actual instructions/examples, and verify relevant commands.
`render` updates only the README's managed profile/toolchain block from the
same JSON manifests used by setup. It preserves all other prose.

`refresh` records the reviewed source/doc contents and executable modes in
`docs/docs-freshness.json`. It requires an actual reason and does not update
prose. Refresh selected areas with repeated `--area`, or use `--all` after a
full review. Source changes without any mapped Markdown content change require
an explicit `--no-doc-impact` reason, for example an internal refactor whose
documented behavior and interface remain unchanged. A timestamp-only touch is
not a doc edit. Keep the reason specific to the change rather than inventing
cosmetic edits to satisfy a hook.
An explicit refresh also synchronizes shared-document hashes for areas whose
source inputs are unchanged, retaining their source review and recording the
docs-only refresh reason. A shared README edit therefore does not require
pretending that unrelated source changed.

The ledger is an authored verification artifact containing relative public source
paths, content identities, modes, and review reasons. It contains no session
transcript or credentials; runtime receipts stay ignored under `.tkstack`.

Stage the source, corresponding docs, and ledger together. Initial publication
must include the new scripts, policy, manifests, and ledger; the staged gate
cannot validate files left untracked or unstaged. A change to the mapping policy
requires reviewing all areas. Saved history remains in normal Git history.

## What the checks establish

- Source hashes, paths, and executable modes match an explicitly reviewed documentation snapshot.
- README profile/toolchain facts match the actual bootstrap manifests.
- Local inline Markdown links in README, glossary, and `docs/` point to files/directories in the same snapshot.
- New/deleted/renamed matched sources are detected, independent of timestamps.

The installer-owned steering block in root `AGENTS.md` is normalized for both
worktree and index fingerprints to accommodate legacy checkout-specific paths.
Self-project setup now emits portable relative pointers and a repository owner
marker; external project/home targets retain checkout-specific ownership.
Authored instructions outside that block are checked normally; renderer changes
are covered by the mapped source scripts. Malformed/duplicate marker blocks are
not normalized. This keeps fresh installation from creating machine-path drift
in the reviewed docs ledger.

This is a source-drift/review gate, not a proof of semantic completeness. An
engineer still verifies explanations and examples. The lightweight link check
ignores fenced code, external URLs, and fragment-only links; it does not fetch
websites or validate every CommonMark extension/heading anchor. Keep skill
package validation and actual behavioral tests in the usual checks.

## Repository agent hooks

Project installation into this source checkout registers `repo-docs` completion
hooks through the normal ownership-aware native configuration path:

| Harness | Event | Failed check |
| --- | --- | --- |
| Codex | `Stop` | JSON continuation decision with the failing areas |
| Claude Code | `Stop` | JSON continuation decision with the failing areas |
| Cursor | `stop` | One follow-up with the failing areas |

The callback checks only this Git repository (including related worktrees).
Other repositories return an empty result. Reentry/loop counters cap continuation
at one attempt; Git remains the commit-time gate if the agent stops again with
issues. Hooks read the worktree; they never refresh the ledger automatically.
Malformed hook input/checker errors return nonzero instead of silently claiming
success. Other upstream hook adapters retain their existing behavior.

Apply project configuration with:

```sh
./install.sh --target "$PWD" --scope project --workspace "$PWD" --offline
```

Registration is separate from observed native activation. Reload/restart the
host when required. Codex requires review/trust of new or changed non-managed
hook definitions through `/hooks`; setup does not bypass that trust mechanism.
The adapters follow the current documented
[Codex Stop protocol](https://developers.openai.com/codex/hooks),
[Claude hooks protocol](https://code.claude.com/docs/en/hooks), and
[Cursor stop protocol](https://cursor.com/docs/agent/hooks).

## Git pre-commit installation

Full setup installs the source repository's Git hook. Narrow maintenance uses:

```sh
python3 scripts/setup_repo_hooks.py --dry-run
python3 scripts/setup_repo_hooks.py
python3 scripts/setup_repo_hooks.py --check
python3 scripts/check_docs.py check --staged
```

The versioned handler is `.githooks/pre-commit`. Installation places an owned
dispatcher in the repository's effective default Git hooks directory, preserving
and chaining any existing pre-commit hook before the docs check. Other hooks and
Git configuration remain untouched. Shared/custom `core.hooksPath` managers are
preserved; add the versioned handler to that manager rather than overwriting it.
The installer reports that case explicitly. A source copy without Git metadata
keeps the versioned files and reports that Git activation is deferred.

The Git callback checks the actual **index**: policy, docs, source identities,
and generated README facts all come from staged blobs. Unstaged fixes cannot
satisfy a staged source change. Sparse checkouts use complete index entries;
worktree checks fall back to indexed content only for skipped sparse paths.
The dispatcher follows the active worktree's Git index while retaining a usable
checker from the durable source checkout. Git hooks can be skipped by Git's
normal override mechanisms; no server-side CI enforcement is claimed here.

To restore the previous owned pre-commit setup:

```sh
python3 scripts/setup_repo_hooks.py --uninstall
```

Removal restores the saved predecessor or removes only the owned dispatcher.
Foreign or modified installed hooks are preserved for inspection. Native hook
entries use the ordinary installer ownership/uninstall path. Editing generated
host settings is temporary; source setup will reapply its declared configuration.

## Verify the maintainer recipe

Use the bootstrap-provisioned command interpreter for the test suite, then
reapply `python3 scripts/install.py --target .` before running doctor. Some tests
rebuild ignored aliases/native views using their own interpreter. Reapplication
restores the normal source installation context; those generated views are not
documentation inputs or versioned source. The README includes this sequence.
