# Official Caveman plugins

The canonical publisher is [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman).
Version **4.0.1** is pinned at
`9b68f7ed12b05e7efaff18e65c5a3fc2849fd0a4`. Its Claude marketplace contains one
plugin named `caveman`; the repository also supplies native Cursor and Codex
plugin layouts. This installation uses those official sources, rather than a
third-party skill with the same name.

The selected snapshot includes all 22 root skills, three Cavecrew agents,
official Claude/Cursor/Codex manifests, commands, Node hook dependencies, and
Apache-2.0/MIT notices. All 151 selected files are locked byte-for-byte with
their upstream Git blob hashes and modes. The separate Codex plugin bundle
is retained as published; the shared installer exposes the full root skill set
in all three harnesses without loading a duplicate plugin bundle.

```sh
python3 scripts/install.py --target .
python3 scripts/doctor.py --target .
```

The managed installation links the official skills and agents and registers
the official hook scripts through the existing adapters. It does not invoke a
native marketplace CLI or claim a native plugin-cache install. Claude/Cursor
CLIs are absent in this workspace; loading these files in a real host requires
a restart and any host-required trust. Do not additionally enable Caveman's
marketplace hooks alongside these managed registrations: choose one owner to
avoid duplicate lifecycle calls.

| Host | Official lifecycle behavior installed |
| --- | --- |
| Codex | Stateless SessionStart context, using the official `.codex/codex-sessionstart.js` |
| Claude Code | SessionStart, SubagentStart, prompt mode tracking, SessionEnd usage recording |
| Cursor | SessionStart context with the official `additional_context` output |

Use `/caveman` (`$caveman` in Codex), `/ultracave`, or `/megacave` explicitly.
Other entries include `/cavecrew`, `/caveman-compress`, `/caveman-review`,
`/caveman-learn`, and `/caveman-setup`. The installed source procedures retain
their native tool/model requirements. Personal `learn`, `sdlc`, and `unslop`
remain the owners of this repository's corresponding portable workflows.

The official startup default is `caveman`. Set `CAVEMAN_DEFAULT_MODE=manual`
before launching the host for opt-in activation, or `off` to disable default
injection. The resolver also supports the upstream `.caveman.json` configuration.
Claude's prompt hook tracks `stop caveman` per session and preserves it on
resume/compaction. Codex and Cursor use the official stateless startup hooks;
their conversation-level stop behavior is a skill instruction, not persisted
prompt-hook state. Ponytail is independently installed and has its own mode
controls; enabling incompatible voices together requires an explicit choice.

Claude's hook subprocess stores Caveman flags/history under
`.tkstack/state/caveman/claude`, isolated from home settings. The adapter removes
the three `CAVECREW_*_MODEL` variables in that subprocess because upstream
overrides can rewrite installed agent files. Vendor pins remain immutable.
Inherited provider authentication and routing are preserved. The separate
proxy/CLI service, MCP shrink, statusline, account integration, and Gemini or
OpenCode runtime installation are not enabled by this plugin setup.

Direct Node tests cover both startup output protocols, explicit opt-out,
Claude stop/resume and concurrent-session separation, missing Node, and
immutable source files. These establish hook behavior outside the host, not
live session activation, compression quality, or token/billing savings.
