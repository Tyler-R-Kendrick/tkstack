"""Give host-launched tools private prerequisites without changing caller credentials."""
import json
import os
from pathlib import Path


def with_paths(root, environment=None):
    result = dict(os.environ if environment is None else environment)
    paths = [root / '.tkstack/bin']
    recipe = root / 'harnesses/bootstrap/toolchains.json'
    if recipe.is_file():
        version = json.loads(recipe.read_text())['node_version']
        paths.extend([root / '.tkstack/runtime/toolchains' / ('node-' + version) / 'bin', root / '.tkstack/runtime/toolchains/uv/bin'])
    prefix = [str(path) for path in paths if path.is_dir()]
    inherited = result.get('PATH', '').split(os.pathsep)
    result['PATH'] = os.pathsep.join(dict.fromkeys([*prefix, *inherited]))
    return result
