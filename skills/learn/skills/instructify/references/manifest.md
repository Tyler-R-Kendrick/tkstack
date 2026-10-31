# Manifest and managed update contract

An instruction manifest has exactly:

```json
{
  "version": 1,
  "id": "contract-evidence",
  "title": "Contract evidence",
  "scope": ".",
  "targets": ["agents", "claude"],
  "instructions": [{
    "id": "report-actual-results",
    "when": "Reporting validation of an API-boundary change.",
    "instruction": "State the actual consumer/provider checks and their results.",
    "verification": "Link the recorded command output for the current revision.",
    "boundary": "If a required check could not run, report that gap explicitly.",
    "source": "Reference the actual user request, repository contract, or learn evidence ID."
  }]
}
```

The example text above illustrates the format; it is not captured user evidence.
IDs are unique lowercase kebab-case within 64 characters. A manifest has 1–64
instructions with exactly the fields shown. Text fields are concise, nonempty
single lines without HTML ownership markers, up to 4096 characters. This keeps
long procedures in skills or referenced sources rather than startup context.
Duplicate JSON fields and unknown manifest fields are rejected.

`scope` is an owned project-relative directory (`.` for the repository). Targets
are explicit: `agents`, `claude`, `cursor`, `copilot`. The helper never chooses
a scope or target through inference and never uses home configuration by default.
The manifest must live inside the specified existing project. Paths cannot
traverse upward, cross symlinks, or write under `.git`, `vendor`, or `.tkstack`.
Scope/loading behavior differs by host; see [harness details](harnesses.md).
Directory scopes are literal paths, without glob metacharacters; adapters
derive their explicit descendant globs from that directory.

## Plan and check

`plan --project <root> --input <manifest>` returns JSON with the project,
manifest path, input snapshots, and exact before/after text for each changed
file. It is read-only. Review the diff in this artifact before applying it;
plans can contain existing private instruction text, so keep them in an
appropriate local task directory. `plan --remove` plans removal of the same
owned sections without deleting unrelated instructions.

`check` recomputes expected file alignment: exit 0 means aligned, 2 means
pending changes, 1 means invalid/conflicting input. It does not check native
loading, semantic agreement, or model compliance. A native rule file with an
unrelated owner is preserved; nonempty Codex override files require reconciling
the active source rather than silently writing a shadowed `AGENTS.md`.

## Ownership and safe application

Each managed section uses start/end markers, a manifest-path/ID-derived owner,
and a SHA-256 of its protected content. Native rule-file frontmatter is protected
as well. Another manifest cannot silently take over the same section ID;
manual edits inside the managed content must be reconciled explicitly. Changes
outside ordinary Markdown sections are preserved.

`apply` acquires `.instructify.lock` in the explicit project and recomputes the
whole plan. Source, target, override, import, or rendered-plan drift invalidates
the proposal before any writes. `--dry-run` performs the comparison without
creating a lock or directories. Independent projects/scopes can be planned
concurrently; writes inside one project serialize because instruction files
and imports can overlap. Busy writers fail promptly so a caller can retry.

File replacement is atomic per file, with existing permissions retained. New
files use the temporary file's restrictive permissions. On an ordinary write
error, completed writes are rolled back when their current bytes still match
what this operation published; changed files are reported as rollback gaps.
An external writer ignoring the lock can still race between checks and writes.
This is cooperative ownership/optimistic concurrency, not a security boundary
or multi-file filesystem transaction. A process crash may leave a partial batch;
inspect the files and create a fresh plan before recovery. Do not blindly reuse
an old plan or delete a lock while its writer may still be active.

Update/remove operations preserve other sections, imports, and user content.
An originally missing file can be removed if only this owned content remains;
an existing empty file stays an existing file. Dedicated native rule headers
remain when foreign trailing content needs them. Atomic replacement does not
by itself arbitrate multiple authors; keep the canonical source under one owner
or reconcile branch changes before publication.

The planner checks only the current manifest's explicit destinations; it does
not discover historical target/scope mappings. Before changing scope, targets,
ID, or source location, remove the old bindings using the old manifest, then
publish/apply the new one. Preserve the old manifest/plan in task or Git evidence
for this migration. Moving the source without migration changes its owner token.

The helper never invokes a model, executes instruction text, scans private
history, modifies vendor packages, or assumes an instruction grants permissions.
Semantic conflicts and provenance require source inspection by the author.
