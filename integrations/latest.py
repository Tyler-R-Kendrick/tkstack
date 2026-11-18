"""Prepare current upstream sources and tool runtimes for dotfiles installs."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, ExitStack
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import posixpath
import re
import shutil
import shlex
import subprocess
import tarfile
import tempfile
import urllib.request
from types import SimpleNamespace


NODE_PACKAGES = ("@interfere/landmines", "oxlint", "@playwright/mcp", "firecrawl-mcp", "firecrawl", "openwiki", "@openai/codex")
NODE_MANIFEST = {'private': True, 'dependencies': {name: 'latest' for name in NODE_PACKAGES},
                 'overrides': {'firecrawl-mcp': {'firecrawl': '$firecrawl'}}}
PYTHON_PACKAGES = {
    "command-schema": ("PyYAML", "jsonschema"),
    "graphify": ("graphifyy[mcp]",),
    "headroom": ("headroom-ai",),
    "serena": ("serena-agent",),
}


def run(argv, *, cwd=None, env=None, timeout=240):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise ValueError(f"{argv[0]} failed: {(result.stderr or result.stdout).strip()[-1200:]}")
    return result.stdout


@contextmanager
def update_lock(root):
    parent = root / '.tkstack/locks'
    parent.mkdir(parents=True, exist_ok=True)
    lock = parent / 'dotfiles-update.lock'
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError(f'Another dotfiles update is using {lock}') from error
    try:
        yield
    finally:
        lock.rmdir()


def below(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def selected_files(files, source):
    selected = set(source['files']) & set(files)
    placements = [source.get('paths', {})] + list(source.get('harness_paths', {}).values())
    for paths in placements:
        skills = paths.get('skills', 'skills')
        if skills is not None:
            for file in files:
                if (file == 'SKILL.md' or file.endswith('/SKILL.md')) and (skills == '.' or below(file, skills)):
                    directory = str(PurePosixPath(file).parent)
                    selected.update(item for item in files if directory == '.' or below(item, directory))
        for kind in ('agents', 'rules'):
            directory = paths.get(kind, kind)
            if directory is not None:
                selected.update(item for item in files if below(item, directory)
                                and len(PurePosixPath(item).parts) == len(PurePosixPath(directory).parts) + 1)
    if source.get('repository') == 'https://github.com/microsoft/SkillOpt':
        selected.update(item for item in files if below(item, 'skillopt_sleep'))
    return sorted(selected)


def safe_relative(value):
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in ('', '.', '..') for part in path.parts):
        raise ValueError(f'Invalid upstream path: {value}')
    return path


def validate_repository(url):
    if not url.startswith('https://github.com/') or not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', url):
        raise ValueError(f'Unsupported upstream repository: {url}')


def source_receipt(url, revision, source):
    selection = {key: source.get(key) for key in ('path', 'paths', 'harness_paths', 'skill_templates')}
    selection['files'] = sorted(source.get('files', {}))
    digest = hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest()
    return {'repository': url, 'revision': revision, 'selection': digest}


def source_group(url, entries, clone_dir, output):
    validate_repository(url)
    run(['git', 'clone', '--quiet', '--depth', '1', '--filter=blob:limit=100k', '--no-checkout', url + '.git', str(clone_dir)])
    revision = run(['git', '-C', str(clone_dir), 'rev-parse', 'HEAD']).strip()
    tree = subprocess.check_output(['git', '-C', str(clone_dir), 'ls-tree', '-rz', '--full-tree', 'HEAD'])
    files = []
    for item in tree.split(b'\0'):
        if not item:
            continue
        meta, name = item.split(b'\t', 1)
        if meta.split()[1] == b'blob':
            files.append(name.decode('utf-8'))
    result = {}
    for name, source in entries:
        prefix = '' if source['path'] == '.' else str(safe_relative(source['path'])) + '/'
        relative = [item[len(prefix):] for item in files if item.startswith(prefix)]
        selected = selected_files(relative, source)
        if not selected:
            raise ValueError(f'{name}: current upstream contains no selected files')
        for path in selected:
            safe_relative(path)
        run(['git', '-C', str(clone_dir), 'checkout', '--quiet', 'HEAD', '--', *[prefix + p for p in selected]])
        target = output / name
        for path in selected:
            original = clone_dir / (prefix + path)
            destination = target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if original.is_symlink():
                link = os.readlink(original)
                if os.path.isabs(link) or not (destination.parent / link).resolve().is_relative_to(target.resolve()):
                    raise ValueError(f'{name}: upstream symlink escapes its source: {path}')
                destination.symlink_to(link)
            else:
                shutil.copy2(original, destination)
        result[name] = source_receipt(url, revision, source)
    return result


def prepare_sources(root):
    sources = json.loads((root / 'sources.lock.json').read_text())['sources']
    view_hash = hashlib.sha256()
    for path in ('skills/skills.json', 'scripts/install.py', 'integrations/latest.py'):
        data = (root / path).read_bytes() if (root / path).is_file() else b''
        view_hash.update(len(data).to_bytes(8, 'big') + data)
    view_digest = view_hash.hexdigest()
    parent = root / '.tkstack/cache/upstreams'
    parent.mkdir(parents=True, exist_ok=True)
    current = parent / 'current'
    if current.exists() and not current.is_symlink():
        raise ValueError(f'Refusing to replace upstream cache path: {current}')
    for source in sources.values():
        validate_repository(source['repository'])
    if current.is_dir():
        existing = current.resolve()
        if not existing.is_relative_to(parent.resolve()):
            raise ValueError(f'Upstream cache escapes its directory: {current}')
        receipt = json.loads((existing / 'sources.json').read_text())
        urls = sorted({source['repository'] for source in sources.values()})
        def head(url):
            return url, run(['git', 'ls-remote', url + '.git', 'HEAD']).split()[0]
        with ThreadPoolExecutor(max_workers=4) as pool:
            revisions = dict(pool.map(head, urls))
        if ((existing / 'views.sha256').is_file() and (existing / 'views.sha256').read_text().strip() == view_digest
                and set(receipt) == set(sources) and
                all(receipt[name] == source_receipt(source['repository'], revisions[source['repository']], source)
                    and (existing / 'sources' / name).is_dir() for name, source in sources.items())):
            return existing
    generation = Path(tempfile.mkdtemp(prefix='generation-', dir=parent))
    try:
        grouped = {}
        for name, source in sources.items():
            safe_relative(name)
            grouped.setdefault(source['repository'], []).append((name, source))
        output = generation / 'sources'
        output.mkdir()
        with tempfile.TemporaryDirectory(prefix='clones-', dir=parent) as clones:
            jobs = [(url, entries, Path(clones) / str(index), output)
                    for index, (url, entries) in enumerate(sorted(grouped.items()))]
            with ThreadPoolExecutor(max_workers=4) as pool:
                parts = list(pool.map(lambda args: source_group(*args), jobs))
        revisions = {name: data for part in parts for name, data in part.items()}
        (generation / 'sources.json').write_text(json.dumps(revisions, indent=2, sort_keys=True) + '\n')
        (generation / 'views.sha256').write_text(view_digest + '\n')
        return generation
    except BaseException:
        shutil.rmtree(generation, ignore_errors=True)
        raise


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'tkstack'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def latest_node():
    releases = json.loads(get('https://nodejs.org/dist/index.json'))
    version = next((item['version'] for item in releases if re.fullmatch(r'v\d+\.\d+\.\d+', item['version'])), None)
    system = {'Linux': 'linux', 'Darwin': 'darwin'}.get(platform.system())
    arch = {'x86_64': 'x64', 'amd64': 'x64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(platform.machine().lower())
    if not version or not system or not arch:
        raise ValueError('No current Node.js binary is available for this platform')
    return version, f'node-{version}-{system}-{arch}'


def install_node(parent, release):
    version, stem = release
    asset = stem + '.tar.gz'
    base = f'https://nodejs.org/dist/{version}/'
    checksums = get(base + 'SHASUMS256.txt').decode().splitlines()
    expected = next((line.split()[0] for line in checksums if len(line.split()) == 2 and line.split()[1] == asset), None)
    data = get(base + asset)
    if not expected or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'Node.js release checksum mismatch for {asset}')
    import io
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        members = archive.getmembers()
        for member in members:
            name = PurePosixPath(member.name)
            if (name.is_absolute() or not name.parts or name.parts[0] != stem or '..' in name.parts
                    or not (member.isfile() or member.isdir() or member.issym() or member.islnk())):
                raise ValueError('Unsafe Node.js release archive')
            if member.issym() or member.islnk():
                link = member.linkname if member.islnk() else posixpath.join(str(name.parent), member.linkname)
                normalized = PurePosixPath(posixpath.normpath(link))
                if normalized.is_absolute() or not normalized.parts or normalized.parts[0] != stem:
                    raise ValueError('Unsafe Node.js release link')
        try:
            archive.extractall(parent, filter='data')
        except TypeError:
            archive.extractall(parent)
    destination = parent / 'node-runtime'
    (parent / stem).rename(destination)
    if not (destination / 'bin/node').is_file() or not (destination / 'bin/npm').is_file():
        raise ValueError('Current Node.js release is missing node or npm')
    return destination


def latest_tag(repository):
    request = urllib.request.Request(f'https://github.com/{repository}/releases/latest', method='HEAD',
                                     headers={'User-Agent': 'tkstack'})
    with urllib.request.urlopen(request, timeout=30) as response:
        match = re.fullmatch(r'https://github\.com/' + re.escape(repository) + r'/releases/tag/([A-Za-z0-9_.-]+)', response.geturl())
    if not match:
        raise ValueError(f'{repository}: could not determine latest release')
    return match.group(1)


def binary_release(directory, repository):
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {'x86_64': 'x86_64', 'amd64': 'x86_64', 'aarch64': 'aarch64', 'arm64': 'aarch64'}.get(machine)
    if system not in ('linux', 'darwin') or not arch:
        raise ValueError(f'{repository}: no supported binary for {system}/{machine}')
    tag = latest_tag(repository)
    if repository == 'rtk-ai/rtk':
        target = f'{arch}-apple-darwin' if system == 'darwin' else f'{arch}-unknown-linux-' + ('musl' if arch == 'x86_64' else 'gnu')
        asset, executable, destination = f'rtk-{target}.tar.gz', 'rtk', 'rtk'
    else:
        asset = f'hf_{tag.removeprefix("v")}_{system}_{"amd64" if arch == "x86_64" else "arm64"}.tar.gz'
        executable, destination = 'hf', 'higgsfield'
    base = f'https://github.com/{repository}/releases/download/{tag}/'
    checksums = get(base + 'checksums.txt').decode().splitlines()
    expected = next((line.split()[0] for line in checksums if len(line.split()) == 2 and line.split()[1].lstrip('*') == asset), None)
    data = get(base + asset)
    if not expected or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'{repository}: release checksum mismatch for {asset}')
    import io
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        matches = [member for member in archive.getmembers() if member.isfile() and PurePosixPath(member.name).name == executable]
        if len(matches) != 1 or matches[0].size > 100 * 1024 * 1024:
            raise ValueError(f'{repository}: expected one executable in {asset}')
        stream = archive.extractfile(matches[0])
        if stream is None:
            raise ValueError(f'{repository}: missing executable in {asset}')
        path = directory / destination
        path.write_bytes(stream.read())
        path.chmod(0o755)
    return tag


def current_uv(root):
    tag = latest_tag('astral-sh/uv')
    safe_relative(tag)
    system = {'Linux': 'unknown-linux-gnu', 'Darwin': 'apple-darwin'}.get(platform.system())
    arch = {'x86_64': 'x86_64', 'amd64': 'x86_64', 'aarch64': 'aarch64', 'arm64': 'aarch64'}.get(platform.machine().lower())
    if not system or not arch:
        raise ValueError('No current uv binary is available for this platform')
    destination = root / '.tkstack/cache/uv-binaries' / tag / 'uv'
    if destination.is_file():
        return destination, tag
    stem = f'uv-{arch}-{system}'
    asset = stem + '.tar.gz'
    base = f'https://github.com/astral-sh/uv/releases/download/{tag}/'
    expected = get(base + asset + '.sha256').decode().split()[0]
    data = get(base + asset)
    if not re.fullmatch(r'[a-f0-9]{64}', expected) or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'uv release checksum mismatch for {asset}')
    import io
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        matches = [member for member in archive.getmembers() if member.name == stem + '/uv' and member.isfile()]
        if len(matches) != 1 or matches[0].size > 100 * 1024 * 1024:
            raise ValueError('The current uv release has no unique executable')
        stream = archive.extractfile(matches[0])
        if stream is None:
            raise ValueError('The current uv release has no executable')
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name('.uv-' + os.urandom(8).hex())
        try:
            temporary.write_bytes(stream.read())
            temporary.chmod(0o755)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    return destination, tag


def current_python(root, uv, env):
    names = {item.split('[', 1)[0] for packages in PYTHON_PACKAGES.values() for item in packages}
    def metadata(name):
        info = json.loads(get(f'https://pypi.org/pypi/{name}/json'))['info']
        version, required = info['version'], info.get('requires_python') or ''
        if not isinstance(version, str) or not re.fullmatch(r'[0-9A-Za-z][0-9A-Za-z.!+_-]*', version) or not isinstance(required, str):
            raise ValueError(f'{name}: invalid published Python metadata')
        return name, (version, required)
    with ThreadPoolExecutor(max_workers=4) as pool:
        versions = dict(pool.map(metadata, sorted(names)))
    result = {}
    for group, packages in PYTHON_PACKAGES.items():
        required = [versions[item.split('[', 1)[0]][1] for item in packages]
        constraint = ','.join(['>=3.11', *(item for item in required if item)])
        listing = json.loads(run([str(uv), 'python', 'list', '--only-downloads', '--output-format', 'json', constraint], env=env))
        available = [item['version'] for item in listing if item.get('implementation') == 'cpython'
                     and item.get('variant') == 'default' and re.fullmatch(r'\d+\.\d+\.\d+', item.get('version', ''))]
        if not available:
            raise ValueError(f'{group}: no supported Python is available for the latest packages ({constraint})')
        version = max(available, key=lambda item: tuple(map(int, item.split('.'))))
        requirements = [item + '==' + versions[item.split('[', 1)[0]][0] for item in packages]
        result[group] = {'version': version, 'requirements': requirements}
    for version in sorted({item['version'] for item in result.values()}):
        run([str(uv), 'python', 'install', '--no-bin', version], env=env)
    for item in result.values():
        item['python'] = run([str(uv), 'python', 'find', '--no-project', '--managed-python', item['version']], env=env).strip()
    return result


def python_runtime(directory, packages, env, uv, interpreter):
    run([str(uv), 'venv', '--python', interpreter, str(directory)], env=env)
    run([str(uv), 'pip', 'install', '--python', str(directory / 'bin/python'), '--upgrade', *packages], env=env)


def runtime_current(root, env, node_release, uv, uv_tag, python_releases):
    current = root / '.tkstack/runtime/current'
    if current.exists() and not current.is_symlink():
        raise ValueError(f'Refusing to replace runtime path: {current}')
    if not current.is_dir():
        return None
    runtime = current.resolve()
    if not runtime.is_relative_to((root / '.tkstack/runtime/versions').resolve()):
        raise ValueError(f'Runtime cache escapes its directory: {current}')
    try:
        if json.loads((runtime / 'node/package.json').read_text()) != NODE_MANIFEST:
            return None
        tags = json.loads((runtime / 'releases.json').read_text())
        node_bin = runtime / 'node-runtime/bin'
        python_versions = {name: data['version'] for name, data in python_releases.items()}
        if (tags.get('node') != node_release[0] or tags.get('uv') != uv_tag or
                tags.get('python') != python_versions or not (node_bin / 'node').is_file()):
            return None
        env = {**env, 'PATH': str(node_bin) + os.pathsep + env.get('PATH', '')}
        def check_python(item):
            name, release = item
            python = runtime / name / 'bin/python'
            if not python.is_file():
                return False
            command = [str(uv), 'pip', 'install', '--python', str(python), '--upgrade', '--dry-run', *release['requirements']]
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise ValueError(f'{name}: update check failed: {result.stderr[-800:]}')
            output = result.stdout + result.stderr
            return 'Would make no changes' in output
        def check_npm():
            command = [str(node_bin / 'npm'), 'outdated', '--prefix', str(runtime / 'node'), '--depth=0', '--json']
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=120)
            if result.returncode not in (0, 1):
                raise ValueError(f'npm update check failed: {result.stderr[-800:]}')
            return not json.loads(result.stdout or '{}')
        with ThreadPoolExecutor(max_workers=4) as pool:
            checks = list(pool.map(check_python, python_releases.items()))
        return runtime if (all(checks) and check_npm()
                           and all(tags.get(repo) == latest_tag(repo) for repo in ('rtk-ai/rtk', 'higgsfield-ai/cli'))
                           and all((runtime / path).is_file() for path in
                                   ('node/node_modules/.bin/oxlint', 'node/node_modules/.bin/openwiki',
                                    'graphify/bin/graphify-mcp', 'headroom/bin/headroom',
                                    'serena/bin/serena', 'bin/rtk', 'bin/higgsfield', 'bin/oxlint',
                                    'bin/landmines', 'bin/openwiki', 'bin/codex', 'bin/playwright-mcp', 'bin/firecrawl-mcp',
                                    'bin/graphify-mcp', 'bin/npm', 'bin/npx', 'bin/uv'))) else None
    except (OSError, json.JSONDecodeError):
        return None


def prepare_runtime(root):
    node_release = latest_node()
    env = os.environ.copy()
    env.update({'PIP_CACHE_DIR': str(root / '.tkstack/cache/pip'), 'UV_CACHE_DIR': str(root / '.tkstack/cache/uv'),
                'npm_config_cache': str(root / '.tkstack/cache/npm'),
                'UV_PYTHON_INSTALL_DIR': str(root / '.tkstack/runtime/python')})
    uv, uv_tag = current_uv(root)
    python_releases = current_python(root, uv, env)
    existing = runtime_current(root, env, node_release, uv, uv_tag, python_releases)
    if existing is not None:
        return existing
    parent = root / '.tkstack/runtime/versions'
    parent.mkdir(parents=True, exist_ok=True)
    generation = Path(tempfile.mkdtemp(prefix='generation-', dir=parent))
    try:
        node = generation / 'node'
        node.mkdir()
        (node / 'package.json').write_text(json.dumps(NODE_MANIFEST, indent=2) + '\n')
        binary = generation / 'bin'
        binary.mkdir()
        shutil.copy2(uv, binary / 'uv')
        def install_node_packages():
            node_home = install_node(generation, node_release)
            node_env = {**env, 'PATH': str(node_home / 'bin') + os.pathsep + env.get('PATH', '')}
            run([str(node_home / 'bin/npm'), 'install', '--prefix', str(node), '--package-lock=false', '--no-audit', '--no-fund'], env=node_env)
            scripts = {name: (node / 'node_modules/.bin' / name).resolve(strict=True)
                       for name in ('oxlint', 'openwiki', 'playwright-mcp', 'firecrawl-mcp', 'codex')}
            scripts.update({name: (node_home / 'bin' / name).resolve(strict=True) for name in ('npm', 'npx')})
            for name, script in scripts.items():
                wrapper = binary / name
                wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(str(node_home / 'bin/node')) + ' '
                                   + shlex.quote(str(script)) + ' "$@"\n')
                wrapper.chmod(0o755)
            landmines = binary / 'landmines'
            config = node / 'node_modules/@interfere/landmines/configs/recommended.json'
            landmines.write_text('#!/bin/sh\nexec ' + shlex.quote(str(binary / 'oxlint')) + ' --config '
                                 + shlex.quote(str(config)) + ' "$@"\n')
            landmines.chmod(0o755)
            return node_release[0]
        tasks = [(python_runtime, (generation / name, item['requirements'], env, uv, item['python']))
                 for name, item in python_releases.items()]
        tasks.extend([(install_node_packages, ()),
                      (binary_release, (binary, 'rtk-ai/rtk')),
                      (binary_release, (binary, 'higgsfield-ai/cli'))])
        def invoke(task):
            function, arguments = task
            return function(*arguments, **({'env': env} if function is run else {}))
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(invoke, tasks))
        (generation / 'releases.json').write_text(json.dumps({'node': results[-3], 'uv': uv_tag,
                                                               'python': {name: item['version'] for name, item in python_releases.items()},
                                                               'rtk-ai/rtk': results[-2],
                                                               'higgsfield-ai/cli': results[-1]}, indent=2) + '\n')
        for item in ('@interfere/landmines/configs/recommended.json', '@playwright/mcp/cli.js', 'firecrawl-mcp/dist/index.js', '.bin/oxlint', '.bin/openwiki'):
            if not (node / 'node_modules' / item).is_file():
                raise ValueError(f'Current npm runtime is missing {item}')
        for name, executable in (('graphify', 'graphify'), ('graphify', 'graphify-mcp'), ('headroom', 'headroom'), ('serena', 'serena')):
            if not (generation / name / 'bin' / executable).is_file():
                raise ValueError(f'Current {name} runtime is missing {executable}')
        graphify = binary / 'graphify-mcp'
        graphify.write_text('#!/bin/sh\nexec ' + shlex.quote(str(generation / 'graphify/bin/graphify-mcp')) + ' "$@"\n')
        graphify.chmod(0o755)
        return generation
    except BaseException:
        shutil.rmtree(generation, ignore_errors=True)
        raise


def publish(link, target):
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() and not link.is_symlink():
        raise ValueError(f'Refusing to replace runtime path: {link}')
    temporary = link.with_name('.' + link.name + '-' + os.urandom(8).hex())
    temporary.symlink_to(os.path.relpath(target, link.parent), target_is_directory=True)
    try:
        os.replace(temporary, link)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def apply_transaction(root, state, plan, stale, changes, restore_file):
    """Restore owned links and configuration if an update cannot finish."""
    pointers = [(state.source_generation, root / '.tkstack/cache/upstreams/current'),
                (state.runtime_generation, root / '.tkstack/runtime/current')]
    links = [(path, os.readlink(path) if path.is_symlink() else None, source)
             for source, path in [*plan, *((None, path) for path in stale), *pointers]]
    files = [(path, before, after, path.stat().st_mode & 0o7777 if path.exists() else None)
             for path, before, after in changes]
    try:
        yield
    except BaseException as error:
        gaps = []
        for path, before, after, mode in reversed(files):
            try:
                if path.is_symlink():
                    raise ValueError('configuration became a symlink')
                actual = path.read_text() if path.exists() else None
                if actual != before:
                    if actual != after:
                        raise ValueError('configuration changed during rollback')
                    restore_file(path, before)
                if mode is not None and path.exists():
                    path.chmod(mode)
            except (OSError, ValueError):
                gaps.append(str(path))
        for path, before, expected in reversed(links):
            try:
                actual = os.readlink(path) if path.is_symlink() else None
                if actual == before and (actual is not None or not path.exists()):
                    continue
                if expected is None:
                    if actual is not None or path.exists():
                        raise ValueError('removed link was replaced')
                elif actual is None or path.resolve() != expected.resolve():
                    raise ValueError('installed link was replaced')
                if before is None:
                    path.unlink()
                else:
                    temporary = path.with_name('.' + path.name + '-restore-' + os.urandom(8).hex())
                    try:
                        temporary.symlink_to(before)
                        os.replace(temporary, path)
                    finally:
                        temporary.unlink(missing_ok=True)
            except (OSError, ValueError):
                gaps.append(str(path))
        state.applied = bool(gaps)
        if gaps:
            raise ValueError(f'Update failed: {error}; could not restore: {", ".join(gaps)}') from error
        raise


def saved_generation(root, saved, name, base, allow_missing=False):
    value = saved.get(name)
    if value is None:
        return None
    path = Path(value).resolve()
    if not path.is_relative_to((root / base).resolve()):
        raise ValueError(f'Missing or invalid installed {name} generation: {path}')
    if not path.is_dir():
        if allow_missing:
            return None
        raise ValueError(f'Missing or invalid installed {name} generation: {path}')
    return path


def source_directories(root, kind, harness, upstreams, adopted, skill_view):
    lock = root / 'sources.lock.json'
    sources = (json.loads(lock.read_text())['sources'] if lock.is_file() else
               {path.name: {} for path in (root / 'vendor').glob('*') if path.is_dir()})
    result = []
    for name, source in sorted(sources.items()):
        if kind == 'skills' and source.get('skill_templates'):
            result.append((name, skill_view(root, name, harness, upstreams)))
            continue
        paths = {**source.get('paths', {}), **source.get('harness_paths', {}).get(harness, {})}
        relative = paths.get(kind, kind)
        if relative is not None:
            result.append((name, (upstreams / name if upstreams is not None else root / 'vendor' / name) / relative))
    if kind == 'skills':
        result.append(('adopted', root / adopted))
    result.append((None, root / kind))
    return result


def installed_tools(target, runtime, scope, saved):
    if runtime is None or scope != 'home':
        return []
    paths = {'node': runtime / 'node-runtime/bin/node', 'npm': runtime / 'bin/npm', 'npx': runtime / 'bin/npx', 'uv': runtime / 'bin/uv',
             'codex': runtime / 'bin/codex', 'oxlint': runtime / 'bin/oxlint', 'landmines': runtime / 'bin/landmines',
             'openwiki': runtime / 'bin/openwiki',
             'playwright-mcp': runtime / 'bin/playwright-mcp', 'firecrawl-mcp': runtime / 'bin/firecrawl-mcp',
             'graphify': runtime / 'graphify/bin/graphify', 'graphify-mcp': runtime / 'graphify/bin/graphify-mcp',
             'headroom': runtime / 'headroom/bin/headroom', 'serena': runtime / 'serena/bin/serena',
             'rtk': runtime / 'bin/rtk', 'higgsfield': runtime / 'bin/higgsfield'}
    links = []
    for name, path in paths.items():
        source = path.resolve()
        links.append((source, target / '.tkstack/bin' / name))
        destination = target / '.local/bin' / name
        old = saved.get('links', {}).get(destination.relative_to(target).as_posix())
        if (not (destination.exists() or destination.is_symlink()) or
                destination.is_symlink() and destination.resolve() in (source, Path(old) if old else source)):
            links.append((source, destination))
        else:
            print(f'Preserving existing {destination}; the current tool is in .tkstack/bin')
    return links


def recorded_tools(root, target, saved):
    """Find owned tool links even when their old generation was removed."""
    links = []
    for relative, old in saved.get('links', {}).items():
        path = PurePosixPath(relative)
        if (len(path.parts) != 3 or path.parts[-1] == '..' or
                path.parts[:2] not in (('.tkstack', 'bin'), ('.local', 'bin'))):
            continue
        source = Path(old)
        if source.is_absolute() and source.is_relative_to(root / '.tkstack/runtime/versions'):
            links.append((source, target / Path(*path.parts)))
    return links


def alias_migrations(root, target, harnesses, scope, aliases_by_source, skill_directories):
    def matches(destination, source):
        return destination.is_symlink() and destination.resolve() == source
    migrations = {}
    steering = target / '.agents/steering'
    for old in (root / 'steering', root / '.tkstack/steering'):
        if matches(steering, old.resolve()):
            migrations[steering] = old.resolve()
    for source, aliases in aliases_by_source.items():
        for path in (root / 'vendor' / source / 'skills').rglob('SKILL.md'):
            if path.parent.name in aliases:
                for harness in harnesses:
                    for relative in skill_directories(harness, scope):
                        migrations[target / relative / path.parent.name] = path.parent.resolve()
    if 'cursor' in harnesses:
        for rule in (root / '.cursor/rules').glob('*.mdc'):
            if not rule.is_symlink():
                migrations[target / '.cursor/rules' / rule.name] = (root / 'harnesses/cursor' / rule.name).resolve()
    return migrations


def receipt_migrations(root, target, saved):
    result = {}
    for relative, old in saved.get('links', {}).items():
        destination, source = target / relative, Path(old)
        if source.is_relative_to(root) and destination.is_symlink() and destination.resolve() == source:
            result[destination] = source
    return result


@contextmanager
def installation(root, target, scope, saved, args, verify_vendor, safe_path):
    state = SimpleNamespace(upstreams=None, runtime=None, source_generation=None, runtime_generation=None,
                            source_created=False, runtime_created=False, applied=False, committed=False, refresh=False)
    with ExitStack() as stack:
        try:
            state.refresh = (scope == 'home' and target != root and not (args.dry_run or args.check or args.status or args.uninstall)
                             and os.environ.get('TKSTACK_OFFLINE') != '1')
            allow_missing = state.refresh or args.uninstall
            state.upstreams = saved_generation(root, saved, 'upstreams', '.tkstack/cache/upstreams', allow_missing)
            state.runtime = saved_generation(root, saved, 'runtime', '.tkstack/runtime/versions', allow_missing)
            if not args.uninstall and not state.refresh:
                verify_vendor(root)
            if state.refresh:
                for path in (root / '.tkstack/cache', root / '.tkstack/runtime', root / '.tkstack/locks'):
                    safe_path(path, root)
                stack.enter_context(update_lock(root))
                print('Updating upstream sources and bundled tool runtimes...')
                old_source = root / '.tkstack/cache/upstreams/current'
                old_runtime = root / '.tkstack/runtime/current'
                old_source = old_source.resolve() if old_source.is_dir() else None
                old_runtime = old_runtime.resolve() if old_runtime.is_dir() else None
                state.source_generation = prepare_sources(root)
                state.source_created = state.source_generation != old_source
                state.upstreams = state.source_generation / 'sources'
                state.runtime_generation = prepare_runtime(root)
                state.runtime_created = state.runtime_generation != old_runtime
                state.runtime = state.runtime_generation
            elif scope == 'home' and args.dry_run:
                print('Would check for current upstream sources and provision bundled tools.')
            yield state
        finally:
            if not state.committed and not state.applied:
                for generation, created in ((state.source_generation, state.source_created),
                                            (state.runtime_generation, state.runtime_created)):
                    if generation is not None and created:
                        shutil.rmtree(generation, ignore_errors=True)


def finish_installation(root, state):
    if state.refresh:
        publish(root / '.tkstack/cache/upstreams/current', state.source_generation)
        publish(root / '.tkstack/runtime/current', state.runtime_generation)
    state.committed = True
