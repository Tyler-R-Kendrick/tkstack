#!/usr/bin/env python3
"""Check reviewed documentation against source content, including the real Git index."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
sys.dont_write_bytecode = True
from urllib.parse import unquote, urlsplit

POLICY, LEDGER = 'docs/docs-policy.json', 'docs/docs-freshness.json'
START, END = '<!-- tkstack:profiles:start -->', '<!-- tkstack:profiles:end -->'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/constrain/scripts"))
from git_snapshot import GitSnapshot, git


class Snapshot(GitSnapshot):
    allow_links = True

    def __init__(self, root, staged=False):
        super().__init__(root, staged)
        self.algorithm = git(self.root, "rev-parse", "--show-object-format").decode().strip()

    def fingerprint(self, name):
        indexed = self.indexed(name)
        if indexed and name != 'AGENTS.md':
            return self.index[name]
        path = self.root / name
        data = self.read(name)
        mode = self.index[name]['mode'] if indexed else '120000' if path.is_symlink() else '100755' if path.stat().st_mode & 0o111 else '100644'
        normalized = False
        if name == 'AGENTS.md' and data.count(b'<!-- tkstack:steering:start -->') == data.count(b'<!-- tkstack:steering:end -->') == 1:
            # Installer-owned absolute paths vary across clones; its renderer is a mapped source.
            data = re.sub(rb'(?s)<!-- tkstack:steering:start -->.*?<!-- tkstack:steering:end -->', b'<!-- tkstack:steering:generated -->', data)
            normalized = True
        oid = hashlib.new(self.algorithm, b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        return {'mode': mode, 'oid': oid, **({'normalized': 'installer-steering-v1'} if normalized else {})}

    def exists(self, name):
        return name in self.files or any(path.startswith(name.rstrip('/') + '/') for path in self.files)


def policy(snapshot):
    value = snapshot.json(POLICY)
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1 or set(value) != {'version', 'areas'} or not isinstance(value['areas'], dict) or not value['areas']:
        raise ValueError('Invalid documentation policy')
    for name, area in value['areas'].items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', name) or not isinstance(area, dict) or set(area) - {'inputs', 'exclude', 'docs'}:
            raise ValueError('Invalid documentation area: ' + name)
        for field in ('inputs', 'docs'):
            if not isinstance(area.get(field), list) or not area[field] or any(not isinstance(path, str) or not path for path in area[field]):
                raise ValueError('Documentation areas need input patterns and concrete document paths')
        if any(path not in snapshot.files or not path.endswith('.md') for path in area['docs']):
            raise ValueError('Documentation area has missing Markdown: ' + name)
    return value


def fingerprints(snapshot, names):
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(zip(names, pool.map(snapshot.fingerprint, names)))


def area_snapshot(snapshot, area):
    names = sorted(name for name in snapshot.files if name != LEDGER and any(fnmatch.fnmatchcase(name, pattern) for pattern in area['inputs'])
        and not any(fnmatch.fnmatchcase(name, pattern) for pattern in area.get('exclude', []))
        and not any(part in ('node_modules', '__pycache__', '.tkstack', '.git') for part in PurePosixPath(name).parts))
    return {'inputs': fingerprints(snapshot, names), 'docs': fingerprints(snapshot, sorted(area['docs']))}


def _setting(text, name):
    match = re.search(rf'(?m)^{name}=(\S+)', text)
    if not match:
        raise ValueError('install.sh is missing ' + name)
    return match.group(1).strip('"').strip("'")


def profile_block(snapshot):
    """README block generated from the bootstrap's Python selection."""
    text = snapshot.read('install.sh').decode()
    rows = [
        START,
        'The host needs Bash, Git, and curl. Dotfiles setup provisions current Node.js. Missing Python 3.11+ is installed as the current stable Python **'
        + _setting(text, 'PYTHON_VERSION') + '** using the current uv release and its published SHA-256.',
        'Archive bootstrap requires an independently supplied SHA-256 digest.',
        'The default catalog installs applicable skills and tools for Codex, Claude Code, and Cursor. Explicit profiles narrow skill selection.',
        END,
    ]
    return '\n'.join(rows)


def prose(text):
    result, fence = [], None
    for line in text.splitlines():
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
        elif fence is None:
            result.append(line)
    return '\n'.join(result)


def structural_errors(snapshot):
    errors = []
    readme = snapshot.read('README.md').decode()
    if readme.count(START) != 1 or readme.count(END) != 1:
        errors.append('README is missing its generated profile block; run check_docs.py render')
    elif readme[readme.index(START):readme.index(END) + len(END)] != profile_block(snapshot):
        errors.append('README install settings are stale; run check_docs.py render')
    markdown = sorted(name for name in snapshot.files if name in ('README.md', 'GLOSSARY.md') or name.startswith('docs/') and name.endswith('.md'))
    for name in markdown:
        content = prose(snapshot.read(name).decode())
        for raw in re.findall(r'!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)', content):
            target = raw.strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            relative = unquote(parsed.path)
            if relative.startswith('/'):
                relative = relative[1:]
            else:
                relative = str(PurePosixPath(name).parent / relative)
            parts = []
            for part in relative.split('/'):
                if part == '..':
                    if not parts:
                        errors.append(name + ': link escapes repository: ' + target)
                        break
                    parts.pop()
                elif part not in ('', '.'):
                    parts.append(part)
            else:
                if parts and not snapshot.exists('/'.join(parts)):
                    errors.append(name + ': missing local link: ' + target)
    return errors


def ledger_document(snapshot):
    value = snapshot.json(LEDGER)
    if not isinstance(value, dict) or type(value.get('version')) is not int or value.get('version') != 1 or not isinstance(value.get('areas'), dict):
        raise ValueError('Invalid documentation freshness ledger')
    for name, record in value['areas'].items():
        if not isinstance(record, dict) or not isinstance(record.get('inputs'), dict) or not isinstance(record.get('docs'), dict) or not isinstance(record.get('reason'), str) or not record['reason'].strip() or type(record.get('no_doc_impact')) is not bool:
            raise ValueError('Invalid documentation review record: ' + name)
    return value


def check(snapshot):
    rules = policy(snapshot)
    errors = structural_errors(snapshot)
    if LEDGER not in snapshot.files:
        return [*errors, 'Missing docs freshness ledger; review docs and run check_docs.py refresh --all --reason ...']
    ledger = ledger_document(snapshot)
    if not isinstance(ledger, dict) or ledger.get('version') != 1 or ledger.get('policy') != snapshot.fingerprint(POLICY) or ledger.get('object_format') != snapshot.algorithm:
        errors.append('Documentation policy changed; review and refresh all documentation areas')
    records = ledger.get('areas', {})
    for name, area in rules['areas'].items():
        actual = area_snapshot(snapshot, area)
        previous = records.get(name, {})
        if actual['inputs'] != previous.get('inputs') or actual['docs'] != previous.get('docs') or not previous.get('reason'):
            errors.append('Stale docs area ' + name + ': review ' + ', '.join(area['docs']) + '; then refresh --area ' + name + ' --reason ...')
    if set(records) - set(rules['areas']):
        errors.append('Removed documentation areas remain in the ledger; refresh --all')
    return errors


def refresh(snapshot, areas, reason, no_doc_impact=False):
    rules = policy(snapshot)
    errors = structural_errors(snapshot)
    if errors:
        raise ValueError('\n'.join(errors))
    previous = ledger_document(snapshot) if LEDGER in snapshot.files else {'areas': {}}
    if previous.get('policy', snapshot.fingerprint(POLICY)) != snapshot.fingerprint(POLICY) and set(areas) != set(rules['areas']):
        raise ValueError('Documentation policy changed; review and refresh --all')
    records = dict(previous.get('areas', {}))
    if set(areas) - set(rules['areas']):
        raise ValueError('Unknown documentation area')
    for name in areas:
        actual = area_snapshot(snapshot, rules['areas'][name])
        old = records.get(name)
        old_content = {path: record['oid'] for path, record in old.get('docs', {}).items()} if old else {}
        new_content = {path: record['oid'] for path, record in actual['docs'].items()}
        if old and old.get('inputs') != actual['inputs'] and old_content == new_content and not no_doc_impact:
            raise ValueError('Area ' + name + ' changed without a documentation edit. Update docs or explicitly justify --no-doc-impact with --reason.')
        records[name] = {**actual, 'reason': reason, 'no_doc_impact': bool(no_doc_impact)}
    for name, area in rules['areas'].items():
        if name in areas or name not in records:
            continue
        actual = area_snapshot(snapshot, area)
        if records[name].get('inputs') == actual['inputs'] and records[name].get('docs') != actual['docs']:
            records[name] = {**records[name], 'docs': actual['docs'], 'docs_refresh_reason': reason}
    records = {name: records[name] for name in rules['areas'] if name in records}
    value = {'version': 1, 'object_format': snapshot.algorithm, 'policy': snapshot.fingerprint(POLICY), 'areas': records}
    destination = snapshot.root / LEDGER
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.docs-freshness-', mode='w', delete=False) as output:
            temporary = Path(output.name)
            output.write(json.dumps(value, indent=2, sort_keys=True) + '\n')
            os.fchmod(output.fileno(), 0o644)
        temporary.replace(destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--repo', type=Path, default=Path.cwd())
    commands = cli.add_subparsers(dest='command')
    checking = commands.add_parser('check')
    checking.add_argument('--staged', action='store_true')
    commands.add_parser('render', help='Update only the source-generated README block')
    updating = commands.add_parser('refresh', help='Record an explicitly reviewed documentation/source snapshot')
    select = updating.add_mutually_exclusive_group(required=True)
    select.add_argument('--all', action='store_true')
    select.add_argument('--area', action='append')
    updating.add_argument('--reason', required=True)
    updating.add_argument('--no-doc-impact', action='store_true')
    args = cli.parse_args()
    try:
        snapshot = Snapshot(args.repo, getattr(args, 'staged', False))
        if args.command == 'render':
            text = snapshot.read('README.md').decode()
            if text.count(START) != 1 or text.count(END) != 1:
                raise ValueError('README must contain one profile marker pair')
            text = text[:text.index(START)] + profile_block(snapshot) + text[text.index(END) + len(END):]
            (snapshot.root / 'README.md').write_text(text)
            print('Rendered README profile block')
        elif args.command == 'refresh':
            if not args.reason.strip():
                raise ValueError('Supply an actual review reason')
            refresh(snapshot, list(policy(snapshot)['areas']) if args.all else args.area, args.reason, args.no_doc_impact)
            print('Recorded reviewed documentation snapshot')
        else:
            errors = check(snapshot)
            if errors:
                print('\n'.join(errors), file=sys.stderr)
                return 1
            print('Documentation is current for the ' + ('staged index' if snapshot.staged else 'worktree') + ' snapshot')
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print('Documentation check: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
