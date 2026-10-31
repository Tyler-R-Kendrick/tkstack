"""Install a hash-locked Python runtime without touching home or system packages."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
from tkstack_state import ensure_state


def package_ready(root, name, tool, require_receipt=True):
    directory = root / '.tkstack/runtime' / name
    recipe = root / tool['recipe']
    try:
        if directory.is_symlink():
            return False
        executable = directory / 'bin' / tool['bin']
        if not executable.is_file() or not os.access(executable, os.X_OK):
            return False
        if require_receipt:
            receipt = json.loads((directory / '.tkstack-runtime.json').read_text())
            if receipt != {'package': tool['package'], 'version': tool['version'],
                           'requirements_sha256': hashlib.sha256((recipe / 'requirements.lock').read_bytes()).hexdigest()}:
                return False
            if any((directory / filename).read_bytes() != (recipe / filename).read_bytes()
                   for filename in ('requirements.in', 'requirements.lock')):
                return False
        result = subprocess.run([str(directory / 'bin/python'), '-B', '-c',
            'import importlib.metadata,json,sys;print(json.dumps({"version":importlib.metadata.version(sys.argv[1]),"python":"%s.%s"%sys.version_info[:2]}))',
            tool['package']], capture_output=True, text=True, check=True, timeout=10)
        return json.loads(result.stdout) == {'version': tool['version'], 'python': tool['python_version']}
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return False


def install(root, name, tool):
    if package_ready(root, name, tool):
        return
    uv = shutil.which('uv')
    if not uv:
        raise ValueError(f'{name}: uv is required for its hash-locked runtime')
    parent = ensure_state(root / '.tkstack/runtime')
    destination = parent / name
    lock = parent / ('.' + name + '-install.lock')
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError(f'{name}: another installation owns {lock}') from error
    created = False
    try:
        if destination.exists() or destination.is_symlink():
            raise ValueError(f'{name}: preserve or remove the existing differing runtime before reinstalling: {destination}')
        destination.mkdir()
        created = True
        environment = {**os.environ, 'UV_CACHE_DIR': str(ensure_state(root / '.tkstack/cache/uv')),
                       'UV_PYTHON_INSTALL_DIR': str(parent / 'python'), 'PYTHONDONTWRITEBYTECODE': '1'}
        subprocess.run([uv, 'venv', '--python', tool['python_version'], '--no-project', str(destination)],
                       env=environment, check=True, timeout=300)
        subprocess.run([uv, 'pip', 'sync', '--python', str(destination / 'bin/python'), '--require-hashes',
                        '--only-binary', ':all:', str(root / tool['recipe'] / 'requirements.lock')],
                       env=environment, check=True, timeout=600)
        if not package_ready(root, name, tool, require_receipt=False):
            raise ValueError(f'{name}: installed package failed native version/interpreter verification')
        for filename in ('requirements.in', 'requirements.lock'):
            shutil.copyfile(root / tool['recipe'] / filename, destination / filename)
        receipt = {'package': tool['package'], 'version': tool['version'],
                   'requirements_sha256': hashlib.sha256((destination / 'requirements.lock').read_bytes()).hexdigest()}
        temporary = destination / '.tkstack-runtime.pending'
        temporary.write_text(json.dumps(receipt, sort_keys=True) + '\n')
        temporary.replace(destination / '.tkstack-runtime.json')
    except BaseException:
        if created:
            shutil.rmtree(destination)
        raise
    finally:
        lock.rmdir()
    print(f"Installed {name} {tool['version']} from its Python requirement hashes")
