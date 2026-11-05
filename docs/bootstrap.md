# Install agent dotfiles

One command installs tkstack. Outside a checkout it obtains
`~/.local/share/tkstack` with Git, or with a curl tarball when Git is absent,
and continues from there. Inside a checkout, `./install.sh` installs that
checkout. Bash and curl are the host prerequisites.

```sh
curl -fsSL https://raw.githubusercontent.com/Tyler-R-Kendrick/tkstack/main/install.sh | bash
```

`install.sh` is the host wrapper. It execs `scripts/install.py`, which links
files and then initializes Serena. It does not install language toolchains,
edit shell startup, register native hooks, write harness MCP config, write
launchers, or rewrite `AGENTS.md` / `CLAUDE.md`. Portable servers stay in
root `mcp.json`. See [Agent Plugins](agent-plugins.md).

The default links Codex, Claude Code, and Cursor. Repeat `--harness` for
Copilot, Grok, Kimi, Muse, or OpenCode. t3code is an orchestrator and is never
linked. `--scope project` uses each host's project skill directory; the default
for a home target is home scope. Keep the checkout: the links point at it.

```sh
./install.sh --dry-run
./install.sh --target /repo --scope project
./install.sh --harness copilot --harness grok
./install.sh --uninstall
```

`--dry-run` prints the link plan and the Serena commands, and writes nothing.
`--uninstall` removes this checkout's links for every harness, including a
legacy `.muse/skills` link, unsets `core.hooksPath` when its value is
`.githooks`, and skips Serena. `--harness` does not limit uninstall. A second
uninstall changes nothing. Foreign links stay.

## Host prerequisites

Missing Python **3.12.15** is installed with uv **0.12.23** after sha256
`b8e6c43099ee9f9a550984d3ad56948457c689e7a99c090b35377234ac241491` is checked.
The download is a temporary file. A caller-supplied `UV_INSTALL_DIR` is ignored;
the script runs `$HOME/.local/bin/uv`. `TKSTACK_PYTHON` wins when it is Python
3.11 or newer. Otherwise the script tries `python3`, `python3.13`,
`python3.12`, and `python3.11`.

`TKSTACK_HOME` chooses the checkout (default `~/.local/share/tkstack`). A
directory this run did not create is used only when its git origin matches
`TKSTACK_REPO` or `TKSTACK_TRUST_HOME=1`. A matching origin is fast-forwarded
with `git pull --ff-only`. Pull failure tells you to commit or stash.
`TKSTACK_TRUST_HOME=1` on a non-matching git checkout runs that tree and does
not pull. On a non-git tree it downloads again and keeps `.tkstack`.

Without Git, the default archive is
`https://codeload.github.com/Tyler-R-Kendrick/tkstack/tar.gz/main`.
`TKSTACK_TARBALL` must be `https://`. The archive has no content hash. The
script rejects curl failure, more than one top-level directory, and members or
symlinks that escape the extract directory. Extraction uses `--no-same-owner`
and `--no-same-permissions`. Symlink checks use `readlink`. Replacing a tarball
checkout copies `.tkstack` into the new tree and restores the old directory if
the final move fails.

`install.sh` wraps its work in `main` and calls it on the last line, so a
truncated `curl | bash` download does not run a prefix.

## What the link step writes

`scripts/install.py` symlinks each selected host's skill directory at the
pinned skills, agents, and Cursor rules. It also links `.agents/steering` at
`.tkstack/steering` when Learn is present, and `.agents/principles` at
`skills/tkstack-principles`. Alias views under `.tkstack/` rewrite installed
names (`matt-tdd`, `emil-prototype`, `pstack-unslop`) without changing
`vendor/`. Graphify has no `SKILL.md` upstream. The installer copies each host
entrypoint and its reference pages to
`.tkstack/skill-views/graphify/<host>/graphify/SKILL.md`. That copy is the
upstream file bytes. It does not rewrite commands or install Graphify.

On a git checkout, install sets `core.hooksPath=.githooks`. Git then runs
`.githooks/pre-commit` and ignores `.git/hooks`. A value that is already
`.githooks` is left alone. Any other value is replaced. Uninstall unsets the
key only when it is still `.githooks`. A directory that is not a git checkout, or a PATH with no `git` binary,
prints `skip git docs hook: not a git checkout` and the link step still
finishes. Dry-run prints the config change and does not run it.

## Serena

After the links, install runs Serena's documented uvx setup when `uvx` is on
`PATH`:

```text
uvx --from git+https://github.com/oraios/serena serena init
uvx --from git+https://github.com/oraios/serena serena project index
```

`serena init` sets up the language-server backend. `serena project index`
runs in the install target when the scope is `project`, and in this checkout
when the scope is home. It does not walk the home directory. The index may
create a gitignored `.serena/` directory in that project. `--dry-run` prints
the two lines and does not execute them. Uninstall prints
`skip serena: uninstall`. If `uv` or `uvx` is absent, or either command exits
non-zero, install prints `skip serena:` and keeps the links it already made.
That includes an offline `uvx` fetch. No API key is written.

Required environment for the shipped MCP servers, not for this index step:

| Variable | Server | When it is required |
| --- | --- | --- |
| `FIRECRAWL_API_KEY` | `firecrawl` (`npx -y firecrawl-mcp`) | Cloud Firecrawl tools. Export it for the client process. `mcp.json` does not reference it, because Agent Plugins would pass `${FIRECRAWL_API_KEY}` through as literal text. |
| none | `serena`, `playwright`, `graphify` | Local commands. Playwright needs Node. Graphify needs `uv tool install "graphifyy[mcp]"` and a graph at `${PLUGIN_DATA}/graphify-out/graph.json`. |
| none | `mobbin`, `vercel` | OAuth in the MCP client. Mobbin requires a paid Mobbin plan. |

## Devcontainer

[`.devcontainer/devcontainer.json`](../.devcontainer/devcontainer.json) runs
`install.sh --target <workspace> --scope project` after create and on later
starts. The link step does not download skills. The image's Node feature is
the devcontainer's own, not something `install.sh` downloads.

A dotfiles install in another devcontainer can use:

```json
{
  "dotfiles.repository": "Tyler-R-Kendrick/tkstack",
  "dotfiles.targetPath": "~/.local/share/tkstack",
  "dotfiles.installCommand": "install.sh"
}
```

## Maintainer checks

Preview, link this checkout, and review docs from the repository root:

```sh
./install.sh --target "$PWD" --scope project --dry-run
python3 scripts/install.py --target . --scope project
python3 skills/sdlc/scripts/routing_inventory.py check
python3 src/check_skills.py
python3 src/check_docs.py check
python3 -m unittest discover -s tests
```

`python3 src/tkstack.py` runs a compiled skill or workflow. There is no
generated `tkstack` launcher.
