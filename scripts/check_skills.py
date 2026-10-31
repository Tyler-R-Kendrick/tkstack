#!/usr/bin/env python3
"""Read-only conformance gate for every owned normalized skill and its artifacts."""

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('owned_skill_checker', ROOT / 'skills/learn/skills/skillify/scripts/skillify.py')
skillify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skillify)
sys.path.insert(0, str(ROOT / 'scripts'))
from skill_roots import all_packages, owned, subskills  # noqa: E402


def check(root=ROOT, jobs=4):
    root = Path(root).resolve(strict=True)
    plugins = skillify.codify.parse_json((root / '.claude-plugin/marketplace.json').read_text())['plugins']
    # Root skills publish as plugins; subskills ship inside their parent's plugin.
    if {plugin['name'] for plugin in plugins} != set(all_packages(root)):
        raise ValueError('Marketplace and owned skill inventory disagree')
    published = {plugin['name']: plugin for plugin in plugins}
    packages = owned(root)
    runtime = (root / 'skills/learn/skills/codify/scripts/package_runtime.py').read_bytes()
    json_reader = (root / 'skills/learn/skills/codify/scripts/json_contract.py').read_bytes()
    state = (root / 'scripts/tkstack_state.py').read_bytes()
    def inspect(name):
        directory = packages[name]
        plugin = published.get(name)
        for helper, expected in (('package_runtime.py', runtime), ('json_contract.py', json_reader), ('tkstack_state.py', state)):
            if (directory / 'scripts' / helper).read_bytes() != expected:
                raise ValueError('Shared source drift in ' + name + '/' + helper)
        result = skillify.validate(directory, require_tool=True, entrypoint='scripts/run.py')
        identity = skillify.codify.command_schema.package_identity(directory)
        if plugin is not None and (plugin['version'] != identity['version'] or plugin['description'] != identity['description']):
            raise ValueError('Marketplace metadata drift for ' + name)
        model = skillify.codify.parse_json((directory / 'scripts/contract.json').read_text())
        if model['name'] != name:
            raise ValueError('Wrong skill contract model')
        _, validator = skillify.codify.command_schema.schema_libraries()
        validator.check_schema(model['facts_schema'])
        generated = skillify.normalize(directory, directory / 'scripts/contract.json', skillify.codify, dry_run=True)
        if generated['changed'] or generated['removed']:
            raise ValueError('Generated skill contract drift for ' + name + '; review Skillify normalize --dry-run')
        commands = skillify.codify.command_schema.catalog(directory)
        paths = {tuple(item['cli']['path']) for item in commands}
        if not {('help',), ('version',), ('model',), ('verify',)} <= paths:
            raise ValueError('Missing standard command surface for ' + name)
        mounts = {item['cli']['path'][0]: item['run']['skill'] for item in commands if 'skill' in item['run']}
        if mounts != {child: 'skills/' + child for child in subskills(directory)}:
            raise ValueError('Every packaged subskill of ' + name + ' needs exactly one mount command')
        if any(item['run'] != {'artifact': 'scripts/workflow.lock.json'} for item in commands
               if item['cli']['path'][0] not in ('help', 'version') and 'skill' not in item['run']):
            raise ValueError('Owned execution must use its reviewed shared artifact')
        skillify.codify.check(directory / 'scripts/workflow.lock.json')
        task_file = root / 'evals' / name / 'tasks.json'
        tasks = skillify.codify.parse_json(task_file.read_text())
        if not tasks.get('reviewed') or {task['split'] for task in tasks['tasks']} != {'train', 'val', 'test'}:
            raise ValueError('Missing reviewed split decision suite for ' + name)
        return {'skill': name, 'parent': None if plugin else directory.parent.parent.name, 'version': identity['version'], 'commands': result['commands'],
                'contract_criteria': len(model['criteria']), 'native_bindings': len(model.get('native', {})),
                'decision_cases': len(tasks['tasks']), 'artifact': 'current'}
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(inspect, sorted(packages)))


if __name__ == '__main__':
    try:
        rows = check()
        print(json.dumps({'status': 'pass', 'skills': len(rows), 'results': rows,
                          'limits': 'Conformance is not a semantic/model-quality score or native provider activation proof.'}, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('skills: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
