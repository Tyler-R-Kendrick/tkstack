"""Offline checks of supported dependency locks and immutable automation sources."""
import ast
import base64
import binascii
import json
from pathlib import PurePosixPath
import re

SHA = re.compile(r'^[0-9a-f]{40}$|^[0-9a-f]{64}$', re.I)
IMAGE = re.compile(r'^\S+@sha256:[0-9a-f]{64}$', re.I)
REQ = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9,._-]+\])?==[A-Za-z0-9][A-Za-z0-9.+_-]*(?:\s*;[^#]+?)?\s*(?=--hash=)')


def integrity(value):
    if not isinstance(value, str):
        return False
    for token in value.split():
        algorithm, separator, digest = token.partition('-')
        if not separator or algorithm not in ('sha256', 'sha384', 'sha512'):
            continue
        try:
            raw = base64.b64decode(digest, validate=True)
        except (ValueError, binascii.Error):
            continue
        if len(raw) == {'sha256': 32, 'sha384': 48, 'sha512': 64}[algorithm]:
            return True
    return False


def workflow(data, name):
    try:
        import yaml
    except ImportError as error:
        raise ValueError('Dependency checks need PyYAML: install the hash-locked command-schema requirements') from error

    class StrictLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            self.flatten_mapping(node)
            mapping = {}
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                if key in mapping:
                    raise ValueError('Duplicate YAML key in ' + name + ': ' + str(key))
                mapping[key] = self.construct_object(value_node, deep=deep)
            return mapping
    try:
        result = yaml.load(data, Loader=StrictLoader)
    except yaml.YAMLError as error:
        raise ValueError('Invalid workflow YAML in ' + name + ': ' + str(error)) from error
    if not isinstance(result, dict):
        raise ValueError('Expected a workflow/action mapping: ' + name)
    return result


def source_ok(ref):
    if not isinstance(ref, str) or not ref or '${{' in ref:
        return False
    if ref.startswith('./'):
        return '..' not in PurePosixPath(ref).parts
    if ref.startswith('docker://'):
        return bool(IMAGE.fullmatch(ref.removeprefix('docker://')))
    path, sep, rev = ref.rpartition('@')
    return bool(sep and '/' in path and SHA.fullmatch(rev))


def inspect(snapshot, execution=None):
    errors, warnings, metrics = [], [], {'npm_manifests': 0, 'npm_packages': 0, 'pip_locks': 0,
                                        'workflow_files': 0, 'action_sources': 0, 'container_sources': 0}
    def fail(rule, path, detail):
        errors.append({'rule': rule, 'path': path, 'detail': detail})
    files = [p for p in snapshot.files if not p.startswith('vendor/')]
    unsupported = {'npm-shrinkwrap.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock', 'uv.lock', 'Cargo.lock', 'go.sum', 'composer.lock', 'Gemfile.lock'}
    for name in files:
        if PurePosixPath(name).name in unsupported:
            fail('dependencies.unsupported-lock', name, 'Add a verified native lock adapter before relying on this dependency format.')
        elif name == 'package.json' or name.endswith('/package.json'):
            metrics['npm_manifests'] += 1
            package = snapshot.json(name)
            if not isinstance(package, dict):
                raise ValueError('Expected package object: ' + name)
            lock_name = str(PurePosixPath(name).parent / 'package-lock.json')
            if lock_name.startswith('./'):
                lock_name = lock_name[2:]
            if lock_name not in snapshot.files:
                fail('dependencies.npm-lock-missing', name, 'Provide a committed package-lock.json and install with npm ci.')
                continue
            lock = snapshot.json(lock_name)
            packages = lock.get('packages') if isinstance(lock, dict) else None
            if not isinstance(lock, dict) or lock.get('lockfileVersion') not in (2, 3) or not isinstance(packages, dict) or not isinstance(packages.get(''), dict):
                fail('dependencies.npm-lock-invalid', lock_name, 'Use a package-lock v2/v3 with a root package inventory.')
                continue
            for key in ('dependencies', 'devDependencies', 'optionalDependencies'):
                if not isinstance(package.get(key, {}), dict) or not isinstance(packages[''].get(key, {}), dict):
                    raise ValueError('npm dependency groups must be objects: ' + name)
                if package.get(key, {}) != packages[''].get(key, {}):
                    fail('dependencies.npm-manifest-drift', name + ':' + key, 'Regenerate the lock when direct dependencies change.')
            direct = set().union(*(package.get(key, {}) for key in ('dependencies', 'devDependencies', 'optionalDependencies')))
            for dependency in sorted(direct):
                if 'node_modules/' + dependency not in packages:
                    fail('dependencies.npm-missing-package', lock_name + ':' + dependency, 'Direct dependency is absent from the resolved lock inventory.')
            for key, item in sorted(packages.items()):
                if not key:
                    continue
                metrics['npm_packages'] += 1
                if not isinstance(item, dict):
                    fail('dependencies.npm-lock-invalid', lock_name + ':' + key, 'Package entry must be an object.')
                    continue
                if item.get('link') is True:
                    path = item.get('resolved')
                    if not isinstance(path, str) or path.startswith('/') or '..' in PurePosixPath(path).parts:
                        fail('dependencies.npm-local-escape', lock_name + ':' + key, 'Workspace links must stay within the repository.')
                    continue
                if not isinstance(item.get('version'), str) or not item['version'] or not integrity(item.get('integrity')):
                    fail('dependencies.npm-integrity', lock_name + ':' + key, 'Lock an exact resolved version and SHA-256/384/512 SRI digest.')
        elif name == 'requirements.lock' or name.endswith('/requirements.lock'):
            metrics['pip_locks'] += 1
            logical, pending = [], ''
            for line in snapshot.read(name).decode('utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                continued = line.endswith('\\')
                pending += line.removesuffix('\\').strip() + ' '
                if not continued:
                    logical.append(pending.strip())
                    pending = ''
            if pending:
                fail('dependencies.pip-lock-invalid', name, 'Incomplete continuation in requirements lock.')
            for number, line in enumerate(logical, 1):
                hashes = re.findall(r'--hash=([^\s]+)', line)
                if not REQ.match(line) or not hashes or any(not re.fullmatch(r'sha256:[0-9a-f]{64}', h, re.I) for h in hashes):
                    fail('dependencies.pip-integrity', name + ':' + str(number), 'Every requirement must use an exact version and SHA-256 hash.')
        elif ((name.startswith('.github/workflows/') and name.endswith(('.yml', '.yaml'))) or
              (name.startswith('.github/actions/') and name.endswith(('/action.yml', '/action.yaml')))):
            metrics['workflow_files'] += 1
            data = workflow(snapshot.read(name), name)
            jobs = data.get('jobs') if name.startswith('.github/workflows/') else None
            nodes = []
            if jobs is not None:
                if not isinstance(jobs, dict):
                    raise ValueError('Workflow jobs must be a mapping: ' + name)
                if execution and len(jobs) > execution['max_jobs']:
                    fail('execution.job-budget', name, 'Workflow exceeds the configured job budget.')
                for job, value in jobs.items():
                    if not isinstance(value, dict):
                        raise ValueError('Workflow job must be a mapping: ' + name)
                    if execution and 'uses' not in value:
                        timeout = value.get('timeout-minutes')
                        if type(timeout) is not int or timeout < 1 or timeout > execution['max_timeout_minutes']:
                            fail('execution.timeout-budget', name + ':' + str(job), 'Set a literal job timeout within the configured limit.')
                    nodes.append((str(job), value))
                    steps = value.get('steps', [])
                    if not isinstance(steps, list):
                        raise ValueError('Workflow steps must be an array: ' + name)
                    nodes.extend((str(job) + ':' + str(i + 1), step) for i, step in enumerate(steps))
            elif name.startswith('.github/actions/'):
                runs = data.get('runs', {})
                steps = runs.get('steps', []) if isinstance(runs, dict) else []
                if not isinstance(steps, list):
                    raise ValueError('Composite action steps must be an array: ' + name)
                nodes.extend((str(i + 1), step) for i, step in enumerate(steps))
            else:
                raise ValueError('Workflow is missing jobs: ' + name)
            for where, node in nodes:
                if not isinstance(node, dict):
                    raise ValueError('Workflow step must be a mapping: ' + name)
                if 'uses' not in node:
                    continue
                metrics['action_sources'] += 1
                if not source_ok(node['uses']):
                    fail('dependencies.action-pin', name + ':' + where, 'Pin remote actions to a full Git commit and Docker actions to a SHA-256 digest.')
        elif name == '.devcontainer/devcontainer.json':
            data = snapshot.json(name)
            if not isinstance(data, dict):
                raise ValueError('Devcontainer must be an object: ' + name)
            if 'image' in data:
                metrics['container_sources'] += 1
                if not isinstance(data['image'], str) or not IMAGE.fullmatch(data['image']):
                    fail('dependencies.container-digest', name + ':image', 'Pin the image to a SHA-256 OCI digest.')
            features = data.get('features', {})
            if not isinstance(features, dict):
                raise ValueError('Devcontainer features must be an object')
            for feature in features:
                metrics['container_sources'] += 1
                if not IMAGE.fullmatch(feature):
                    fail('dependencies.container-digest', name + ':features:' + feature, 'Pin the feature to a SHA-256 OCI digest.')
            if 'build' in data or 'dockerFile' in data:
                warnings.append({'rule':'dependencies.dockerfile-unchecked','path':name,'detail':'Dockerfile base images require a native Dockerfile adapter.'})
    # Recognize the current installer acquisition paths; this is not a shell parser.
    if 'scripts/install.py' in files:
        tree = ast.parse(snapshot.read('scripts/install.py'), filename='scripts/install.py')
        if any(isinstance(node, (ast.List, ast.Tuple))
               and any(isinstance(item, ast.Constant) and item.value == 'uvx' for item in node.elts)
               and any(isinstance(item, ast.Name) and item.id == 'SERENA_FROM' for item in node.elts)
               for node in ast.walk(tree)):
            warnings.append({'rule':'dependencies.runtime-unlocked','path':'scripts/install.py:serena',
                             'detail':'The installer uvx launch does not consume a verified transitive dependency lock.'})
    if 'install.sh' in files:
        shell = snapshot.read('install.sh').decode('utf-8')
        # The bootstrap uses a separately supplied digest and a fail-closed
        # comparison before tar reads the file. The archive fixtures exercise it.
        verified = shell.find('if [[ "$(file_sha256 "$archive")" != "$TKSTACK_TARBALL_SHA256" ]]; then')
        extracting = shell.find('if ! reject_archive_members "$archive"')
        if 'TKSTACK_TARBALL' in shell and not 0 <= verified < extracting:
            warnings.append({'rule':'dependencies.bootstrap-unverified','path':'install.sh:archive',
                             'detail':'Check the downloaded archive SHA-256 before extraction.'})
    # MCP executors can download packages without using the reviewed locks above.
    if 'mcp.json' in files:
        mcp = snapshot.json('mcp.json')
        if not isinstance(mcp, dict) or not isinstance(mcp.get('mcpServers'), dict):
            raise ValueError('Invalid MCP server document')
        for name, entry in sorted(mcp['mcpServers'].items()):
            if isinstance(entry, dict) and entry.get('command') in ('npx', 'uvx'):
                warnings.append({'rule':'dependencies.runtime-unlocked','path':'mcp.json:' + name,
                                 'detail':'This runtime fetch is not bound to an integrity-checked transitive dependency lock.'})
    return metrics, errors, warnings
