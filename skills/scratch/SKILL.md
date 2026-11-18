---
name: scratch
description: Use an ignored, task-owned workspace for drafts, whiteboarding, notes, and exploratory evaluation artifacts. Select when temporary working material needs a place during a task, then preserve requested results and clean up the finished task's own files.
license: MIT
compatibility: "Any agent harness; TKstack's state helper requires Python 3.11+."
metadata:
  author: Tyler Kendrick
  version: "0.1.1"
  kind: guidance
---

# Scratch

Use the active project's `.tkstack/.scratch/` for disposable drafts, sketches,
notes, intermediate files, and exploratory eval plans or results. It is local
working space, not a source of authoritative instructions or a permanent record.
Never stage, force-add, or commit its contents. Git ignore rules can be overridden
and do not protect secrets; avoid putting credentials or unnecessary sensitive
data in scratch.

## Start

Work from the chosen project root. TKstack setup creates `.tkstack/.scratch/`
and an explicit `/.scratch/` entry in `.tkstack/.gitignore`. If setup has not
run or the directory is missing, initialize it through the installed state
helper. For a project installation, use its principles link:

```sh
python3 .agents/principles/scripts/tkstack_state.py init --project . --namespace .scratch &&
  mktemp -d .tkstack/.scratch/work-XXXXXXXX
```

If only the personal installation is present, run this from the project root:

```sh
python3 ~/.agents/principles/scripts/tkstack_state.py init --project . --namespace .scratch &&
  mktemp -d .tkstack/.scratch/work-XXXXXXXX
```

Use the unique path returned by `mktemp` as this task's owned directory. Do not
share mutable files between tasks or write loose files at the scratch root. If
the helper, ignore policy, or expected directory cannot be verified, use a
private OS temporary directory outside the checkout and report the limitation.
Some tools, including TKstack's native Git experiment controller, require their
own worktrees or evidence outside a source checkout; follow that tool's contract.

## Finish or resume

Stop and join this task's writers. Review the actual files and retain anything
needed for ongoing review, a resumable experiment, or the user's requested
evidence. Promote a requested durable result to its canonical source location
after review; do not stage the temporary copy. Check the staged changes before
committing.

When the task is complete and retained results are safe, confirm `.tkstack/`
and `.scratch/` are not symlinks and the resolved task directory is a direct
child of that scratch root, is not itself a symlink, and has no active writers.
Then remove only that child. Never delete the scratch root, another task's
files, or an unknown/stale directory automatically. If using a shell, pass the
verified absolute child path explicitly to `rm -r --`; do not use a glob or an
unresolved variable.
If ownership or retention is unclear, leave the directory intact and report it.
