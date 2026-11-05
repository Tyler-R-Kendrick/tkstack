# t3code

T3 Code is an orchestrator. It has no skills directory of its own.
`--harness t3code` installs the placements of every host in `skills/skills.json`
`delegates.t3code`: Claude, Codex, Cursor, Copilot, and Grok. Those hosts read
their own skill directories. There is no t3code directory.

```sh
./install.sh --harness t3code
./install.sh --dry-run --harness t3code
./install.sh --uninstall
```

Home scope links `.claude/skills`, `.agents/skills`, `.cursor/skills` (and
`.cursor/rules`), `.copilot/skills`, and `.grok/skills`. Project scope uses
`.github/skills` for Copilot. `--dry-run` prints that plan and writes nothing.
`--uninstall` removes this checkout's links for every harness, including those
placements. `--harness` does not limit uninstall. The paths are the same ones
in [Harness preferences](harnesses.md).

The default install already links Claude, Codex, and Cursor. `--harness t3code`
also links Copilot and Grok. Repo-quality counts t3code as covered when every
host in `delegates.t3code` is itself a harness the installer links.
