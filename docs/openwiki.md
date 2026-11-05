# OpenWiki

[LangChain's OpenWiki](https://github.com/langchain-ai/openwiki) **0.7.2** is
installed locally with its official `openwiki` skill and stdio MCP server for
Codex, Claude Code, and Cursor. Restart the harness to discover the connection.

Ask your agent to initialize a wiki:

```text
Initialize this repository's OpenWiki from the current source and tests.
```

Ask for incremental maintenance after source changes:

```text
Update this repository's OpenWiki for changes since its last successful run.
```

The host-driven integration uses the coding agent's existing authenticated
session. It needs no separate OpenWiki model credential. It supplies deterministic
run state, a resumable page queue, source-grounded Claims, and finalization; the
agent researches and writes the assigned page. Retrieval is local and model-free.
Use it for concrete questions; the upstream skill explicitly avoids loading wikis
at every task start. Wiki content is context to verify against source.

Installation does not generate a wiki. `init` replaces generated documentation;
use `update` to retain and refresh existing pages. No schedule or background
generation job is enabled by this setup.

## Reproduce the installation

Node.js **22.22.0+** and npm are required; this installation was exercised with
Node **24.19.0** and npm **11.9.0** on Linux x86-64.

```sh
python3 scripts/install.py --target .
```

That links the skill. It does not run `npm ci` or register MCP.
The npm package version recorded with the source pin is **openwiki 0.7.2**
(`sources.lock.json`). This repository does not commit an npm lock for it.
A host that wants the CLI installs that package itself. Runtime files stay
under ignored `.tkstack/`.

Run the upstream `openwiki` CLI when Node and the package are installed. tkstack
does not wrap it. A host MCP entry, if you add one, uses
`.tkstack/openwiki/` for private config/state and disables telemetry by default.
Explicit `OPENWIKI_CONFIG_DIR` and `OPENWIKI_TELEMETRY_DISABLED` environment
settings take precedence. Keep credentials in that ignored state or the launching
environment. Standalone CLI generation uses its own provider setup; it is separate
from the host-driven MCP workflow.

Use tkstack's installer to manage the skill links. It does not register MCP
entries. OpenWiki's
own integration installer expects ownership of those destinations and rejects
symlinked components, so the two installers should not manage the same files.

## Evidence and sources

The six vendored documentation/skill/metadata files come unchanged from
[`305599f8e44203f9ca6b74bb6b38eebaf0b0405e`](https://github.com/langchain-ai/openwiki/tree/305599f8e44203f9ca6b74bb6b38eebaf0b0405e).
Their Git blob identities and modes are in `sources.lock.json`. The published
npm package is **0.7.2**. This repository does not commit that tarball's
integrity lock. Its official skill matches the vendored skill.
Only `integrations/openwiki` is installed as a skill; upstream connector-authoring
and Mermaid helpers are not added to the global skill catalog.

Native smoke evidence is stored in ignored
`.tkstack/evidence/openwiki/native-mcp.json`. It records real MCP initialization,
tool discovery, positive search and exact-section reading, and rejection of a
missing page for each of the three host identities, using an isolated fixture.
These checks make no generation/model calls and do not claim an actual native
Claude or Cursor session was run. The full wiki generation lifecycle has not been
executed against this repository.

This managed cloud session's `codex mcp get openwiki --json` did not expose the
project entry. The installer verifies the project config, and the MCP checks
launch its exact command directly; current-session discovery is not established.
Reload the harness and apply its normal project trust/connection controls.

OpenWiki provides repository documentation and retrieval. `/learn` remains the
authoritative correction ledger, and SkillOpt remains the custom-skill revision
gate. WikiSkill is a separate skill-evolution project.
