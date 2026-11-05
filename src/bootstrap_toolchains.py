"""Resolve startup prerequisites; missing Node/uv install privately from pinned recipes."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from tkstack_state import ensure_state


def version(command, environment):
    executable = shutil.which(command, path=environment.get('PATH'))
    if not executable:
        return None
    try:
        result = subprocess.run([executable, '--version'], env=environment, capture_output=True, text=True, check=True, timeout=10)
        found = re.search(r'(\d+)\.(\d+)\.(\d+)', result.stdout)
        return tuple(map(int, found.groups())) if found else None
    except (OSError, subprocess.SubprocessError):
        return None


def with_path(environment, directory):
    result = dict(environment)
    result['PATH'] = str(directory) + os.pathsep + result.get('PATH', '')
    return result


def resolve(root, environment=None, install=False):
    environment = dict(os.environ if environment is None else environment)
    environment['PATH'] = os.pathsep.join(part for part in environment.get('PATH', '').split(os.pathsep) if part != str(root / '.tkstack/bin'))
    recipe = json.loads((root / 'harnesses/bootstrap/toolchains.json').read_text())
    if sys.version_info[:2] < tuple(map(int, recipe['python_minimum'].split('.'))):
        raise ValueError('tkstack requires Python ' + recipe['python_minimum'] + '+')
    parent = root / '.tkstack/runtime/toolchains'
    private_uv = parent / 'uv/bin'
    private_node = parent / ('node-' + recipe['node_version']) / 'bin'
    for directory in (private_uv, private_node):
        if directory.is_dir():
            environment = with_path(environment, directory)
    uv_expected = tuple(map(int, recipe['uv_version'].split('.')))
    uv_ready = version('uv', environment) == uv_expected
    minimum_node = tuple(map(int, recipe['node_minimum'].split('.')))
    actual_node = version('node', environment)
    node_ready = actual_node is not None and actual_node >= minimum_node and bool(shutil.which('npm', path=environment.get('PATH')))
    if install and not uv_ready:
        ensure_state(parent)
        directory = parent / 'uv'
        if directory.exists():
            raise ValueError('Existing private uv environment differs; preserve/repair ' + str(directory))
        try:
            subprocess.run([sys.executable, '-m', 'venv', str(directory)], check=True, env=environment, timeout=120)
            subprocess.run([str(directory / 'bin/python'), '-m', 'pip', 'install', '--disable-pip-version-check', '--require-hashes',
                            '--only-binary=:all:', '-r', str(root / 'harnesses/bootstrap/requirements.lock')],
                           check=True, env={**environment, 'PIP_CACHE_DIR': str(root / '.tkstack/cache/pip')}, timeout=300)
            environment = with_path(environment, private_uv)
            uv_ready = version('uv', environment) == uv_expected
            if not uv_ready:
                raise ValueError('Installed uv does not match its pinned version')
        except BaseException:
            if directory.is_dir() and not directory.is_symlink():
                shutil.rmtree(directory)
            raise
    if install and not node_ready:
        machine = {'amd64': 'x86_64', 'arm64': 'aarch64'}.get(platform.machine().lower(), platform.machine().lower())
        key = platform.system().lower() + '-' + machine
        asset = recipe['node_platforms'].get(key)
        if not asset:
            raise ValueError('No pinned Node toolchain for ' + key + '; supply Node >= ' + recipe['node_minimum'])
        ensure_state(parent)
        destination = parent / ('node-' + recipe['node_version'])
        if destination.exists() or destination.is_symlink():
            raise ValueError('Existing private Node differs; preserve/repair ' + str(destination))
        with tempfile.TemporaryDirectory(prefix='.node-', dir=parent) as temporary:
            staging = Path(temporary)
            archive_path = staging / 'node.tar.gz'
            with urllib.request.urlopen(asset['url'], timeout=60) as response, archive_path.open('wb') as output:
                shutil.copyfileobj(response, output)
            if hashlib.sha256(archive_path.read_bytes()).hexdigest() != asset['sha256']:
                raise ValueError('Node archive checksum mismatch')
            if not hasattr(tarfile, 'data_filter'):
                raise ValueError('Private Node extraction needs Python 3.11.8+ or 3.12+; otherwise provide Node externally')
            with tarfile.open(archive_path, 'r:gz') as archive:
                # The validated distribution contains relative npm links; never extract outside staging.
                for member in archive.getmembers():
                    path = Path(member.name)
                    if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != asset['prefix']:
                        raise ValueError('Unexpected path in pinned Node archive')
                archive.extractall(staging, filter='data')
            (staging / asset['prefix']).rename(destination)
        environment = with_path(environment, private_node)
        actual_node = version('node', environment)
        node_ready = actual_node is not None and actual_node >= minimum_node and bool(shutil.which('npm', path=environment.get('PATH')))
        if not node_ready:
            raise ValueError('Installed Node/npm failed native version verification')
    return environment, {'python': {'status': 'available', 'version': '.'.join(map(str, sys.version_info[:3]))},
                         'uv': {'status': 'available' if uv_ready else 'missing', 'required': recipe['uv_version']},
                         'node': {'status': 'available' if node_ready else 'missing', 'minimum': recipe['node_minimum']}}
