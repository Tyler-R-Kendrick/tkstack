# Harness preferences

| Harness | Install path |
| --- | --- |
| Codex | `.agents/skills` |
| Claude Code | `.claude/skills` |
| Cursor | `.cursor/skills`, plus `.cursor/rules` |
| Copilot | `~/.copilot/skills` at home, `.github/skills` in a project |
| Grok | `.grok/skills` |
| Kimi | `.kimi/skills` |
| Muse | `~/.config/muse/skills` at home, `.agents/skills` in a project |
| OpenCode | `.config/opencode/skills` at home, `.opencode/skills` in a project |
| t3code | No skills directory. `./install.sh --harness t3code` installs the delegate harnesses' placements (`delegates.t3code`): `.claude/skills`, `.agents/skills`, `.cursor/skills` and `.cursor/rules`, `~/.copilot/skills` or `.github/skills`, and `.grok/skills`. |

The personal, development and design profiles select named skills. The catalog profile enables the full source placement, vendored agents and Cursor rules. TKStack's Cursor steering rule accompanies each Cursor installation. Learn uses a generated host-facing index with a pointer to its canonical package; its authoring subcommands run through the mounted Learn interface. Codex user instructions honor CODEX_HOME; project and isolated home targets use their own paths.

The installer checks link destinations and owned startup sections. Native Codex discovery is exercised in the release suite. Other hosts need their own reload/trust and activation checks. See [bootstrap](bootstrap.md) for personal versus team configuration, and [integrations](integrations.md) for MCP and hook readiness.
