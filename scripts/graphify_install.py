"""Generate native Graphify skill views while retaining exact upstream snapshots."""
import json
from pathlib import Path
import re
import shlex
import sys
import tempfile


def view_directory(root, source, harness=None):
    return root / '.tkstack/skill-views' / source / (harness or 'default')


def render(root, source, profile, destination):
    upstream = root / 'vendor' / source
    text = (upstream / profile['entrypoint']).read_text()
    text = text.replace('graphify-out', '.tkstack/graphify').replace('~/.graphify', '.tkstack/graphify')
    python = shlex.quote(str(destination / 'scripts/python'))
    setup = '''### Step 1 - Use tkstack's pinned runtime

Do not install or upgrade a global runtime. This view uses the managed locked
Graphify installation and its scoped `.tkstack/graphify/` output. Run from the
workspace root. Missing runtime is an error: install it through the toolkit's
`setup_integrations.py --target . --install-runtimes --runtime graphify`.
All temporary session evidence belongs in `.tkstack/sessions/<session>/`.

```bash
''' + python + ''' -c "from pathlib import Path; import sys; from graphify.paths import out_path; out_path('.graphify_python').write_text(sys.argv[1],encoding='utf-8'); out_path('.graphify_root').write_text(str(Path(sys.stdin.readline().rstrip('\\n')).resolve()),encoding='utf-8')" ''' + python + ''' <<'GRAPHIFY_ROOT_EOF'
INPUT_PATH
GRAPHIFY_ROOT_EOF
```

For subsequent Python commands, use the interpreter launcher recorded in
`.tkstack/graphify/.graphify_python`. It selects the pinned interpreter and
sets GRAPHIFY_OUT for each invocation. Graph extraction may use inference for
non-code content; preserve explicit provider/budget selection. This installer
does not enable Codex multi_agent or start semantic extraction. Native install,
uninstall, and global commands are unavailable through the managed launcher:
use tkstack's installer and explicit .tkstack graphs/MCP project_path instead.
GitHub clone defaults use .tkstack/graphify/repos rather than home.

'''
    text, count = re.subn(r'### Step 1 -[^\n]*\n.*?(?=### Step 2 -)', lambda _: setup, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Graphify source layout changed; review its native setup before adapting')
    cli = shlex.join([sys.executable, str(root / 'scripts/tool.py'), 'graphify'])
    def commands(content):
        return re.sub(r'(?<![\w/.$-])graphify (?=(?:query|path|explain|extract|update|tree|merge-graphs|merge-chunks|merge-semantic|cache-check|check-update|benchmark|clone|export|hook-guard|hook-check|global|add|watch)\b)', lambda _: cli + ' ', content)
    files = {'SKILL.md': commands(text).encode()}
    for path in sorted((upstream / profile['references']).glob('*.md')):
        files['references/' + path.name] = commands(path.read_text().replace('graphify-out', '.tkstack/graphify').replace('~/.graphify', '.tkstack/graphify')).encode()
    for name in ('LICENSE', 'LICENSE-MIT', 'NOTICE'):
        files[name] = (upstream / name).read_bytes()
    files['scripts/python'] = ('#!' + sys.executable + '\nimport os,sys\nos.execv(sys.executable,[sys.executable,' +
        repr(str(root / 'scripts/graphify_adapter.py')) + ',*sys.argv[1:]])\n').encode()
    return files


def prepare_views(root):
    path = root / 'sources.lock.json'
    if not path.is_file():
        return
    for source, record in json.loads(path.read_text())['sources'].items():
        for harness, profile in record.get('skill_templates', {}).items():
            directory = view_directory(root, source, harness) / 'graphify'
            files = render(root, source, profile, directory)
            for name, data in files.items():
                target = directory / name
                if any(parent.is_symlink() for parent in (target, *target.parents) if parent != root.parent):
                    raise ValueError('Graphify generated resources must not be symlinks')
                target.parent.mkdir(parents=True, exist_ok=True)
                expected_mode = 0o755 if name == 'scripts/python' else 0o644
                if not target.exists() or target.read_bytes() != data or target.stat().st_mode & 0o777 != expected_mode:
                    temporary = None
                    try:
                        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.graphify-', delete=False) as stream:
                            temporary = Path(stream.name)
                            stream.write(data)
                        temporary.chmod(expected_mode)
                        temporary.replace(target)
                    finally:
                        if temporary is not None:
                            temporary.unlink(missing_ok=True)


def check_views(root):
    path = root / 'sources.lock.json'
    if not path.is_file():
        return
    for source, record in json.loads(path.read_text())['sources'].items():
        for harness, profile in record.get('skill_templates', {}).items():
            directory = view_directory(root, source, harness) / 'graphify'
            for name, data in render(root, source, profile, directory).items():
                target = directory / name
                expected_mode = 0o755 if name == 'scripts/python' else 0o644
                if target.is_symlink() or not target.is_file() or target.read_bytes() != data or target.stat().st_mode & 0o777 != expected_mode:
                    raise ValueError('Graphify generated view is missing or stale; rerun install.py: ' + str(target))
