"""Canonical executable workflow templates and optional inference runtime."""
import json
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
BACKENDS = {"python": ("py", "python3"), "ai-sdk": ("ts", "node")}


def workflow_files(backend, description):
    if backend not in BACKENDS:
        raise ValueError("Backend must be python or ai-sdk")
    suffix, runtime = BACKENDS[backend]
    files = {"scripts/LICENSE.tkstack": (PACKAGE / "LICENSE").read_bytes()}
    files["scripts/tkstack_state.py"] = (PACKAGE / "scripts/tkstack_state.py").read_bytes()
    files['references/subcommands.md'] = (PACKAGE / 'references/command-definitions.md').read_bytes()
    for name in ('codify.py', 'workflow_authoring.py', 'command_schema.py', 'command.schema.json', 'command_manual.py', 'json_contract.py'):
        files['scripts/' + name] = (PACKAGE / 'scripts' / name).read_bytes()
    for name in ('requirements.in', 'requirements.lock'):
        files['scripts/requirements-commands.' + name.split('.')[-1]] = (PACKAGE / 'requirements' / name).read_bytes()
    for name in ('help.md', 'version.md', 'run.md'):
        files['commands/' + name] = (PACKAGE / 'templates/commands' / (name + '.tmpl')).read_bytes()
    for path in (PACKAGE / "templates" / backend).iterdir():
        data = path.read_text().replace("@DESCRIPTION_JSON@", json.dumps(description))
        files["scripts/" + path.name] = data.encode()
    if backend == "ai-sdk":
        runtime_directory = PACKAGE / "scripts/ai-runtime"
        for name in ("package.json", "package-lock.json", "tsconfig.json", "config.ts", "harness.ts",
                     "inference.ts", "limits.ts", "profiles.json", "runtime.test.ts"):
            files["scripts/" + name] = (runtime_directory / name).read_bytes()
    guide = (PACKAGE / "templates/tool.md.tmpl").read_text()
    replacements = {"@ENTRYPOINT@": f"scripts/run.{suffix}", "@WORKFLOW@": f"scripts/workflow.{suffix}",
        "@SETUP@": "# From this skill directory; Python 3.11+; no package install." if backend == "python" else
                    "# From this skill directory; Node 24+.\nnpm --prefix scripts ci",
        "@INVOKE@": f"{runtime} scripts/run.{suffix} --input /path/to/input.json"}
    for key, value in replacements.items():
        guide = guide.replace(key, value)
    files["references/tool.md"] = guide.encode()
    return files
