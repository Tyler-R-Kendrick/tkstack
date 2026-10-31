#!/usr/bin/env python3
"""Compile verified Markdown-derived code to a reusable executable lock artifact."""
import argparse
import ast
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tkstack_state import ensure_state, state_path, project_root, session_tempdir
from json_contract import loads as parse_json

PACKAGE = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("codify_workflow_authoring_" + hashlib.sha256(str(PACKAGE).encode()).hexdigest()[:12], PACKAGE / "scripts/workflow_authoring.py")
authoring = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(authoring)
_command_spec = importlib.util.spec_from_file_location("codify_commands_" + hashlib.sha256(str(PACKAGE).encode()).hexdigest()[:12], PACKAGE / "scripts/command_schema.py")
command_schema = importlib.util.module_from_spec(_command_spec)
_command_spec.loader.exec_module(command_schema)
VERSION = "0.1.0"
FORMAT = "tkstack.codify/v1"
LIMIT = 16 * 1024 * 1024
SKIP = {".git", ".tkstack", "node_modules", "__pycache__"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()




def read_bytes(path):
    if path.stat().st_size > LIMIT:
        raise ValueError(f"File exceeds 16 MiB: {path.name}")
    with path.open('rb') as source:
        data = source.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError("File exceeds 16 MiB")
    return data


def relative_file(name):
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError("Expected a relative POSIX file path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in name.split('/')) or any(part in SKIP for part in path.parts):
        raise ValueError("Unsafe artifact path")
    return path


def regular(path, root):
    path = path.absolute()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Expected an existing file inside the root: {path}")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f"Symlinked build inputs are not supported: {path}")
        if part == root:
            break
    return path


def scaffold(source, target, backend="python"):
    source = source.absolute()
    before = read_bytes(source)
    before.decode('utf-8')
    files = authoring.workflow_files(backend, "Execute the verified procedure derived from PROMPT.md.")
    files["PROMPT.md"] = before
    files["LICENSE"] = (PACKAGE / "LICENSE").read_bytes()
    target.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in files.items():
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    except OSError:
        shutil.rmtree(target)
        raise
    return {"status": "workflow-draft", "path": str(target), "source_sha256": digest(before),
            "next": "Implement scripts/workflow, author positive and negative contract cases, then compile PROMPT.md. Drafts cannot be compiled."}


def snapshot(root, paths, output):
    selected = {}
    for supplied in paths:
        supplied = supplied.absolute()
        if not supplied.is_relative_to(root):
            raise ValueError("All build inputs must be contained in --root")
        if supplied.is_symlink():
            raise ValueError("Symlinked build inputs are not supported")
        if supplied.is_dir():
            entries = []
            for parent, dirs, files in os.walk(supplied, followlinks=False):
                dirs[:] = sorted(name for name in dirs if name not in SKIP)
                for directory in dirs:
                    if (Path(parent) / directory).is_symlink():
                        raise ValueError("Symlinked build directories are not supported")
                entries.extend(Path(parent) / name for name in sorted(files))
        else:
            entries = [supplied]
        for path in entries:
            if path == output:
                continue
            path = regular(path, root)
            name = path.relative_to(root).as_posix()
            relative_file(name)
            data = read_bytes(path)
            if path.suffix == '.py':
                ast.parse(data.decode('utf-8'), filename=name)
            if (path.parent == paths[0].absolute() and path.name in ('workflow.py', 'workflow.ts')
                    and b'WORKFLOW_NOT_IMPLEMENTED' in data):
                raise ValueError("Implement the executable workflow before compiling a lock")
            mode = 0o755 if path.stat().st_mode & 0o100 else 0o644
            selected[name] = {"sha256": digest(data), "mode": mode, "base64": base64.b64encode(data).decode('ascii')}
    if not selected or len(selected) > 512 or sum(len(item['base64']) for item in selected.values()) > LIMIT:
        raise ValueError("Expected 1..512 files totaling at most 16 MiB encoded")
    return dict(sorted(selected.items()))


def cases_from(data):
    value = parse_json(data)
    if not isinstance(value, dict) or set(value) != {'version', 'cases'} or type(value['version']) is not int or value['version'] != 1:
        raise ValueError("Cases require version 1 and cases")
    cases = value['cases']
    if not isinstance(cases, list) or not 2 <= len(cases) <= 64:
        raise ValueError("Supply 2..64 cases including success and rejection")
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or not {'id', 'input', 'exit'} <= set(case) or set(case) - {'id', 'input', 'exit', 'output'}:
            raise ValueError("Each case requires id, input, exit, and output for success")
        if not isinstance(case['id'], str) or not case['id'] or case['id'] in ids:
            raise ValueError("Case IDs must be unique nonempty strings")
        ids.add(case['id'])
        if not isinstance(case['input'], dict) or type(case['exit']) is not int or not 0 <= case['exit'] <= 125:
            raise ValueError("Case input must be an object and exit an integer 0..125")
        if (case['exit'] == 0) != ('output' in case):
            raise ValueError("Only success cases require output")
    if not any(case['exit'] == 0 for case in cases) or not any(case['exit'] != 0 for case in cases):
        raise ValueError("Cases must include a success and a rejection")
    return cases


def decode_files(lock):
    files = lock['files']
    if not isinstance(files, dict) or not 1 <= len(files) <= 512:
        raise ValueError("Invalid artifact inventory")
    decoded, size = {}, 0
    for name, item in files.items():
        relative_file(name)
        if not isinstance(item, dict) or set(item) != {'sha256', 'mode', 'base64'} or not isinstance(item['base64'], str) or type(item['mode']) is not int or not 0 <= item['mode'] <= 0o777:
            raise ValueError("Invalid artifact file record")
        size += len(item['base64'])
        if size > LIMIT:
            raise ValueError("Artifact exceeds 16 MiB encoded")
        try:
            data = base64.b64decode(item['base64'], validate=True)
        except ValueError as error:
            raise ValueError("Invalid artifact encoding") from error
        if digest(data) != item['sha256']:
            raise ValueError(f"Artifact file hash mismatch: {name}")
        decoded[name] = data
    for name in decoded:
        if any(parent.as_posix() in decoded for parent in PurePosixPath(name).parents):
            raise ValueError("Artifact file/directory collision")
    return decoded


def validate_lock(lock):
    fields = {'format', 'compiler', 'root', 'source', 'cases', 'entrypoint', 'runtime', 'inference', 'files', 'verification', 'artifact_sha256'}
    if not isinstance(lock, dict) or set(lock) != fields or lock['format'] != FORMAT or lock['compiler'] != {'name': 'codify', 'version': VERSION}:
        raise ValueError("Unsupported codify lock format/compiler")
    unsigned = {key: value for key, value in lock.items() if key != 'artifact_sha256'}
    if digest(canonical(unsigned)) != lock['artifact_sha256']:
        raise ValueError("Artifact digest mismatch")
    if not isinstance(lock['root'], str) or Path(lock['root']).is_absolute():
        raise ValueError("Root must be relative to the lock file")
    for kind in ('source', 'cases'):
        record = lock[kind]
        if not isinstance(record, dict) or set(record) != {'path', 'sha256'}:
            raise ValueError("Invalid source/cases provenance")
        relative_file(record['path'])
    relative_file(lock['entrypoint'])
    inference = lock['inference']
    if not isinstance(inference, dict) or set(inference) != {'mode', 'profiles'} or inference['mode'] not in ('none', 'explicit'):
        raise ValueError("Invalid inference declaration")
    profiles = inference['profiles']
    if not isinstance(profiles, list) or any(not isinstance(name, str) or not name for name in profiles) or profiles != sorted(set(profiles)):
        raise ValueError("Inference profiles must be sorted unique names")
    if bool(profiles) != (inference['mode'] == 'explicit'):
        raise ValueError("Explicit inference requires named profiles")
    decoded = decode_files(lock)
    if lock['entrypoint'] not in decoded or lock['runtime'] not in ('python', 'node'):
        raise ValueError("Missing supported entrypoint")
    verification = lock['verification']
    if not isinstance(verification, dict) or set(verification) != {'status', 'case_ids', 'repeat_successes'} or verification['status'] != 'passed':
        raise ValueError("Artifact must contain successful contract verification")
    if type(verification['repeat_successes']) is not int or verification['repeat_successes'] != (2 if inference['mode'] == 'none' else 1):
        raise ValueError("Invalid repeatability evidence")
    ids = verification['case_ids']
    if not isinstance(ids, list) or len(ids) < 2 or any(not isinstance(x, str) for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("Invalid case inventory")
    return decoded


def check(path):
    path = path.absolute()
    lock = parse_json(read_bytes(path))
    decoded = validate_lock(lock)
    root = (path.parent / lock['root']).resolve(strict=True)
    observed = {}
    for kind in ('source', 'cases'):
        record = lock[kind]
        data = read_bytes(regular(root / record['path'], root))
        if digest(data) != record['sha256']:
            raise ValueError(f"Stale {kind}; recompile explicitly")
        observed[record['path']] = data
    for name, data in decoded.items():
        if (read_bytes(regular(root / name, root)) != data or
                (root / name).stat().st_mode & 0o100 != lock['files'][name]['mode'] & 0o100):
            raise ValueError(f"Stale workflow input {name}; recompile explicitly")
    case_ids = [case['id'] for case in cases_from(observed[lock['cases']['path']])]
    if case_ids != lock['verification']['case_ids']:
        raise ValueError("Verification case inventory mismatch")
    return lock


def invoke(lock, payload, project, timeout=30, dependencies=None, config=None, environment=None):
    decoded = decode_files(lock)
    if not isinstance(payload, dict) or len(canonical(payload)) > 1024 * 1024:
        raise ValueError("Input must be a JSON object within 1 MiB")
    if not 1 <= timeout <= 300:
        raise ValueError("Timeout must be 1..300 seconds")
    if lock['inference']['mode'] == 'none' and config is not None:
        raise ValueError("This lock declares no inference; external profiles are not accepted")
    if config is not None:
        configuration = config if isinstance(config, dict) else parse_json(read_bytes(config))
        if not isinstance(configuration, dict) or not isinstance(configuration.get('profiles'), dict) or set(configuration['profiles']) - set(lock['inference']['profiles']):
            raise ValueError("Configuration contains undeclared inference profiles")
    else:
        configuration = None
        bundled = str(PurePosixPath(lock['entrypoint']).parent / 'profiles.json')
        if bundled in decoded:
            bundled_config = parse_json(decoded[bundled])
            if not isinstance(bundled_config, dict) or not isinstance(bundled_config.get('profiles'), dict) or set(bundled_config['profiles']) - set(lock['inference']['profiles']):
                raise ValueError("Bundled configuration contains undeclared inference profiles")
    with session_tempdir(prefix='codify-', project=project) as run:
        work = run / 'work'
        work.mkdir()
        for name, data in decoded.items():
            destination = work / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            destination.chmod(lock['files'][name]['mode'])
        if dependencies is not None:
            if lock['runtime'] != 'node':
                raise ValueError("External npm dependencies require the node runtime")
            dependencies = dependencies.resolve(strict=True)
            package_path = str(PurePosixPath(lock['entrypoint']).parent / 'package.json')
            if package_path not in decoded:
                raise ValueError("Node dependency reuse requires a locked package.json")
            package = parse_json(decoded[package_path])
            for name, version in package.get('dependencies', {}).items():
                relative_file(name)
                actual = parse_json(read_bytes(dependencies / name / 'package.json'))
                if actual.get('version') != version:
                    raise ValueError(f"Installed direct dependency version mismatch: {name}")
            (work / lock['entrypoint']).parent.joinpath('node_modules').symlink_to(dependencies, target_is_directory=True)
        input_path = run / 'input.json'
        input_path.write_bytes(canonical(payload))
        command = [sys.executable, '-B'] if lock['runtime'] == 'python' else ['node']
        command += [str(work / lock['entrypoint']), '--input', str(input_path)]
        if configuration is not None:
            config_path = run / 'profiles.json'
            config_path.write_bytes(canonical(configuration))
            command += ['--config', str(config_path)]
        with (run / 'stdout').open('w+b') as out, (run / 'stderr').open('w+b') as err:
            child_environment = dict(os.environ if environment is None else environment)
            shared_group = child_environment.get('TKSTACK_CODIFY_EXECUTION') == '1'
            child_environment['TKSTACK_CODIFY_EXECUTION'] = '1'
            process = subprocess.Popen(command, cwd=work, env=child_environment, stdout=out, stderr=err, start_new_session=not shared_group)
            try:
                try:
                    code = process.wait(timeout=timeout)
                except (subprocess.TimeoutExpired, KeyboardInterrupt):
                    if shared_group:
                        process.kill()
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    raise ValueError("Workflow deadline exceeded or invocation interrupted")
                if out.tell() > 1024 * 1024 or err.tell() > 1024 * 1024:
                    raise ValueError("Workflow output exceeds 1 MiB")
                out.seek(0)
                err.seek(0)
                return code, out.read().decode('utf-8'), err.read().decode('utf-8')
            finally:
                if not shared_group:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass


def compile_workflow(source, entrypoint, cases, output=None, root=None, includes=(), profiles=(), dry_run=False,
                     project=None, jobs=4, timeout=30, dependencies=None, config=None):
    root = (root or source.parent).resolve(strict=True)
    if (root / 'commands').exists():
        command_schema.catalog(root)
        includes = [*includes, root / 'commands']
    source, entrypoint, cases = [regular(path.absolute(), root) for path in (source, entrypoint, cases)]
    output = (output or source.with_suffix('.lock.json')).absolute()
    if not output.is_relative_to(root) or output.is_symlink() or output in (source, entrypoint, cases):
        raise ValueError("Lock output must be a separate regular file within --root")
    if not output.parent.is_dir() or output.parent.resolve() != output.parent:
        raise ValueError("Lock output parent must be an existing real directory")
    if type(jobs) is not int or not 1 <= jobs <= 16 or not 1 <= timeout <= 300:
        raise ValueError("Use jobs 1..16 and timeout 1..300 seconds")
    if entrypoint.suffix not in ('.py', '.ts', '.js', '.mjs'):
        raise ValueError("Entrypoint must be Python or Node-compatible code")
    before = output.read_bytes() if output.exists() else None
    source_data, case_data = read_bytes(source), read_bytes(cases)
    source_data.decode('utf-8')
    contract = cases_from(case_data)
    profile_names = sorted(set(profiles))
    if any(not isinstance(name, str) or not name for name in profile_names):
        raise ValueError("Inference profiles must be nonempty names")
    lock = {'format': FORMAT, 'compiler': {'name': 'codify', 'version': VERSION},
            'root': Path(os.path.relpath(root, output.parent)).as_posix(),
            'source': {'path': source.relative_to(root).as_posix(), 'sha256': digest(source_data)},
            'cases': {'path': cases.relative_to(root).as_posix(), 'sha256': digest(case_data)},
            'entrypoint': entrypoint.relative_to(root).as_posix(), 'runtime': 'python' if entrypoint.suffix == '.py' else 'node',
            'inference': {'mode': 'explicit' if profile_names else 'none', 'profiles': profile_names},
            'files': snapshot(root, [entrypoint.parent, *includes], output),
            'verification': {'status': 'passed', 'case_ids': [case['id'] for case in contract], 'repeat_successes': 1 if profile_names else 2}}
    if lock['entrypoint'] not in lock['files']:
        raise ValueError("Entrypoint was excluded from the artifact")
    lock['artifact_sha256'] = digest(canonical(lock))
    validate_lock(lock)
    encoded = canonical(lock) + b'\n'
    if len(encoded) > LIMIT:
        raise ValueError('Serialized artifact exceeds 16 MiB')
    if dry_run:
        return {'status': 'planned', 'artifact_sha256': lock['artifact_sha256'], 'files': sorted(lock['files']), 'output': str(output)}
    project = project or project_root(root)
    def verify(case):
        first = None
        for _ in range(1 if case['exit'] else lock['verification']['repeat_successes']):
            code, stdout, stderr = invoke(lock, case['input'], project, timeout, dependencies, config)
            if code != case['exit']:
                raise ValueError(f"Case {case['id']} exit {code}; expected {case['exit']}")
            if code == 0:
                value = canonical(parse_json(stdout))
                if value != canonical(case['output']) or (first is not None and value != first):
                    raise ValueError(f"Case {case['id']} output mismatch or non-repeatable result")
                first = value
            elif stdout.strip():
                raise ValueError(f"Rejected case {case['id']} emitted success output")
        return case['id']
    with ThreadPoolExecutor(max_workers=min(jobs, len(contract))) as pool:
        futures = [pool.submit(verify, case) for case in contract]
        failures = []
        for future in futures:
            try:
                future.result()
            except (OSError, ValueError) as error:
                failures.append(str(error))
        if failures:
            raise ValueError('; '.join(failures))
    current = snapshot(root, [entrypoint.parent, *includes], output)
    if current != lock['files'] or read_bytes(source) != source_data or read_bytes(cases) != case_data:
        raise ValueError("Build inputs changed during verification")
    lock_id = digest(str(output).encode())[:16]
    writer = ensure_state(state_path('locks', project) / 'codify') / (lock_id + '.lock')
    writer.mkdir()
    temporary = None
    try:
        if snapshot(root, [entrypoint.parent, *includes], output) != lock['files'] or read_bytes(source) != source_data or read_bytes(cases) != case_data:
            raise ValueError("Build inputs changed before publication")
        if (output.read_bytes() if output.exists() else None) != before:
            raise ValueError("Lock artifact changed during compilation")
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.codify-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
        temporary.chmod(output.stat().st_mode & 0o777 if output.exists() else 0o644)
        temporary.replace(output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        writer.rmdir()
    return {'status': 'compiled', 'output': str(output), 'artifact_sha256': lock['artifact_sha256'],
            'case_ids': lock['verification']['case_ids'], 'inference': lock['inference']}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command_argv = []
    if '--' in argv:
        split = argv.index('--')
        command_argv, argv = argv[split + 1:], argv[:split]
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    draft = commands.add_parser('scaffold')
    draft.add_argument('source', type=Path)
    draft.add_argument('--target', type=Path, required=True)
    draft.add_argument('--backend', choices=tuple(authoring.BACKENDS), default='python')
    build = commands.add_parser('compile')
    build.add_argument('source', type=Path)
    build.add_argument('--entrypoint', type=Path, required=True)
    build.add_argument('--cases', type=Path, required=True)
    build.add_argument('--root', type=Path)
    build.add_argument('--output', type=Path)
    build.add_argument('--include', dest='includes', action='append', type=Path, default=[])
    build.add_argument('--profile', dest='profiles', action='append', default=[])
    build.add_argument('--jobs', type=int, default=4)
    build.add_argument('--dry-run', action='store_true')
    inspect = commands.add_parser('check')
    inspect.add_argument('artifact', type=Path)
    run = commands.add_parser('run')
    run.add_argument('artifact', type=Path)
    run.add_argument('--input', required=True)
    for command in (build, run):
        command.add_argument('--config', type=Path)
        command.add_argument('--project', type=Path, help='Active project for ignored .tkstack state; default current project')
        command.add_argument('--timeout', type=int, default=30)
        command.add_argument('--dependencies', type=Path, help='Explicit installed node_modules for the artifact dependency lock')
    command_schema.add_parsers(commands)
    parsed = parser.parse_args(argv)
    if command_argv and parsed.command != 'invoke':
        parser.error('Only invoke accepts -- <command> [arguments]')
    if parsed.command in ('commands', 'invoke'):
        try:
            call = None
            if getattr(parsed, 'call', None) is not None:
                call = sys.stdin.read(1024 * 1024 + 1) if parsed.call == '-' else read_bytes(Path(parsed.call))
                if len(call) > 1024 * 1024:
                    raise ValueError('Tool call exceeds 1 MiB')
            engine = SimpleNamespace(check=check, invoke=invoke, project_root=project_root)
            code, out, err = command_schema.operation(engine, parsed, command_argv, call)
            sys.stdout.write(out)
            sys.stderr.write(err)
            return code if 0 <= code <= 125 else 1
        except (OSError, ValueError, TypeError, KeyError) as error:
            print(f'codify: {error}', file=sys.stderr)
            return 1
    args = vars(parsed)
    command = args.pop('command')
    try:
        if command == 'scaffold':
            result = scaffold(**args)
        elif command == 'compile':
            result = compile_workflow(**args)
        elif command == 'check':
            artifact = check(args['artifact'])
            result = {'status': 'current', 'artifact_sha256': artifact['artifact_sha256'], 'inference': artifact['inference']}
        else:
            artifact = check(args['artifact'])
            raw = sys.stdin.read(1024 * 1024 + 1) if args['input'] == '-' else read_bytes(Path(args['input']))
            if len(raw) > 1024 * 1024:
                raise ValueError('Input exceeds 1 MiB')
            code, out, err = invoke(artifact, parse_json(raw), args['project'] or project_root(), args['timeout'], args['dependencies'], args['config'])
            if code == 0:
                parse_json(out)
            sys.stdout.write(out)
            sys.stderr.write(err)
            return code if 0 <= code <= 125 else 1
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, TypeError, SyntaxError, KeyError) as error:
        print(f'codify: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
