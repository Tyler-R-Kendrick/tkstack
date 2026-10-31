#!/usr/bin/env python3
"""Install and initialize tkstack dotfiles noninteractively, including managed runtimes."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import fcntl
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
import uuid

import install
import bootstrap_shell
from runtime_environment import with_paths
import bootstrap_toolchains
from tkstack_state import ensure_state, state_root
from sync_codify import sync as check_codify_release

ROOT = Path(__file__).resolve().parent.parent
from bootstrap_profiles import validate as validate_profiles
PROFILES = validate_profiles(json.loads((ROOT / 'harnesses/bootstrap/profiles.json').read_text()))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--profile', choices=PROFILES, default='dotfiles')
    result.add_argument('--target', type=Path, default=Path.home(), help='Dotfiles target (default: current user home)')
    result.add_argument('--scope', choices=('home', 'project'), default='home', help='Native instruction placement; default home')
    result.add_argument('--workspace', type=Path, help='Workspace for private state/Copilot setup; default source checkout')
    result.add_argument('--harness', choices=tuple(install.SKILL_PATHS), action='append')
    result.add_argument('--runtime', action='append', help='Limit runtime setup to named integrations (repeatable)')
    result.add_argument('--offline', action='store_true', help='Apply files using available runtimes; never download prerequisites or packages')
    result.add_argument('--no-toolchains', action='store_true', help='Use only already available Node/npm/uv')
    result.add_argument('--strict', action='store_true', help='Also fail for known unresolved external/runtime/credential prerequisites')
    mode = result.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='Read-only plan/preflight; no initialization or downloads')
    mode.add_argument('--check', action='store_true', help='Read-only verification of the selected installation')
    copilot = result.add_mutually_exclusive_group()
    copilot.add_argument('--copilot', dest='copilot', action='store_true')
    copilot.add_argument('--no-copilot', dest='copilot', action='store_false')
    result.set_defaults(copilot=None)
    result.add_argument('--no-shell', action='store_true', help='Do not add home bash/login pointers; env.sh is still generated')
    result.add_argument('--jobs', type=int, default=4, help='Independent runtime workers, 1..8 (default 4)')
    result.add_argument('--runtime-timeout', type=int, default=900, help='Deadline per runtime in seconds (10..1800)')
    return result


def command(script, *args):
    return [sys.executable, '-B', str(ROOT / 'scripts' / script), *map(str, args)]


def selection(args, manifest):
    if not 1 <= args.jobs <= 8 or not 10 <= args.runtime_timeout <= 1800:
        raise ValueError('Use jobs 1..8 and runtime-timeout 10..1800')
    unknown = set(args.runtime or []) - manifest['tools'].keys()
    if unknown:
        raise ValueError('Unknown runtime: ' + ', '.join(sorted(unknown)))
    harnesses = list(dict.fromkeys(args.harness or PROFILES[args.profile]['harnesses']))
    runtimes = list(dict.fromkeys(args.runtime or manifest['tools']))
    target = args.target.expanduser().resolve()
    workspace = (args.workspace or ROOT).expanduser().resolve()
    copilot = PROFILES[args.profile]['copilot'] if args.copilot is None else args.copilot
    common = ['--target', str(target), '--scope', args.scope]
    for harness in harnesses:
        common += ['--harness', harness]
    return target, workspace, harnesses, runtimes, copilot, common


def initialization_roots(target, workspace, scope):
    primary = state_root('user') if scope == 'home' and target.resolve() == Path.home().resolve() else state_root('workspace', project=target)
    roots = list(dict.fromkeys((primary, state_root('workspace', project=workspace))))
    if any(path.exists() and not path.is_dir() for path in roots):
        raise ValueError('A selected .tkstack state root is not a directory')
    return roots


def execute(arguments, environment, log=None, timeout=120):
    output = log.open('w') if log else subprocess.PIPE
    try:
        process = subprocess.Popen(arguments, env=environment, cwd=ROOT, stdout=output,
                                   stderr=subprocess.STDOUT, text=True, start_new_session=True)
        try:
            stdout, _ = process.communicate(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
        if process.returncode:
            raise ValueError(f'{Path(arguments[2]).name} exited {process.returncode}; inspect {log}' if log else (stdout or 'Command failed').strip())
        return subprocess.CompletedProcess(arguments, process.returncode, stdout=stdout)
    finally:
        if log:
            output.close()


def runtime_status(environment):
    result = execute(command('setup_integrations.py', '--status'), environment)
    return json.loads(result.stdout)


def requirements(status, selected, offline):
    result = []
    for name in selected:
        value = status.get(name, {})
        if value.get('runtime') not in ('available', None):
            result.append({'integration': name, 'kind': 'runtime', 'status': 'deferred' if offline else 'missing',
                           'action': 'Set OPEN_DESIGN_CLI to the official executable and make its daemon available.' if name == 'open-design' else 'Install the declared runtime or inspect its failure log.'})
    if status.get('ponytail', {}).get('runtime') == 'node-missing':
        result.append({'integration': 'ponytail', 'kind': 'prerequisite', 'action': 'Provide Node.js/npm.'})
    if status.get('stitch', {}).get('credential_environment') != 'present':
        result.append({'integration': 'stitch', 'kind': 'credential', 'action': 'Supply STITCH_API_KEY; rerun setup to register its MCP connection.'})
    if status.get('headroom', {}).get('runtime') == 'available':
        result.append({'integration': 'headroom', 'kind': 'service', 'blocking': False, 'action': 'CCR operations need its separately started proxy; bootstrap does not change provider routing.'})
    result.append({'integration': 'fal', 'kind': 'host-authentication', 'blocking': False, 'action': 'Complete OAuth in the harness when required; setup does not sign in.'})
    return result


@contextmanager
def ownership():
    lock = ensure_state(ROOT / '.tkstack/locks') / 'bootstrap.lock'
    if lock.is_symlink():
        raise ValueError('Bootstrap lock must be a regular file')
    with lock.open('a+') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('Another bootstrap owns this checkout; retry after it finishes') from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def run(args):
    manifest = json.loads((ROOT / 'harnesses/integrations.json').read_text())
    target, workspace, harnesses, selected, copilot, common = selection(args, manifest)
    state_roots = initialization_roots(target, workspace, args.scope)
    environment, toolchains = bootstrap_toolchains.resolve(ROOT, install=False)
    report = {'version': 1, 'profile': args.profile, 'target': str(target), 'workspace': str(workspace), 'scope': args.scope,
              'harnesses': harnesses, 'selected_runtimes': selected, 'copilot': copilot, 'toolchains': toolchains,
              'state_roots': [str(path) for path in state_roots], 'offline': args.offline, 'stages': {}, 'runtime_failures': {}, 'requirements': [], 'status': 'planned'}
    install.verify_vendor(ROOT)
    check_codify_release(check=True)
    # Preflight existing destinations before initialization or network effects.
    execute(command('install.py', *common, '--dry-run'), environment)
    if copilot:
        execute(command('setup_lever.py', '--target', workspace, '--dry-run'), environment)
    shell_changes = bootstrap_shell.shell_plan(ROOT, target, args.scope, not args.no_shell)
    import runner_install
    for state in dict.fromkeys([ROOT / '.tkstack', *state_roots]):
        runner_install.plan(ROOT, state)
    import setup_repo_hooks
    setup_repo_hooks.setup(ROOT, dry_run=True)
    report['shell_files'] = [str(path) for path, _, _ in shell_changes]
    report['stages']['preflight'] = 'passed'
    if args.dry_run:
        report['requirements'] = requirements(runtime_status(environment), selected, args.offline)
        print(json.dumps(report, indent=2))
        return 0
    if args.check:
        errors = ['Shell startup pointers are missing or stale'] if shell_changes else []
        try:
            setup_repo_hooks.setup(ROOT, check=True)
        except (OSError, ValueError) as error:
            errors.append(str(error))
        for state in dict.fromkeys([ROOT / '.tkstack', *state_roots]):
            try:
                runner_install.check(ROOT, state)
            except (OSError, ValueError) as error:
                errors.append(str(error))
        try:
            bootstrap_shell.check(ROOT)
        except (OSError, ValueError) as error:
            errors.append(str(error))
        for arguments in [command('doctor.py', *common), *([command('setup_lever.py', '--target', workspace, '--check')] if copilot else [])]:
            try:
                execute(arguments, environment)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                errors.append(str(error))
        status = runtime_status(environment)
        report['requirements'] = requirements(status, selected, args.offline)
        required_missing = [name for name in selected if manifest['tools'][name]['kind'] != 'external' and status[name].get('runtime') == 'missing']
        report['status'] = 'invalid' if errors or (required_missing and not args.offline) or (args.strict and any(item.get('blocking', True) for item in report['requirements'])) else 'verified'
        report['verification_errors'] = errors
        print(json.dumps(report, indent=2))
        return int(report['status'] == 'invalid')
    with ownership():
        identity = 'bootstrap-' + uuid.uuid4().hex
        session = ensure_state(ROOT / '.tkstack/sessions' / identity)
        (session / 'session.json').write_text(json.dumps({'version': 1, 'id': identity, 'scope': 'workspace', 'status': 'active', 'purpose': 'Dotfiles bootstrap: ' + args.profile}) + '\n')
        report['session'] = identity
        errors = []
        try:
            if not args.offline and not args.no_toolchains:
                print('Preparing private startup prerequisites...', flush=True)
                try:
                    environment, report['toolchains'] = bootstrap_toolchains.resolve(ROOT, install=True)
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    errors.append('toolchains: ' + str(error))
            if not args.offline:
                automatic = [name for name in selected if manifest['tools'][name]['kind'] not in ('external', 'vendored-python', 'vendored-node')]
                def worker(name):
                    log = session / (name + '.log')
                    execute(command('setup_integrations.py', '--install-runtimes', '--runtimes-only', '--runtime', name),
                            environment, log, args.runtime_timeout)
                    return name
                with ThreadPoolExecutor(max_workers=min(args.jobs, len(automatic) or 1)) as pool:
                    futures = {pool.submit(worker, name): name for name in automatic}
                    for future in as_completed(futures):
                        name = futures[future]
                        try:
                            future.result()
                            print('Runtime ready: ' + name, flush=True)
                        except (OSError, ValueError, subprocess.SubprocessError) as error:
                            report['runtime_failures'][name] = str(error)
                            print('Runtime failed: ' + name + ' (see session log)', flush=True)
            report['runtime_failures'] = dict(sorted(report['runtime_failures'].items()))
            env_file = bootstrap_shell.publish(ROOT, environment)
            bootstrap_shell.apply_shell(shell_changes)
            environment = with_paths(ROOT, environment)
            report['environment_file'] = str(env_file)
            # Only one configuration writer runs after all independent runtime workers finish.
            execute(command('install.py', *common), environment, session / 'install.log')
            report['stages']['installation'] = 'passed'
            for root in state_roots:
                install.initialize_state(ROOT, state_root=root)
            report['stages']['initialization'] = 'passed'
            report['repository_hooks'] = setup_repo_hooks.setup(ROOT)
            if copilot:
                execute(command('setup_lever.py', '--target', workspace), environment, session / 'copilot.log')
                execute(command('setup_lever.py', '--target', workspace, '--check'), environment, session / 'copilot-check.log')
                report['stages']['copilot'] = 'passed'
            execute(command('doctor.py', *common), environment, session / 'doctor.log')
            report['stages']['verification'] = 'passed'
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            errors.append(str(error))
        try:
            status = runtime_status(environment)
            report['runtime_status'] = {name: status[name] for name in selected}
            report['requirements'] = requirements(status, selected, args.offline)
            if not args.offline:
                for name in selected:
                    if manifest['tools'][name]['kind'] not in ('external',) and status[name].get('runtime') == 'missing' and name not in report['runtime_failures']:
                        errors.append('Runtime is not ready: ' + name)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            errors.append('status: ' + str(error))
        report['verification_errors'] = errors
        report['status'] = ('failed' if errors or report['runtime_failures'] or (args.strict and any(item.get('blocking', True) for item in report['requirements'])) else
                            'configured-with-requirements' if any(item.get('blocking', True) for item in report['requirements']) else 'ready')
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        session_metadata = json.loads((session / 'session.json').read_text())
        session_metadata['status'] = 'closed'
        (session / 'session.json').write_text(json.dumps(session_metadata) + '\n')
        destination = ensure_state(ROOT / '.tkstack/bootstrap/installations') / (hashlib.sha256(str(target).encode()).hexdigest()[:16] + '.json')
        report['report_path'] = str(destination)
        temporary = session / 'report.json'
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        staged = destination.with_suffix('.pending')
        staged.write_bytes(temporary.read_bytes())
        staged.replace(destination)
        print(json.dumps(report, indent=2))
        return int(report['status'] == 'failed')


def main():
    args = parser().parse_args()
    try:
        return run(args)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('tkstack bootstrap: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
