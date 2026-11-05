"""Validate this checkout as an Agent Plugins 1.0.0 package.

The vendored schemas are the published 1.0.0 documents from
agentplugins/agent-plugins-spec (schemas/1.0.0/). The checker applies the
subset of JSON Schema those files use, then the specification rules the
schema does not express: command tokens, remote URLs, placeholder expansion,
and Agent Skills frontmatter for skills discovered at skills/*/SKILL.md.
"""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit


SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
PLUGIN_SCHEMA_NAME = "plugin.schema.json"
MCP_SCHEMA_NAME = "mcp.schema.json"
SKILL_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLACEHOLDER = re.compile(r"\$\{([^{}]+)\}")
SECRET = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9]|fc-[A-Za-z0-9]|ghp_[A-Za-z0-9]|github_pat_[A-Za-z0-9]"
    r"|xox[baprs]-[A-Za-z0-9]|AKIA[A-Z0-9]{8})"
)
EXPECTED_SERVERS = {
    "serena": {
        "type": "stdio",
        "command": "uvx",
        "args": [
            "--from",
            "git+https://github.com/oraios/serena",
            "serena",
            "start-mcp-server",
            "--project-from-cwd",
        ],
    },
    "playwright": {
        "type": "stdio",
        "command": "npx",
        "args": ["@playwright/mcp@latest"],
    },
    "firecrawl": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "firecrawl-mcp"],
    },
    "mobbin": {
        "type": "streamable-http",
        "url": "https://api.mobbin.com/mcp",
    },
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


def load_schema(name):
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _resolve_ref(root, ref):
    if not ref.startswith("#/"):
        return None
    node = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def validate_instance(instance, schema, root=None, path="$"):
    """Return errors for the JSON Schema subset published in the 1.0.0 files."""
    root = schema if root is None else root
    if "$ref" in schema:
        target = _resolve_ref(root, schema["$ref"])
        if target is None:
            return [f"{path} has an unresolved schema reference {schema['$ref']}"]
        return validate_instance(instance, target, root, path)
    if "oneOf" in schema:
        matches = [
            branch for branch in schema["oneOf"]
            if not validate_instance(instance, branch, root, path)
        ]
        if len(matches) != 1:
            return [f"{path} must match exactly one schema variant"]
        return []
    errors = []
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path} must be {schema['const']!r}")
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(instance, dict):
            return errors + [f"{path} must be an object"]
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path} is missing {key}")
        for key, value in instance.items():
            if key in properties:
                errors.extend(validate_instance(value, properties[key], root, f"{path}.{key}"))
            elif additional is False:
                errors.append(f"{path} has unknown field {key}")
            elif isinstance(additional, dict):
                errors.extend(validate_instance(value, additional, root, f"{path}.{key}"))
        banned = schema.get("propertyNames", {}).get("not", {}).get("enum", [])
        for key in instance:
            if key in banned:
                errors.append(f"{path} must not name {key}")
        return errors
    if expected == "string":
        if not isinstance(instance, str):
            return errors + [f"{path} must be a string"]
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path} is shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path} is longer than {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path} does not match {schema['pattern']}")
        return errors
    if expected == "array":
        if not isinstance(instance, list):
            return errors + [f"{path} must be an array"]
        item = schema.get("items")
        if isinstance(item, dict):
            for index, value in enumerate(instance):
                errors.extend(validate_instance(value, item, root, f"{path}[{index}]"))
        return errors
    return errors


def _json_object(path):
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return None, ["invalid UTF-8"]
    except json.JSONDecodeError as error:
        return None, [f"invalid JSON ({error.msg} at line {error.lineno})"]
    except OSError as error:
        return None, [str(error)]
    if not isinstance(loaded, dict):
        return None, ["JSON value is not an object"]
    return loaded, []


def _placeholder_errors(text, label):
    return [
        f"{label} contains ${{{name}}}, which Agent Plugins 1.0 leaves literal"
        for name in PLACEHOLDER.findall(text)
        if name not in {"PLUGIN_ROOT", "PLUGIN_DATA"}
    ]


def _command_errors(command):
    if not command or any(character.isspace() for character in command) or "${" in command:
        return ["command must be one executable token and must not contain placeholders"]
    if command.startswith("./"):
        if ".." in command.split("/"):
            return ["command must stay inside the plugin root"]
        return []
    if "/" in command or "\\" in command:
        return ["command must be a bare executable name or a ./ path"]
    return []


def _loopback(host):
    host = (host or "").strip("[]").lower()
    if host in {"localhost", "::1"}:
        return True
    parts = host.split(".")
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        numbers = [int(part) for part in parts]
        return numbers[0] == 127 and all(0 <= number <= 255 for number in numbers)
    return False


def _url_errors(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        return ["url must be an absolute http or https URL"]
    errors = []
    if parsed.username or parsed.password:
        errors.append("url must not contain user information")
    if parsed.fragment:
        errors.append("url must not contain a fragment")
    if parsed.scheme != "https" and not _loopback(parsed.hostname):
        errors.append("a non-loopback url must use https")
    return errors


def _secret_errors(value, label):
    if SECRET.search(value):
        return [f"{label} embeds a credential"]
    return []


def mcp_semantic_errors(document):
    """Specification rules that the MCP schema leaves to prose."""
    servers = document.get("mcpServers")
    if not isinstance(servers, dict):
        return []
    errors = []
    for name, entry in servers.items():
        if not isinstance(entry, dict):
            continue
        label = f"mcpServers.{name}"
        transport = entry.get("type")
        if transport == "stdio":
            command = entry.get("command")
            if isinstance(command, str):
                errors.extend(f"{label}.{item}" for item in _command_errors(command))
            for field in ("args", "env", "cwd"):
                value = entry.get(field)
                if isinstance(value, str):
                    errors.extend(_placeholder_errors(value, f"{label}.{field}"))
                elif isinstance(value, list):
                    for index, item in enumerate(value):
                        if isinstance(item, str):
                            errors.extend(_placeholder_errors(item, f"{label}.{field}[{index}]"))
                elif isinstance(value, dict):
                    for key, item in value.items():
                        if isinstance(item, str):
                            errors.extend(_placeholder_errors(item, f"{label}.env.{key}"))
                            errors.extend(_secret_errors(item, f"{label}.env.{key}"))
        elif transport in {"streamable-http", "sse"}:
            url = entry.get("url")
            if isinstance(url, str):
                errors.extend(f"{label}.{item}" for item in _url_errors(url))
                if PLACEHOLDER.search(url):
                    errors.append(f"{label}.url must not contain placeholders")
            headers = entry.get("headers")
            if isinstance(headers, dict):
                seen = {}
                for key, item in headers.items():
                    folded = key.lower()
                    if folded in seen:
                        errors.append(f"{label}.headers repeats {seen[folded]!r} as {key!r}")
                    else:
                        seen[folded] = key
                    if isinstance(item, str):
                        if PLACEHOLDER.search(item) or PLACEHOLDER.search(key):
                            errors.append(f"{label}.headers.{key} must be literal")
                        errors.extend(_secret_errors(item, f"{label}.headers.{key}"))
    return errors


def expected_server_errors(document):
    servers = document.get("mcpServers")
    if not isinstance(servers, dict):
        return ["mcp.json has no mcpServers object"]
    errors = []
    for name, expected in EXPECTED_SERVERS.items():
        entry = servers.get(name)
        if not isinstance(entry, dict):
            errors.append(f"mcp.json is missing server {name}")
            continue
        for key, value in expected.items():
            if entry.get(key) != value:
                errors.append(f"mcpServers.{name}.{key} is {entry.get(key)!r}, expected {value!r}")
        if name == "firecrawl" and "env" in entry:
            errors.append("mcpServers.firecrawl.env would overlay FIRECRAWL_API_KEY with a literal")
    return errors


def _unquote(value):
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, ["missing YAML frontmatter"]
    end = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        return None, ["unterminated YAML frontmatter"]
    fields = {}
    errors = []
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            errors.append(f"unparsed frontmatter line: {line}")
            index += 1
            continue
        key, rest = match.group(1), match.group(2).strip()
        if key in fields:
            errors.append(f"duplicate frontmatter field {key}")
        if rest == "":
            mapping = {}
            index += 1
            while index < end and (lines[index].startswith(" ") or lines[index].startswith("\t")):
                nested = re.match(r"^[ \t]+([A-Za-z0-9_.-]+):\s*(.*)$", lines[index])
                if not nested:
                    errors.append(f"unparsed nested frontmatter line: {lines[index].strip()}")
                else:
                    mapping[nested.group(1)] = _unquote(nested.group(2))
                index += 1
            fields[key] = mapping
            continue
        fields[key] = _unquote(rest)
        index += 1
    return fields, errors


def skill_document_errors(directory, text):
    fields, errors = parse_frontmatter(text)
    if fields is None:
        return errors
    unknown = sorted(set(fields) - SKILL_FIELDS)
    if unknown:
        errors.append("frontmatter has fields outside the Agent Skills spec: " + ", ".join(unknown))
    name = fields.get("name")
    if not isinstance(name, str) or not name:
        errors.append("frontmatter name is missing")
    else:
        if not SKILL_NAME.fullmatch(name) or len(name) > 64:
            errors.append(f"frontmatter name {name!r} is not an Agent Skills name")
        if name != directory.name:
            errors.append(f"frontmatter name {name!r} does not match directory {directory.name}")
    description = fields.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append("frontmatter description is missing")
    elif len(description) > 1024:
        errors.append("frontmatter description is longer than 1024 characters")
    compatibility = fields.get("compatibility")
    if compatibility is not None:
        if not isinstance(compatibility, str):
            errors.append("compatibility must be a string")
        elif len(compatibility) > 500:
            errors.append("compatibility is longer than 500 characters")
    metadata = fields.get("metadata")
    if metadata is not None:
        if not isinstance(metadata, dict):
            errors.append("metadata must be a map of strings")
        else:
            for key, value in metadata.items():
                if not isinstance(value, str):
                    errors.append(f"metadata.{key} must be a string")
    allowed = fields.get("allowed-tools")
    if allowed is not None and not isinstance(allowed, str):
        errors.append("allowed-tools must be a string")
    return errors


def _inside(root, path):
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def discovered_skill_errors(root):
    skills = Path(root) / "skills"
    if not skills.exists():
        return []
    if skills.is_symlink() or not skills.is_dir() or not _inside(root, skills):
        return ["skills/ is not a directory inside the plugin root"]
    errors = []
    for child in sorted(skills.iterdir()):
        if not child.is_dir():
            continue
        document = child / "SKILL.md"
        if not document.is_file():
            continue
        relative = document.relative_to(root).as_posix()
        if document.is_symlink() or not _inside(root, document):
            errors.append(f"{relative} resolves outside the plugin root")
            continue
        try:
            text = document.read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"{relative}: {error}")
            continue
        errors.extend(f"{relative}: {item}" for item in skill_document_errors(child, text))
    return errors


def conformance_problems(root):
    root = Path(root)
    problems = []
    plugin_path = root / "plugin.json"
    if not plugin_path.is_file():
        problems.append("missing plugin.json")
    else:
        plugin, errors = _json_object(plugin_path)
        problems.extend(f"plugin.json: {item}" for item in errors)
        if plugin is not None:
            problems.extend(
                f"plugin.json: {item}"
                for item in validate_instance(plugin, load_schema(PLUGIN_SCHEMA_NAME))
            )
    mcp_path = root / "mcp.json"
    if not mcp_path.is_file():
        problems.append("missing mcp.json")
        document = None
    else:
        document, errors = _json_object(mcp_path)
        problems.extend(f"mcp.json: {item}" for item in errors)
        if document is not None:
            problems.extend(
                f"mcp.json: {item}"
                for item in validate_instance(document, load_schema(MCP_SCHEMA_NAME))
            )
            problems.extend(f"mcp.json: {item}" for item in mcp_semantic_errors(document))
            problems.extend(f"mcp.json: {item}" for item in expected_server_errors(document))
    problems.extend(discovered_skill_errors(root))
    return problems
