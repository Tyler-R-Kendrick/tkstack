#!/usr/bin/env python3
"""Read-only, offline repository constraints. No test code is imported or executed."""
import argparse
import ast
import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
sys.dont_write_bytecode = True
from git_snapshot import GitSnapshot as Snapshot
from dependencies import inspect as inspect_dependencies
from boundaries import check as check_boundaries


def obj(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError(label + ' requires exactly: ' + ', '.join(fields))
    return value


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value or value.startswith('/') or '..' in PurePosixPath(value).parts:
        raise ValueError('Expected a repository-relative path or glob')
    return value


def integer(value):
    if type(value) is not int or value < 0:
        raise ValueError('Budgets must be nonnegative integers')
    return value


def selected(name, includes, excludes=()):
    return any(fnmatch.fnmatchcase(name, p) for p in includes) and not any(fnmatch.fnmatchcase(name, p) for p in excludes)


def test_inventory(snapshot, policy):
    files, findings, bodies = {}, [], {}
    patterns = policy['include']
    excludes = policy['exclude']
    for name in snapshot.files:
        if not selected(name, patterns, excludes):
            continue
        raw = snapshot.read(name)
        tree = ast.parse(raw, filename=name)
        tests = []
        for parent in ast.walk(tree):
            if not isinstance(parent, (ast.ClassDef, ast.Module)):
                continue
            for node in parent.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith('test_'):
                    continue
                identity = (parent.name + '.' if isinstance(parent, ast.ClassDef) else '') + node.name
                location = name + ':' + identity
                calls = [x for x in ast.walk(node) if isinstance(x, ast.Call)]
                assertions = [x for x in calls if isinstance(x.func, ast.Attribute) and x.func.attr.startswith(('assert', 'fail'))]
                bare = [x for x in ast.walk(node) if isinstance(x, ast.Assert)]
                flags = []
                if not assertions and not bare:
                    flags.append('no-oracle')
                for call in assertions:
                    args = call.args[:2] if call.func.attr in ('assertEqual', 'assertNotEqual', 'assertIs', 'assertIsNot', 'assertIn', 'assertNotIn') else call.args[:1]
                    if args and all(isinstance(arg, ast.Constant) for arg in args):
                        flags.append('constant-oracle')
                    if len(args) == 2 and ast.dump(args[0]) == ast.dump(args[1]):
                        flags.append('self-comparison')
                if any(isinstance(x.test, ast.Constant) for x in bare):
                    flags.append('constant-oracle')
                # A body is comparable only in the same fixture context and
                # with the same parameters and decorators. Other contexts may
                # exercise distinct behavior even when their assertions match.
                body = node.body[1:] if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str) else node.body
                signature = (parent, ast.dump(node.args, include_attributes=False),
                             tuple(ast.dump(item, include_attributes=False) for item in node.decorator_list),
                             ast.dump(ast.Module(body=body, type_ignores=[]), include_attributes=False))
                if signature in bodies:
                    flags.append('duplicate-body')
                else:
                    bodies[signature] = location
                for flag in sorted(set(flags)):
                    findings.append({'rule': 'tests.' + flag, 'path': location, 'line': node.lineno})
                tests.append(identity)
        files[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'tests': tests, 'bytes': len(raw)}
    return files, findings


def evaluate(snapshot, category='source', audit=False):
    config = snapshot.json('.constrain/config.json')
    if not isinstance(config, dict) or set(config) - {'version', 'tests', 'layout', 'artifacts', 'execution', 'documents', 'boundaries'} or not {'version', 'tests', 'layout', 'artifacts'} <= set(config):
        raise ValueError('Invalid configuration fields')
    if type(config['version']) is not int or config['version'] != 1:
        raise ValueError('Expected constrain configuration version 1')
    test_policy = obj(config['tests'], ('include', 'exclude', 'max_cases', 'max_bytes', 'reviews', 'exceptions'), 'tests')
    for field in ('include', 'exclude'):
        if not isinstance(test_policy[field], list) or any(not isinstance(p, str) for p in test_policy[field]):
            raise ValueError('Test discovery patterns must be arrays')
        for p in test_policy[field]:
            relative(p)
    if not test_policy['include']:
        raise ValueError('Test discovery must not be empty')
    for key in ('max_cases', 'max_bytes'):
        integer(test_policy[key])
    relative(test_policy['reviews'])
    if not isinstance(test_policy['exceptions'], list):
        raise ValueError('exceptions must be an array')
    exceptions = {}
    for entry in test_policy['exceptions']:
        obj(entry, ('rule', 'path', 'reason'), 'exception')
        if entry['rule'] not in ('tests.no-oracle', 'tests.constant-oracle', 'tests.self-comparison', 'tests.duplicate-body') or not isinstance(entry['path'], str) or ':' not in entry['path'] or not isinstance(entry['reason'], str) or len(entry['reason'].strip()) < 20:
            raise ValueError('Exceptions need an exact test identity, supported rule, and concrete reason')
        key = (entry['rule'], entry['path'])
        if key in exceptions:
            raise ValueError('Duplicate exception')
        exceptions[key] = entry
    layout = obj(config['layout'], ('budgets',), 'layout')
    if not isinstance(layout['budgets'], list) or not layout['budgets']:
        raise ValueError('At least one layout budget is required')
    metrics, errors, inventory, findings, warnings = {}, [], {}, [], []
    execution = config.get('execution')
    if execution is not None:
        obj(execution, ('max_jobs', 'max_timeout_minutes'), 'execution')
        for field in execution:
            integer(execution[field])
            if not execution[field]:
                raise ValueError('Execution budgets must be positive')
    if category in ('source', 'all', 'dependencies', 'execution'):
        dep_metrics, dep_errors, warnings = inspect_dependencies(snapshot, execution)
        metrics['dependencies'] = dep_metrics
        errors.extend(e for e in dep_errors if category not in ('dependencies', 'execution') or e['rule'].startswith(category + '.'))
    if category in ('source', 'all', 'documents', 'boundaries'):
        documents = config.get('documents') if category != 'boundaries' else None
        rules = config.get('boundaries', []) if category != 'documents' else []
        if documents is not None:
            if not isinstance(documents, dict):
                raise ValueError('documents must be an object')
            for field in ('include', 'exclude'):
                for pattern in documents.get(field, []):
                    relative(pattern)
        if not isinstance(rules, list):
            raise ValueError('boundaries must be an array')
        for rule in rules:
            if isinstance(rule, dict):
                for pattern in rule.get('include', []):
                    relative(pattern)
        bound_metrics, bound_errors = check_boundaries(snapshot, selected, documents, rules)
        metrics['boundaries'] = bound_metrics
        errors.extend(bound_errors)
    if category in ('source', 'all', 'tests'):
        inventory, findings = test_inventory(snapshot, test_policy)
        reviews = snapshot.json(test_policy['reviews'])
        if not isinstance(reviews, dict):
            raise ValueError('Reviews must map suite paths to review records')
        for name, info in inventory.items():
            record = reviews.get(name)
            if not record:
                errors.append({'rule': 'tests.unreviewed', 'path': name})
                continue
            obj(record, ('sha256', 'risk', 'oracle', 'kinds', 'overlap'), 'review')
            allowed = {'contract', 'simulation', 'functional', 'unit', 'property', 'state-machine', 'performance', 'lean', 'live-e2e', 'structural'}
            if not isinstance(record['kinds'], list) or not record['kinds'] or any(kind not in allowed for kind in record['kinds']) or len(set(record['kinds'])) != len(record['kinds']):
                raise ValueError('Each suite needs distinct supported verification kinds')
            if not isinstance(record['overlap'], str) or len(record['overlap'].strip()) < 20:
                raise ValueError('Each suite needs an explicit cross-layer redundancy assessment')
            if any(not isinstance(record[k], str) or len(record[k].strip()) < 20 for k in ('risk', 'oracle')):
                raise ValueError('Each suite needs a concrete regression risk and behavioral oracle')
            if record['sha256'] != info['sha256']:
                errors.append({'rule': 'tests.stale-review', 'path': name})
        errors.extend({'rule': 'tests.stale-review-entry', 'path': name} for name in sorted(set(reviews) - set(inventory)))
        used = set()
        for finding in findings:
            key = finding['rule'], finding['path']
            if key in exceptions:
                used.add(key)
            else:
                errors.append(finding)
        errors.extend({'rule': 'tests.stale-exception', 'path': path} for rule, path in sorted(set(exceptions) - used))
        metrics['test_cases'] = sum(len(i['tests']) for i in inventory.values())
        metrics['test_bytes'] = sum(i['bytes'] for i in inventory.values())
        for metric, limit in [('test_cases', 'max_cases'), ('test_bytes', 'max_bytes')]:
            if metrics[metric] > test_policy[limit]:
                errors.append({'rule': 'tests.budget', 'path': metric, 'actual': metrics[metric], 'limit': test_policy[limit]})
    if category in ('source', 'all', 'layout'):
        ids = set()
        for budget in layout['budgets']:
            obj(budget, ('id', 'include', 'exclude', 'max_files', 'max_bytes', 'max_depth', 'reason'), 'layout budget')
            if not isinstance(budget['id'], str) or not budget['id'] or budget['id'] in ids:
                raise ValueError('Layout budget IDs must be distinct')
            ids.add(budget['id'])
            if not isinstance(budget['reason'], str) or len(budget['reason'].strip()) < 20:
                raise ValueError('Layout budgets need an ownership reason')
            for field in ('include', 'exclude'):
                if not isinstance(budget[field], list):
                    raise ValueError('Layout patterns must be arrays')
                for pattern in budget[field]:
                    relative(pattern)
            for field in ('max_files', 'max_bytes', 'max_depth'):
                integer(budget[field])
            names = [p for p in snapshot.files if selected(p, budget['include'], budget['exclude'])]
            actual = {'files': len(names), 'bytes': sum(snapshot.size(p) for p in names), 'depth': max((len(PurePosixPath(p).parts) for p in names), default=0)}
            metrics[budget['id']] = actual
            for field, value in actual.items():
                if value > budget['max_' + field]:
                    errors.append({'rule': 'layout.budget', 'path': budget['id'] + '.' + field, 'actual': value, 'limit': budget['max_' + field]})
    if not isinstance(config['artifacts'], list):
        raise ValueError('artifacts must be an array')
    if category == 'artifacts' or (category == 'all' and config['artifacts']):
        if snapshot.staged:
            raise ValueError('Build artifacts must be checked after building, not from the index')
        if not config['artifacts']:
            raise ValueError('No deployment artifacts configured')
        seen = set()
        for artifact in config['artifacts']:
            required = {'path', 'max_bytes', 'baseline_bytes', 'max_growth_bytes', 'environment', 'value'}
            if not isinstance(artifact, dict) or not required <= set(artifact) or set(artifact) - (required | {'kind', 'max_file_bytes', 'max_files'}):
                raise ValueError('Invalid artifact budget fields')
            kind = artifact.get('kind', 'file')
            if kind not in ('file', 'directory'):
                raise ValueError('Artifact kind must be file or directory')
            if kind == 'file' and ('max_file_bytes' in artifact or 'max_files' in artifact):
                raise ValueError('Per-file/count limits apply only to directory artifacts')
            for field in ('max_file_bytes', 'max_files'):
                if field in artifact:
                    integer(artifact[field])
            name = relative(artifact['path'])
            if any(c in name for c in '*?[') or name in seen:
                raise ValueError('Artifact paths must be distinct literal files')
            seen.add(name)
            for field in ('max_bytes', 'baseline_bytes', 'max_growth_bytes'):
                integer(artifact[field])
            if any(not isinstance(artifact[k], str) or len(artifact[k].strip()) < 20 for k in ('environment', 'value')):
                raise ValueError('Artifact limits need deployment provenance and a feature-value rationale')
            path = snapshot.root / name
            if any(p.is_symlink() for p in (path, *path.parents) if p != snapshot.root and p.is_relative_to(snapshot.root)):
                raise ValueError('Missing or symlinked build artifact: ' + name)
            if kind == 'file':
                if not path.is_file():
                    raise ValueError('Missing or symlinked build artifact: ' + name)
                size, count = path.stat().st_size, 1
            else:
                if not path.is_dir():
                    raise ValueError('Missing artifact directory: ' + name)
                size = count = 0
                entries = []
                for item in path.rglob('*'):
                    if len(entries) == 100000:
                        raise ValueError('Artifact directory exceeds 100000 entries')
                    entries.append(item)
                for item in sorted(entries):
                    if item.is_symlink():
                        raise ValueError('Symlinked build artifact: ' + str(item.relative_to(snapshot.root)))
                    if item.is_dir():
                        continue
                    if not item.is_file():
                        raise ValueError('Unsupported build artifact entry: ' + str(item.relative_to(snapshot.root)))
                    count += 1
                    item_size = item.stat().st_size
                    size += item_size
                    if 'max_file_bytes' in artifact and item_size > artifact['max_file_bytes']:
                        errors.append({'rule': 'artifacts.file-limit', 'path': str(item.relative_to(snapshot.root)), 'actual': item_size, 'limit': artifact['max_file_bytes']})
                if 'max_files' in artifact and count > artifact['max_files']:
                    errors.append({'rule': 'artifacts.file-count', 'path': name, 'actual': count, 'limit': artifact['max_files']})
            metrics[name] = {'bytes': size, 'growth_bytes': size - artifact['baseline_bytes'], 'files': count}
            if size > artifact['max_bytes']:
                errors.append({'rule': 'artifacts.environment-limit', 'path': name, 'actual': size, 'limit': artifact['max_bytes']})
            if size - artifact['baseline_bytes'] > artifact['max_growth_bytes']:
                errors.append({'rule': 'artifacts.unbudgeted-growth', 'path': name, 'actual': size - artifact['baseline_bytes'], 'limit': artifact['max_growth_bytes']})
    return {'status': 'fail' if errors else 'pass', 'metrics': metrics, 'errors': errors, 'warnings': warnings,
            **({'inventory': inventory, 'findings': findings} if audit else {}),
            'limits': 'AST checks and hash-bound review records do not prove semantic test value. Review the asserted behavior and demonstrate fault sensitivity; never refresh hashes merely to pass.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'audit'))
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--category', choices=('source', 'all', 'tests', 'layout', 'artifacts', 'dependencies', 'execution', 'documents', 'boundaries'), default='source')
    parser.add_argument('--staged', action='store_true', help='Read policy, reviews and sources from the Git index')
    parser.add_argument('--strict-dependencies', action='store_true', help='Fail when discovered runtime dependency acquisition is unchecked')
    args = parser.parse_args(argv)
    if args.strict_dependencies and args.category not in ('source', 'all', 'dependencies'):
        parser.error('--strict-dependencies requires source, all, or dependencies')
    try:
        result = evaluate(Snapshot(args.repo, args.staged), args.category, args.command == 'audit')
        if args.strict_dependencies and result['warnings']:
            result['errors'].extend(result['warnings'])
            result['status'] = 'fail'
        print(json.dumps(result, indent=2, sort_keys=True))
        return int(result['status'] != 'pass')
    except (OSError, ValueError, SyntaxError, TypeError, KeyError, subprocess.TimeoutExpired) as error:
        print('constrain: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
