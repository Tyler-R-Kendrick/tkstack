"""Repository policy for the MCP servers this checkout ships.

Agent Plugins 1.0 does not require mcp.json, and §6.2 says an absent fixed
location is not an error. The spec also does not name a server list. These
pins are this repository's choice. Spec conformance stays in agent_plugins.py.
"""

from pathlib import Path

from agent_plugins import json_object


EXPECTED_SERVERS = {
    "playwright": {"type": "stdio", "command": "node",
                   "args": ["${PLUGIN_ROOT}/integrations/mcp/node_modules/@playwright/mcp/cli.js"]},
    "firecrawl": {"type": "stdio", "command": "node",
                  "args": ["${PLUGIN_ROOT}/integrations/mcp/node_modules/firecrawl-mcp/dist/index.js"]},
    "vercel": {
        "type": "streamable-http",
        "url": "https://mcp.vercel.com",
    },
    "graphify": {
        "type": "stdio",
        "command": "graphify-mcp",
        "args": ["${PLUGIN_DATA}/graphify-out/graph.json"],
    },
}


def expected_server_errors(document):
    servers = document.get("mcpServers")
    if not isinstance(servers, dict):
        return ["mcp.json has no mcpServers object"]
    errors = ["Serena needs an explicit consumer project in native host configuration"] if "serena" in servers else []
    for name, expected in EXPECTED_SERVERS.items():
        entry = servers.get(name)
        if not isinstance(entry, dict):
            errors.append(f"mcp.json is missing server {name}")
            continue
        for key, value in expected.items():
            if entry.get(key) != value:
                errors.append(f"mcpServers.{name}.{key} is {entry.get(key)!r}, expected {value!r}")
        if name == "firecrawl" and "env" in entry:
            errors.append(
                "mcpServers.firecrawl.env would overlay FIRECRAWL_API_KEY with a literal"
            )
    return errors


def policy_problems(root):
    """Problems with this checkout's shipped MCP document. Not spec conformance."""
    path = Path(root) / "mcp.json"
    if not path.is_file():
        return ["missing mcp.json"]
    document, errors = json_object(path)
    if document is None:
        return []
    del errors
    return expected_server_errors(document)
