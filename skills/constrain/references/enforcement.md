# Enforcement

Use the same engine everywhere:

```sh
python3 <constrain>/scripts/constrain.py audit --repo /workspace/project
python3 <constrain>/scripts/constrain.py check --repo /workspace/project
python3 <constrain>/scripts/constrain.py check --repo /workspace/project --staged
python3 <constrain>/scripts/constrain.py check --repo /workspace/project --category dependencies --strict-dependencies
```

Tkstack's CI uses the hash-locked command-schema Python environment and checks before the offline suite. Git hooks need Python 3.11+ and PyYAML from the same requirements lock when workflow files are present; missing PyYAML fails closed. Its Git pre-commit gate reads
configuration, reviews, and tests from the index, so unstaged fixes cannot hide
bad staged content. The repository hook calls the skill engine directly; no
root wrapper or second detector. Other projects opt in with their own policy
and hook/CI command. Dotfiles setup installs the skill and its startup pointer;
it must not copy tkstack's budgets into unrelated projects or claim native
agent hooks are activated.

For a Claude Stop command hook, invoke the check command with the absolute
workspace path. Exit 0 permits completion; on constraint/input failure an
adapter must emit stderr and exit 2 to use Claude's blocking-error semantics.
Preserve existing settings and test the actual native event before claiming
activation. Git and CI are the installed enforcement in this repo; no Claude,
Codex, Cursor or MCP activation is implied. An agent reminder cannot replace
the commit/CI gate. Neither gate is a security boundary against an author who
edits policy or bypasses hooks; protect CI/review through repository settings.
