# Keep installation and usage documentation current

`README.md` is the install/use entrypoint. Focused pages in `docs/` own the
details. Documentation maintenance uses one deterministic checker, a reviewed
source/content ledger, repository completion hooks, and a Git pre-commit gate.
Checks use only Python's standard library and Git; they do not call a model,
rewrite docs, or automatically approve a new baseline.

## Review a source change

```sh
python3 src/check_docs.py check
python3 src/check_docs.py render
python3 src/check_docs.py refresh --area setup --reason 'Reviewed setup changes and updated install instructions'
python3 src/check_docs.py check
```

The policy in `docs/docs-policy.json` maps source paths to documentation owners.
The error identifies affected areas and pages. Compare the source change to
those pages, update actual instructions/examples, and verify relevant commands.
`render` updates only the README's install-pin block from `PYTHON_VERSION`,
`UV_VERSION`, and `UV_INSTALLER_SHA256` in `install.sh`. It preserves all other prose.

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
- README install-pin facts match `install.sh`.
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

## Completion checks

Run the documentation checker before marking a source change complete. A host may register its own completion hook. TKStack's personal installer leaves native registration and host trust to the user.

## Git pre-commit

Maintainers can enable the versioned hook in their TKStack checkout with `git config --local core.hooksPath .githooks` after checking the existing setting and hooks. If a hook manager is already configured, have it invoke `.githooks/pre-commit`. Ordinary installation and removal leave the source checkout's Git configuration alone.

The hook checks the staged constraint policy and documentation snapshot. An unstaged repair cannot satisfy a failing staged change. Sparse paths fall back to indexed content. Undo a manually selected hook path with Git at the same scope.

## Verify the maintainer recipe

Run `python3 -m unittest discover -s tests -v` from the checkout. The suite
uses the Python that runs it. CI installs the locked PyYAML/jsonschema packages
into `.tkstack/runtime/command-schema` and runs the same suite with that
interpreter. Some tests rebuild ignored aliases or native views.
`python3 scripts/install.py --target .` restores the normal source installation
before `python3 src/check_skills.py`.
Those generated views are not documentation inputs or versioned source. The
README Develop section has copy-paste commands for the unittest suite,
the opt-in deterministic repository-quality ceilings and the documentation
check. The source installer restores generated views before the skill gate.
Repository-quality rubric anchors can be reviewed by the invoking agent; there
is no separate model-judge launcher. See [Repository quality](../evals/README.md).

Test changes also pass the [constrain engine](../skills/constrain/SKILL.md). Its
review inventory names suite risks, behavioral oracles, verification kinds and
cross-layer overlap. The pre-commit hook checks that policy and sources from the
same staged snapshot before the documentation gate. Do not add another feature
doc when its existing page or skill reference can own the information.

The configured documentation byte budget counts both human-facing pages and
the reviewed source-hash ledger. Budget changes must identify the added
capability and its existing documentation owners; the Testify/constraint
addition changes those records without introducing another documentation tree.
