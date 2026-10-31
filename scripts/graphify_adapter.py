#!/usr/bin/env python3
"""Use the pinned Graphify interpreter and keep generated state in scoped .tkstack."""
import json
import os
from pathlib import Path
import subprocess
import sys
import re
sys.dont_write_bytecode = True
from tkstack_state import ensure_state, state_container, state_path

ROOT = Path(__file__).resolve().parent.parent


def managed_arguments(root, args):
    args = list(args)
    if args and args[0] in ('install', 'uninstall', 'global'):
        raise ValueError('Use tkstack installation for managed files; native global graph storage is not managed. Use explicit .tkstack graphs or MCP project_path instead.')
    if len(args) >= 2 and args[0] == 'clone' and '--out' not in args:
        match = re.fullmatch(r'https?://github.com/([A-Za-z0-9_-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?', args[1])
        if match and match[2] not in ('.', '..'):
            destination = state_path('graphify') / 'repos' / match[1] / match[2]
            ensure_state(destination.parent)
            args += ['--out', str(destination)]
    return args


def runtime_environment(root, args=(), initialize=False):
    environment = dict(os.environ)
    output = Path(environment['GRAPHIFY_OUT']).expanduser().absolute() if environment.get('GRAPHIFY_OUT') else state_path('graphify')
    if args and args[0] == 'extract' and not environment.get('GRAPHIFY_OUT') and not environment.get('TKSTACK_WORKSPACE_DIR'):
        base = Path(args[1]).expanduser() if len(args) > 1 and not args[1].startswith('-') else Path.cwd()
        if not base.is_absolute():
            base = Path.cwd() / base
        if not base.exists():
            raise ValueError('Graphify extraction target must exist')
        if base.is_file():
            base = base.parent
        for index, argument in enumerate(args):
            if argument in ('--out', '--output') and index + 1 < len(args):
                base = Path(args[index + 1]).expanduser()
            elif argument.startswith(('--out=', '--output=')):
                base = Path(argument.split('=', 1)[1]).expanduser()
        if not base.is_absolute():
            base = Path.cwd() / base
        output = state_path('graphify', project=base)
    state_container(output)
    if initialize or (args and args[0] in ('extract', 'update', 'add', 'merge-graphs', 'build', 'cluster', 'cache-check', 'merge-chunks', 'merge-semantic')):
        ensure_state(output)
    environment['GRAPHIFY_OUT'] = str(output)
    environment['GRAPHIFY_NO_AUTO_REFRESH'] = '1'
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    return environment


def main():
    try:
        tool = json.loads((ROOT / 'harnesses/integrations.json').read_text())['tools']['graphify']
        from python_runtime import package_ready
        if not package_ready(ROOT, 'graphify', tool):
            raise ValueError('Graphify runtime unavailable; run setup_integrations.py --target . --install-runtimes --runtime graphify')
        python = ROOT / '.tkstack/runtime/graphify/bin/python'
        return subprocess.run([str(python), '-B', *sys.argv[1:]], env=runtime_environment(ROOT, initialize=True)).returncode
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 127


if __name__ == '__main__':
    raise SystemExit(main())
