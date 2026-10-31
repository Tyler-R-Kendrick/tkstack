"""Generate private CLI shims and ownership-checked shell startup pointers."""
import hashlib
from pathlib import Path
import shlex
import shutil
import sys
from tkstack_state import ensure_state

BEGIN, END = '# tkstack:path:start', '# tkstack:path:end'
ALIASES = {'tkstack': ('tkstack',), 'rtk': ('rtk',), 'hf': ('higgsfield',), 'higgsfield': ('higgsfield',),
           'codify': ('codify',), 'skillify': ('skillify',), 'impeccable': ('impeccable',), 'headroom': ('headroom',), 'wikiskill': ('wikiskill',),
           'open-design': ('open-design',), 'openwiki': ('openwiki',), 'graphify': ('graphify',),
           'graphify-mcp': ('graphify', 'mcp')}


def shell_plan(root, target, scope, enabled=True):
    if not enabled or scope != 'home':
        return []
    env_file = root / '.tkstack/bootstrap/env.sh'
    owner = '# tkstack:path:source ' + hashlib.sha256(str(root).encode()).hexdigest()[:16]
    block = '\n'.join([BEGIN, owner, '[ ! -r ' + shlex.quote(str(env_file)) + ' ] || . ' + shlex.quote(str(env_file)), END])
    login = next((target / name for name in ('.bash_profile', '.bash_login') if (target / name).exists()), target / '.profile')
    result = []
    for path in (target / '.bashrc', login):
        if path.is_symlink():
            raise ValueError('Shell startup is managed through a symlink; use --no-shell and source ' + str(env_file) + ' in its owning dotfiles manager')
        before = path.read_text() if path.exists() else ''
        if before.count(BEGIN) != before.count(END) or before.count(BEGIN) > 1:
            raise ValueError('Malformed tkstack shell markers in ' + str(path))
        if BEGIN in before:
            start, end = before.index(BEGIN), before.index(END) + len(END)
            if end <= start or owner not in before[start:end]:
                raise ValueError('Shell block belongs to another checkout: ' + str(path))
            after = before[:start] + block + before[end:]
        else:
            after = before + ('\n' if before and not before.endswith('\n') else '') + block + '\n'
        if before != after:
            result.append((path, before, after))
    return result


def apply_shell(plan):
    for path, before, _ in plan:
        if (path.read_text() if path.exists() else '') != before:
            raise ValueError('Shell file changed during setup: ' + str(path))
    for path, _, after in plan:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(after)


def alias_text(root, arguments):
    if arguments == ('tkstack',):
        from runner_install import launcher_text
        return launcher_text(root)
    return ('#!' + sys.executable + '\nimport os,sys\nos.execv(sys.executable,' +
            repr([sys.executable, '-B', str(root / 'scripts/tool.py'), *arguments]) + '+sys.argv[1:])\n')


def check(root):
    for name, arguments in ALIASES.items():
        path = root / '.tkstack/bin' / name
        if path.is_symlink() or not path.is_file() or path.read_text() != alias_text(root, arguments) or path.stat().st_mode & 0o777 != 0o755:
            raise ValueError('Private command shim is missing or stale: ' + str(path))
    if not (root / '.tkstack/bootstrap/env.sh').is_file():
        raise ValueError('Bootstrap environment file is missing')


def publish(root, environment):
    directory = ensure_state(root / '.tkstack/bin')
    for name, arguments in ALIASES.items():
        target = directory / name
        text = alias_text(root, arguments)
        if target.is_symlink():
            raise ValueError('Private command must not be a symlink: ' + str(target))
        target.write_text(text)
        target.chmod(0o755)
    # A toolchain probe omits our shim directory, so these cannot recurse into themselves.
    for name in ('node', 'npm', 'uv'):
        executable = shutil.which(name, path=environment.get('PATH'))
        if executable:
            if Path(executable).parent == directory:
                raise ValueError('Refusing a recursive private toolchain shim')
            target = directory / name
            if target.is_symlink():
                raise ValueError('Private command must not be a symlink')
            target.write_text('#!' + sys.executable + '\nimport os,sys\nos.execv(' + repr(executable) + ',[' + repr(executable) + ']+sys.argv[1:])\n')
            target.chmod(0o755)
    env_file = ensure_state(root / '.tkstack/bootstrap') / 'env.sh'
    prefix = shlex.quote(str(directory))
    env_file.write_text('# Generated tkstack command environment; no credentials.\ncase ":${PATH-}:" in\n  *:' + prefix + ':*) ;;\n  *) PATH=' + prefix + ':"${PATH-}"; export PATH ;;\nesac\n')
    return env_file
