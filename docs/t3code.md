# t3code

T3 Code is an orchestrator. It has no skills directory and no install path
of its own. `scripts/install.py` does not accept `--harness t3code`, and
`scripts/harness_paths.py` does not link one.

`skills/skills.json` `delegates.t3code` names the hosts T3 Code runs: Claude,
Codex, Cursor, Copilot, and Grok. T3 Code consumes the skills those delegate
harnesses already placed. The placements are the install paths in
[Harness preferences](harnesses.md). Installing tkstack into those hosts is
how T3 Code gets the skills:

```sh
./install.sh --harness claude --harness codex --harness cursor --harness copilot --harness grok
```

The default install already links Claude, Codex, and Cursor. Repeat
`--harness` for Copilot and Grok. Repo-quality counts t3code as covered when
every host in `delegates.t3code` is itself a harness the installer links.
