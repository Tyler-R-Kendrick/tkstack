"""Run a registered command against an immutable Git tree.

The export and the working directory are private to this trial.  This local
runner is not a security sandbox: commands can access the host and network.
Use a properly isolated runner for untrusted commands or source code.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
import math
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import subprocess
import sys
import threading
import tempfile
import time


_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_TARGET = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_MAX_SOURCE_BYTES = 512 * 1024 * 1024
_MAX_SOURCE_FILES = 100_000
_MAX_OUTPUT_BYTES = 4 * 1024 * 1024
class _Cancellation:
    def __init__(self):
        self.active = {}
        self.lock = threading.RLock()
        self.cancelled = threading.Event()


_SCOPE = contextvars.ContextVar('trial_cancellation', default=None)


@contextmanager
def cancellation_scope():
    token = _SCOPE.set(_Cancellation())
    try:
        yield
    finally:
        _SCOPE.reset(token)


def cancellation_requested():
    scope = _SCOPE.get()
    return scope is not None and scope.cancelled.is_set()


def launch_permitted(registered: bool, cancelled: bool) -> bool:
    return registered and not cancelled


def cancel_active_trials():
    """Ask all registered local trial groups to stop, including batch workers."""
    scope = _SCOPE.get()
    if scope is not None:
        with scope.lock:
            scope.cancelled.set()
            for process in scope.active.values():
                try:
                    if os.name == 'posix':
                        os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                        os.killpg(process.pid, signal.SIGTERM)
                    else:
                        process.terminate()
                except ChildProcessError:
                    process.returncode = 255
                except ProcessLookupError:
                    pass


def _relative_path(value: str, *, allow_dot: bool = False) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ValueError("path must be a nonempty relative POSIX path")
    if value == "." and allow_dot:
        return PurePosixPath(".")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("..", ".git") for part in path.parts):
        raise ValueError("path must stay inside the exported tree")
    if path == PurePosixPath("."):
        raise ValueError("path must name an entry")
    return path


def _validate(registry, allowed_targets, target, timeout, max_output_bytes):
    if not isinstance(registry, dict) or not isinstance(target, str) or not _TARGET.fullmatch(target):
        raise ValueError("invalid target registry or target name")
    if not isinstance(allowed_targets, (list, tuple, set, frozenset)) or not all(
        isinstance(name, str) and _TARGET.fullmatch(name) for name in allowed_targets
    ):
        raise ValueError("allowed_targets must contain valid target names")
    if target not in allowed_targets or target not in registry:
        raise ValueError("target is unknown or not allowed for this task")
    entry = registry[target]
    if not isinstance(entry, dict) or set(entry) != {"argv", "cwd"}:
        raise ValueError("target must contain exactly argv and cwd")
    argv = entry["argv"]
    if not isinstance(argv, list) or not argv or any(
        not isinstance(arg, str) or "\x00" in arg for arg in argv
    ) or not argv[0]:
        raise ValueError("target argv must be a nonempty string array with an executable")
    cwd = _relative_path(entry["cwd"], allow_dot=True)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number")
    if type(max_output_bytes) is not int or not 0 <= max_output_bytes <= _MAX_OUTPUT_BYTES:
        raise ValueError("max_output_bytes is outside the supported range")
    return list(argv), cwd


def _git_env():
    # Keep ambient Git config, overrides and credentials out of source export.
    return {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": os.devnull,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "LC_ALL": "C",
    }


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True,
        env=_git_env(), timeout=60, check=False,
    )
    if result.returncode:
        raise RuntimeError("git failed: " + result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def _materialize(repo: Path, commit: str, root: Path):
    """Stream raw tracked Git blobs, avoiding archive attribute transformations."""
    listing = _git(repo, "ls-tree", "-rz", "--full-tree", commit)
    records = []
    for record in listing.split(b"\0"):
        if not record:
            continue
        metadata, separator, raw_name = record.partition(b"\t")
        fields = metadata.split(b" ")
        if not separator or len(fields) != 3:
            raise RuntimeError("invalid Git tree record")
        mode, kind, object_id = fields
        if kind != b"blob" or mode not in (b"100644", b"100755", b"120000"):
            raise RuntimeError("unsupported Git tree entry (submodules require explicit materialization)")
        try:
            name = os.fsdecode(raw_name)
            path = _relative_path(name)
        except ValueError as exc:
            raise RuntimeError("unsafe path in Git tree") from exc
        records.append((mode, object_id.decode("ascii"), path))
        if len(records) > _MAX_SOURCE_FILES:
            raise RuntimeError("source tree exceeds file limit")

    requests = b"".join(object_id.encode("ascii") + b"\n" for _, object_id, _ in records)
    check = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch-check"], input=requests,
        capture_output=True, env=_git_env(), timeout=60, check=False,
    )
    headers = check.stdout.splitlines()
    if check.returncode or len(headers) != len(records):
        raise RuntimeError("could not inspect frozen Git blobs")
    total = 0
    for (_, object_id, _), header in zip(records, headers):
        fields = header.split(b" ")
        if len(fields) != 3 or fields[0] != object_id.encode("ascii") or fields[1] != b"blob":
            raise RuntimeError("could not inspect frozen Git blob")
        try:
            size = int(fields[2])
        except ValueError as exc:
            raise RuntimeError("invalid frozen Git blob size") from exc
        if size < 0 or total + size > _MAX_SOURCE_BYTES:
            raise RuntimeError("source tree exceeds size limit")
        total += size

    # Bound Git execution and avoid buffering tree contents in Python memory.
    # --batch-check above caps the maximum output before this second Git call.
    with tempfile.TemporaryFile() as blob_data:
        process = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "--batch"], input=requests,
            stdout=blob_data, stderr=subprocess.PIPE, env=_git_env(),
            timeout=60, check=False,
        )
        if process.returncode:
            raise RuntimeError("git cat-file failed")
        blob_data.seek(0)
        links = []
        for mode, object_id, relative in records:
            header = blob_data.readline(256)
            fields = header.rstrip(b"\n").split(b" ")
            if len(fields) != 3 or fields[0] != object_id.encode("ascii") or fields[1] != b"blob":
                raise RuntimeError("could not read frozen Git blob")
            size = int(fields[2])
            destination = root.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if mode == b"120000":
                if size > 4096:
                    raise RuntimeError("symlink target exceeds size limit")
                content = blob_data.read(size)
                links.append((destination, content))
            else:
                with destination.open("xb") as output:
                    remaining = size
                    first = True
                    while remaining:
                        chunk = blob_data.read(min(remaining, 1024 * 1024))
                        if not chunk:
                            raise RuntimeError("truncated frozen Git blob")
                        if first and chunk.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                            raise RuntimeError("Git LFS content requires explicit materialization")
                        first = False
                        output.write(chunk)
                        remaining -= len(chunk)
                destination.chmod(0o755 if mode == b"100755" else 0o644)
            if blob_data.read(1) != b"\n":
                raise RuntimeError("truncated frozen Git blob")
        for destination, content in links:
            target = os.fsdecode(content)
            if not target or "\x00" in target or os.path.isabs(target):
                raise RuntimeError("unsafe symlink in source tree")
            destination.symlink_to(target)
        for destination, _ in links:
            try:
                destination.resolve().relative_to(root.resolve())
            except (ValueError, RuntimeError) as exc:
                raise RuntimeError("escaping or cyclic symlink in source tree") from exc



def _terminate(process, scope, *, graceful=False):
    if os.name == "posix":
        try:
            os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except ChildProcessError:
            with scope.lock:
                scope.active.pop(process.pid, None)
                process.returncode = 255
            raise RuntimeError('trial child ownership was lost')
        if graceful:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            # Allow a trusted wrapper to terminate its registered stage groups.
            # Keep this grace bounded and preserve the leader PID until SIGKILL.
            if _can_observe_unreaped():
                deadline = time.monotonic() + 0.5
                while time.monotonic() < deadline:
                    if _exited_without_reaping(process):
                        break
                    time.sleep(0.01)
            else:
                time.sleep(0.5)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    mask = None
    if os.name == 'posix' and hasattr(signal, 'pthread_sigmask') and threading.current_thread() is threading.main_thread():
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
    try:
        with scope.lock:
            scope.active.pop(process.pid, None)
            process.wait()
    finally:
        if mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def _can_observe_unreaped():
    return (os.name == "posix" and signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL and
            hasattr(signal, 'pthread_sigmask') and all(hasattr(os, name) for name in ("waitid", "P_PID", "WEXITED", "WNOHANG", "WNOWAIT")))


def _exited_without_reaping(process):
    # Preserve the leader PID until its remaining process group is killed.
    if os.name == 'posix':
        try:
            return os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
        except ChildProcessError:
            process.returncode = 255
            raise RuntimeError('trial child ownership was lost')
    return process.poll() is not None


def _stage_exec(fd, error_fd, argv):
    """Execute only after the parent has registered the new process group."""
    if hasattr(signal, 'pthread_sigmask'):
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
    os.set_inheritable(error_fd, False)
    try:
        permit = os.read(fd, 1)
    finally:
        os.close(fd)
    if permit != b'1':
        return 125
    try:
        os.execvpe(argv[0], argv, os.environ)
    except OSError as error:
        os.write(error_fd, str(error).encode('utf-8', 'replace')[:4096])
        return 127


def _execute(argv, cwd, home, timeout, maximum, snapshot_root):
    if os.name == 'posix' and not _can_observe_unreaped():
        raise RuntimeError('local trials require non-reaping POSIX process supervision')
    scope = _SCOPE.get() or _Cancellation()
    env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": str(home),
           "TMPDIR": str(home), "LC_ALL": "C"}
    env["TKSTACK_EXPERIMENT_SNAPSHOT_ROOT"] = str(snapshot_root.resolve())
    env["TKSTACK_MANAGED_PROCESS_GROUP"] = "1"
    if os.name == "nt" and "SystemRoot" in os.environ:
        env["SystemRoot"] = os.environ["SystemRoot"]
    process = None
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    counts = {"stdout": 0, "stderr": 0}
    selector = selectors.DefaultSelector()
    deadline = time.monotonic() + timeout
    timed_out = False
    read_fd = write_fd = launch_read = launch_write = None
    launch_error = bytearray()
    try:
        # A signal delivered in the main thread during Popen must not strand
        # a newly created session before its process is registered for cleanup.
        mask = None
        if (os.name == 'posix' and hasattr(signal, 'pthread_sigmask') and
                threading.current_thread() is threading.main_thread()):
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try:
            if os.name == 'posix':
                read_fd, write_fd = os.pipe()
                launch_read, launch_write = os.pipe()
                command = [sys.executable, '-B', str(Path(__file__).resolve()), '--stage-exec',
                           str(read_fd), str(launch_write), *argv]
                process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           start_new_session=True, pass_fds=(read_fd, launch_write))
                os.close(read_fd)
                read_fd = None
                os.close(launch_write)
                launch_write = None
            else:
                process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with scope.lock:
                scope.active[process.pid] = process
                if write_fd is not None:
                    if launch_permitted(scope.active.get(process.pid) is process, scope.cancelled.is_set()):
                        os.write(write_fd, b'1')
                    os.close(write_fd)
                    write_fd = None
        finally:
            if mask is not None:
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        if scope.cancelled.is_set():
            try:
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
            except ProcessLookupError:
                pass
        for name in captured:
            stream = getattr(process, name)
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        if launch_read is not None:
            os.set_blocking(launch_read, False)
            selector.register(launch_read, selectors.EVENT_READ, 'launch')
        while selector.get_map() or not _exited_without_reaping(process):
            remaining = deadline - time.monotonic()
            if scope.cancelled.is_set() or remaining <= 0:
                timed_out = True
                break
            for key, _ in selector.select(min(remaining, 0.1)):
                try:
                    data = os.read(key.fd, 65536)
                except BlockingIOError:
                    continue
                if not data:
                    selector.unregister(key.fileobj)
                    if key.data == 'launch':
                        os.close(launch_read)
                        launch_read = None
                    continue
                name = key.data
                if name == 'launch':
                    launch_error.extend(data[:max(0, 4096 - len(launch_error))])
                    continue
                counts[name] += len(data)
                captured[name].extend(data[:max(0, maximum - len(captured[name]))])
        if timed_out or os.name == 'posix':
            _terminate(process, scope, graceful=timed_out)
        else:
            with scope.lock:
                scope.active.pop(process.pid, None)
                process.wait()
        result = {
            "status": "timeout" if timed_out else ("infra_error" if launch_error else ("passed" if process.returncode == 0 else "failed")),
            "exit_code": None if timed_out else process.returncode,
            "stdout": captured["stdout"].decode("utf-8", "replace"),
            "stderr": captured["stderr"].decode("utf-8", "replace"),
            "stdout_bytes": counts["stdout"], "stderr_bytes": counts["stderr"],
            "stdout_truncated": counts["stdout"] > maximum,
            "stderr_truncated": counts["stderr"] > maximum,
        }
        if launch_error:
            result['error'] = launch_error.decode('utf-8', 'replace')
        return result
    finally:
        if read_fd is not None:
            os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        if launch_read is not None:
            os.close(launch_read)
        if launch_write is not None:
            os.close(launch_write)
        selector.close()
        if process is not None and process.returncode is None:
            _terminate(process, scope, graceful=True)
        if process is not None:
            with scope.lock:
                scope.active.pop(process.pid, None)
            process.stdout.close()
            process.stderr.close()


def run_trial(repo, commit, expected_tree, registry, allowed_targets, target, *,
              timeout=30, max_output_bytes=65536, deadline=None):
    """Run a named registered target on a frozen commit and return execution evidence.

    Invalid inputs raise ValueError. Materialization/launch errors return
    ``infra_error``; a timed out command returns ``timeout``. ``passed`` means
    exit code zero only, not a quality or acceptance decision. Output byte
    counts describe what the runner observed before exit/timeout. The timeout
    applies to command execution; Git export has its own 60-second subprocess
    limits. ``deadline`` is an optional absolute time.monotonic() deadline.
    If it expires before dispatch, return timeout without starting the command;
    otherwise the command timeout is capped to the remaining interval. This local adapter executes with host privileges and is not a sandbox.
    POSIX waitid(WNOWAIT) permits cleanup of same-group children on successful
    exit. Detached sessions and other platforms require an external supervisor.
    """
    argv, relative_cwd = _validate(registry, allowed_targets, target, timeout, max_output_bytes)
    if not isinstance(commit, str) or not _OBJECT_ID.fullmatch(commit):
        raise ValueError("commit must be a full lowercase Git object ID")
    if not isinstance(expected_tree, str) or not _OBJECT_ID.fullmatch(expected_tree):
        raise ValueError("expected_tree must be a full lowercase Git object ID")
    if deadline is not None and (isinstance(deadline, bool) or not isinstance(deadline, (int, float)) or not math.isfinite(deadline)):
        raise ValueError("deadline must be a finite monotonic timestamp")
    start = time.monotonic()
    result = {
        "status": "infra_error", "exit_code": None, "stdout": "", "stderr": "",
        "stdout_bytes": 0, "stderr_bytes": 0, "stdout_truncated": False,
        "stderr_truncated": False, "commit": commit, "tree": expected_tree,
        "target": target, "error": None,
    }
    try:
        if deadline is not None and time.monotonic() >= deadline:
            result["status"] = "timeout"
            result["error"] = "experiment deadline elapsed before dispatch"
            result["duration_seconds"] = time.monotonic() - start
            return result
        repo = Path(repo).resolve(strict=True)
        actual_commit = _git(repo, "rev-parse", "--verify", commit + "^{commit}").decode("ascii").strip()
        actual_tree = _git(repo, "rev-parse", "--verify", commit + "^{tree}").decode("ascii").strip()
        if actual_commit != commit or actual_tree != expected_tree:
            raise RuntimeError("frozen commit or tree identity does not match")
        with tempfile.TemporaryDirectory(prefix="tkstack-trial-") as temp:
            root = Path(temp) / "source"
            home = Path(temp) / "home"
            root.mkdir()
            home.mkdir()
            _materialize(repo, commit, root)
            cwd = root.joinpath(*relative_cwd.parts).resolve(strict=True)
            try:
                cwd.relative_to(root.resolve())
            except ValueError as exc:
                raise RuntimeError("target working directory escapes export") from exc
            if not cwd.is_dir():
                raise RuntimeError("target working directory is not a directory")
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    result["status"] = "timeout"
                    result["error"] = "experiment deadline elapsed before dispatch"
                    result["duration_seconds"] = time.monotonic() - start
                    return result
                timeout = min(timeout, remaining)
            result.update(_execute(argv, cwd, home, timeout, max_output_bytes, root))
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        result["status"] = "infra_error"
        result["error"] = str(exc)
    result["duration_seconds"] = time.monotonic() - start
    return result


if __name__ == '__main__':
    if len(sys.argv) < 5 or sys.argv[1] != '--stage-exec':
        raise SystemExit('invalid stage invocation')
    raise SystemExit(_stage_exec(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]))
