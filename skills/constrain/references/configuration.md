# Configuration and sparsity

One authored policy lives in `.constrain/config.json`; hash-bound suite reviews
live in `.constrain/reviews.json`. Do not add a parallel requirements ledger,
per-test Markdown, generated reports, caches, or transcripts there. CLI stdout
is the report; retain temporary experiments in ignored workspace scratch.

Version 1 requires `version`, `tests`, `layout`, and `artifacts`; optional `documents`, `boundaries`, and `execution` configure additional checks. `tests` requires
`include`/`exclude` arrays of repository-relative fnmatch globs, `max_cases`,
`max_bytes`, `reviews` (relative JSON path), and `exceptions`. Each exception has
an exact `rule`, `path` (`suite:Class.test_method`), and concrete `reason`.
Unknown fields, duplicate JSON keys, invalid paths or negative budgets fail.
`audit` includes discovered identities, hashes and raw findings; `check` is
compact. Both exit 1 for violations, 2 for invalid inputs, 0 for a clean result.
Neither updates hashes or changes policy. `--category source|tests|layout|artifacts|dependencies|execution|documents|boundaries|all` selects
the applicable layer. The CI/Git source gate defaults to `source`; build/deployment gates use `all`
or `artifacts` after building.

`layout.budgets` contains named records with `id`, `include`, `exclude`,
`max_files`, `max_bytes`, `max_depth`, and `reason`. Depth is POSIX path-component
count; bytes are actual content bytes; counts use Git tracked plus unignored
untracked files, or exactly the index with `--staged`. File globs use Python
fnmatch (`*` can span `/`). An untracked empty directory has no budget footprint.
Inputs are bounded to 4 MiB each; symlink content is rejected rather than followed.
Budgets describe ownership: tests in tests/, engine code with its skill, durable
usage with the matching reference, shared entrypoints in src/, snapshots in
vendor/. Vendor bytes are immutable and excluded from owned sparsity budgets.

Before increasing a limit, first remove duplication or extend a canonical owner.
An increase requires an explicit reviewed config diff explaining the new
contract, cost, and why existing ownership cannot serve it. Ratchet down after
cleanup. There is no automatic baseline, waiver command, or auto-approval.
Categories need a real detector, measurable metric, good/bad/exception fixtures,
and enforcement before adding another config namespace. Do not add an MCP server
or abstraction layer until a real consumer needs an additional transport.

## Deployment artifact budgets

`artifacts` is an array of records with literal relative `path`, `max_bytes`,
`baseline_bytes`, `max_growth_bytes`, `environment`, and `value`. Optional
`kind` is `file` (default) or `directory`. A directory can additionally set
`max_file_bytes` and `max_files`; the checker sums every regular file and
rejects symlinks and special files. `environment`
cites the host/product limit and the artifact measured; `value` states the useful
feature justifying growth (or why zero growth is allowed). Run
`check --repo <workspace> --category artifacts` after building. It reads named
files even when Git ignores them, and rejects missing outputs, symlinks,
over-ceiling files and unbudgeted growth. Large binaries use stat, not full
content reads. The hard environment ceiling and discretionary growth allowance
are separate constraints. Shrinking is permitted. Config diffs remain reviewed;
the checker cannot prove a feature's value or a cited host limit's currency.

The default `source` gate covers source tests/layout, independent of build outputs;
artifact checks run in the build/deployment job after its build, never the
staged-source hook. `all` includes every configured artifact; an empty artifact list fails an
explicit `artifacts` check.
Tkstack currently deploys no Pages site or binary, so its array is empty.
For GitHub Pages, consult the current official Pages limits for the actual
published site and file limits; enforce those at the packaging boundary, with
headroom. A compressed archive's byte count is not the expanded site's size.
Point a directory budget at the actual expanded publish directory to enforce
site totals and any per-file limit; do not substitute compressed archive size.

## Additional implemented rules

`documents` has `include` and `exclude` Git-snapshot globs for exact-byte
duplicate detection. `boundaries` is a list of rules with distinct `id`,
`include` Python path globs, and arrays `forbid_imports` and `forbid_calls`.
An empty matched scope fails. These are syntactic checks, not dataflow or
semantic equivalence. `execution` contains positive integer `max_jobs` and
`max_timeout_minutes` for GitHub workflow jobs. Dependency lock and action
source discovery runs automatically in the source gate; see
[dependencies](dependencies.md) for required PyYAML, supported formats and
known acquisition gaps. Rule findings have stable category-prefixed IDs.

The source checker and documentation gate share `scripts/git_snapshot.py` for bounded worktree, staged and sparse reads. Policy inputs reject symlinks. Documentation fingerprints may record the link target text.
