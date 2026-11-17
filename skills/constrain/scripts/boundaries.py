"""Explicit, bounded static checks for owned documents and Python boundaries."""
import ast
import hashlib


def check(snapshot, selected, documents, rules):
    errors, metrics = [], {'document_files': 0, 'boundary_files': 0}
    if documents is not None:
        if not isinstance(documents, dict) or set(documents) != {'include', 'exclude'}:
            raise ValueError('documents requires include and exclude patterns')
        if not isinstance(documents['include'], list) or not documents['include'] or not isinstance(documents['exclude'], list):
            raise ValueError('documents needs nonempty include and an exclude array')
        seen = {}
        for name in snapshot.files:
            if not selected(name, documents['include'], documents['exclude']):
                continue
            metrics['document_files'] += 1
            digest = hashlib.sha256(snapshot.read(name)).hexdigest()
            if digest in seen:
                errors.append({'rule':'documents.duplicate-bytes','path':name,'other':seen[digest]})
            else:
                seen[digest] = name
    if not isinstance(rules, list):
        raise ValueError('boundaries must be an array')
    ids = set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {'id', 'include', 'forbid_imports', 'forbid_calls'}:
            raise ValueError('Each boundary requires id, include, forbid_imports, and forbid_calls')
        if not isinstance(rule['id'], str) or not rule['id'] or rule['id'] in ids:
            raise ValueError('Boundary IDs must be unique nonempty strings')
        ids.add(rule['id'])
        for field in ('include', 'forbid_imports', 'forbid_calls'):
            if not isinstance(rule[field], list) or any(not isinstance(v, str) or not v for v in rule[field]):
                raise ValueError('Boundary fields must be arrays of nonempty strings')
        if not rule['include'] or not (rule['forbid_imports'] or rule['forbid_calls']):
            raise ValueError('A boundary needs a scope and at least one forbidden operation')
        names = [name for name in snapshot.files if selected(name, rule['include'])]
        if not names:
            errors.append({'rule':'boundaries.empty-scope','path':rule['id']})
        for name in names:
            metrics['boundary_files'] += 1
            if not name.endswith('.py'):
                raise ValueError('Python boundary rules require .py files: ' + name)
            tree = ast.parse(snapshot.read(name), filename=name)
            for node in ast.walk(tree):
                imports = ([n.name for n in node.names] if isinstance(node, ast.Import) else
                           [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
                for module in imports:
                    if any(module == banned or module.startswith(banned + '.') for banned in rule['forbid_imports']):
                        errors.append({'rule':'boundaries.forbidden-import','path':name,'line':node.lineno,'boundary':rule['id'],'value':module})
                if isinstance(node, ast.Call):
                    call = ast.unparse(node.func)
                    if call in rule['forbid_calls']:
                        errors.append({'rule':'boundaries.forbidden-call','path':name,'line':node.lineno,'boundary':rule['id'],'value':call})
    return metrics, errors
