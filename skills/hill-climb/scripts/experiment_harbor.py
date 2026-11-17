"""Run a frozen Git candidate through Harbor with a separate verifier container.

Harbor, its container engine, image, and verifier are supplied by the operator.
This adapter stages a candidate with Harbor's Oracle agent and makes no model
calls. Containers and the selected network policy provide their own isolation;
this adapter does not grant a host-level security boundary.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time

from experiment_runner import _execute, _git, _materialize
from json_contract import loads as strict_json_loads


_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_IMAGE = re.compile(r"(?:[A-Za-z0-9._:/-]+@)?sha256:[0-9a-f]{64}\Z")
_MAX_VERIFIER_BYTES = 16 * 1024 * 1024
_MAX_RECEIPT_BYTES = 4 * 1024 * 1024


class _DeadlineExpired(Exception):
    pass


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _remaining(deadline, timeout):
    if deadline is None:
        return timeout
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise _DeadlineExpired("experiment deadline elapsed before dispatch")
    return min(timeout, remaining)


def verifier_digest(verifier_dir):
    """Hash a trusted verifier directory's paths, file bytes and permission bits.

    Symbolic links, special files, and Harbor build definitions are rejected.
    The verifier image is selected separately and Harbor uploads these files to
    a fresh copy of that image. ``test.sh`` is required.
    """
    root = Path(verifier_dir).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("verifier must be a directory")
    digest = hashlib.sha256()
    total = 0
    seen = set()
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError("verifier cannot contain symlinks or special files")
        name = relative.encode("utf-8")
        digest.update(b"D" if path.is_dir() else b"F")
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update((path.stat().st_mode & 0o777).to_bytes(2, "big"))
        if path.is_dir():
            continue
        if relative in {"Dockerfile", "docker-compose.yaml", "docker-compose.yml", ".harborignore"}:
            raise ValueError("verifier build and ignore definitions are not supported")
        if path.stat().st_size > _MAX_VERIFIER_BYTES - total:
            raise ValueError("verifier exceeds size limit")
        data = path.read_bytes()
        total += len(data)
        if total > _MAX_VERIFIER_BYTES:
            raise ValueError("verifier exceeds size limit")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        seen.add(relative)
    if "test.sh" not in seen:
        raise ValueError("verifier requires test.sh")
    return digest.hexdigest()


def _read_receipt(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_RECEIPT_BYTES:
        raise ValueError("missing or oversized Harbor receipt")
    data = path.read_bytes()
    value = strict_json_loads(data)
    if not isinstance(value, dict):
        raise ValueError("invalid Harbor receipt")
    return value, hashlib.sha256(data).hexdigest()


def _collect(jobs, expected_task, run):
    job_dir = jobs / "candidate"
    if not job_dir.is_dir():
        raise ValueError("Harbor job directory missing")
    trial_dirs = [p for p in job_dir.iterdir() if p.is_dir() and (p / "result.json").is_file()]
    if len(trial_dirs) != 1:
        raise ValueError("Harbor must report exactly one completed trial")
    trial_dir = trial_dirs[0]
    result, result_sha256 = _read_receipt(trial_dir / "result.json")
    if result.get("schema_version", 1) != 1:
        raise ValueError("unsupported Harbor trial receipt version")
    if not result.get("finished_at") or result.get("step_results"):
        raise ValueError("Harbor trial did not finish as a single-step trial")
    task = result.get("task_id")
    if not isinstance(task, dict) or task.get("path") != str(expected_task):
        raise ValueError("Harbor task identity does not match")
    agent_info = result.get("agent_info")
    if not isinstance(agent_info, dict) or agent_info.get("name") != "oracle":
        raise ValueError("Harbor agent does not match")
    if result.get("verifier_environment_mode") != "separate":
        raise ValueError("Harbor did not run a separate verifier")
    if result.get("exception_info") is not None:
        raise ValueError("Harbor reported a trial exception")
    if result.get("reward_valid") is not True:
        raise ValueError("Harbor verifier reward is missing or invalid")
    verifier_result = result.get("verifier_result")
    if not isinstance(verifier_result, dict):
        raise ValueError("Harbor verifier result is malformed")
    rewards = verifier_result.get("rewards")
    if not isinstance(rewards, dict) or not rewards or any(
        not isinstance(k, str) or not _finite_number(v) for k, v in rewards.items()
    ):
        raise ValueError("Harbor verifier rewards are malformed")
    exit_file = trial_dir / "agent" / "exit-code.txt"
    if exit_file.exists() and exit_file.read_text().strip() != "0":
        raise ValueError("Harbor oracle could not stage the candidate")
    case_receipt = trial_dir / "verifier" / "case_sha256.txt"
    if case_receipt.is_symlink() or not case_receipt.is_file() or case_receipt.stat().st_size > 256:
        raise ValueError("Harbor verifier did not attest the selected case")
    actual_case = case_receipt.read_text(encoding="ascii").strip()
    if actual_case != run["case_sha256"]:
        raise ValueError("Harbor verifier case digest does not match")
    manifest_path = trial_dir / "artifacts" / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file() or manifest_path.stat().st_size > _MAX_RECEIPT_BYTES:
        raise ValueError("Harbor artifact manifest missing")
    manifest_bytes = manifest_path.read_bytes()
    manifest = strict_json_loads(manifest_bytes)
    if not isinstance(manifest, list) or not any(
        isinstance(entry, dict) and entry.get("source") == "/app/submission" and entry.get("status") == "ok"
        for entry in manifest
    ):
        raise ValueError("Harbor did not collect the candidate artifact")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    usage = result.get("agent_result")
    if not isinstance(usage, dict):
        raise ValueError("Harbor agent usage is malformed")
    if not isinstance(result.get("id"), str) or not result["id"]:
        raise ValueError("Harbor trial identifier is missing")
    run.update({
        "status": "completed", "rewards": rewards,
        "usage": {"input_tokens": usage.get("n_input_tokens"),
                  "cache_tokens": usage.get("n_cache_tokens"),
                  "output_tokens": usage.get("n_output_tokens"),
                  "cost_usd": usage.get("cost_usd"), "agent": "oracle"},
        "trial_result": str(trial_dir / "result.json"), "trial_result_sha256": result_sha256,
        "artifact_manifest": str(manifest_path), "artifact_manifest_sha256": manifest_sha256,
        "harbor_trial_id": result.get("id"), "case_receipt": str(case_receipt),
        "case_receipt_sha256": hashlib.sha256(case_receipt.read_bytes()).hexdigest(),
    })


def run_harbor_trial(repo, commit, expected_tree, verifier_dir, expected_verifier_sha256,
                     image, run_dir, *, case_file, expected_case_sha256, harbor_bin="harbor", timeout=120,
                     network_mode="no-network", max_output_bytes=65536, deadline=None):
    """Run one Oracle staging trial and return Harbor verifier evidence.

    The verifier must read /tests/case.input and write its SHA-256 to
    /logs/verifier/case_sha256.txt. A pre-existing run directory is refused.
    Timeout or failure after dispatch
    returns ``unknown`` if a terminal receipt cannot establish the outcome;
    caller must reconcile containers and spending before retrying. Completed
    rewards are observations, not an acceptance decision. The timeout applies
    to Harbor execution after staging. An optional monotonic deadline is
    rechecked after staging and bounds version probe and Harbor execution;
    Git export has separate subprocess timeouts. Supports Harbor's Docker
    backend and POSIX container images with bash, tar, and core utilities.
    """
    for name, value in (("commit", commit), ("expected_tree", expected_tree)):
        if not isinstance(value, str) or not _OID.fullmatch(value):
            raise ValueError(name + " must be a full lowercase object ID")
    if not isinstance(expected_verifier_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_verifier_sha256):
        raise ValueError("expected verifier digest must be SHA-256")
    if not isinstance(expected_case_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_case_sha256):
        raise ValueError("expected case digest must be SHA-256")
    if not isinstance(image, str) or not _IMAGE.fullmatch(image):
        raise ValueError("image must be pinned by sha256 digest")
    if network_mode not in ("no-network", "public"):
        raise ValueError("network_mode must be no-network or public")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    if type(max_output_bytes) is not int or not 0 <= max_output_bytes <= 4 * 1024 * 1024:
        raise ValueError("invalid output limit")
    if deadline is not None and (isinstance(deadline, bool) or not isinstance(deadline, (int, float)) or not math.isfinite(deadline)):
        raise ValueError("deadline must be a finite monotonic timestamp")
    if not isinstance(harbor_bin, str) or not harbor_bin or "\x00" in harbor_bin:
        raise ValueError("invalid Harbor executable")
    source = Path(repo).resolve(strict=True)
    destination = Path(run_dir).resolve(strict=False)
    if destination == source or source in destination.parents:
        raise ValueError("run directory must be outside the source repository")
    verifier_root = Path(verifier_dir).resolve(strict=True)
    if destination == verifier_root or verifier_root in destination.parents:
        raise ValueError("run directory must be outside the verifier directory")
    destination.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    run = {"status": "infra_error", "commit": commit, "tree": expected_tree,
           "verifier_sha256": expected_verifier_sha256, "image": image,
           "network_mode": network_mode, "case_sha256": expected_case_sha256, "rewards": None, "usage": None,
           "trial_result": None, "trial_result_sha256": None,
           "artifact_manifest": None, "artifact_manifest_sha256": None,
           "harbor_trial_id": None, "error": None, "run_dir": str(destination)}
    dispatched = False
    try:
        _remaining(deadline, timeout)
        binary = shutil.which(harbor_bin)
        if binary is None:
            run["status"] = "unavailable"
            run["error"] = "Harbor executable is unavailable"
            run["duration_seconds"] = time.monotonic() - start
            (destination / "adapter-result.json").write_text(json.dumps(run, sort_keys=True, indent=2) + "\n")
            return run
        actual_commit = _git(source, "rev-parse", "--verify", commit + "^{commit}").decode("ascii").strip()
        actual_tree = _git(source, "rev-parse", "--verify", commit + "^{tree}").decode("ascii").strip()
        if actual_commit != commit or actual_tree != expected_tree:
            raise RuntimeError("frozen commit or tree does not match")
        if verifier_digest(verifier_dir) != expected_verifier_sha256:
            raise RuntimeError("verifier digest does not match")
        with tempfile.TemporaryDirectory(prefix="harbor-trial-", dir=destination) as scratch_name:
            scratch = Path(scratch_name)
            task = scratch / "task"
            solution = task / "solution"
            solution.mkdir(parents=True)
            tests = task / "tests"
            shutil.copytree(verifier_dir, tests, symlinks=True)
            if verifier_digest(tests) != expected_verifier_sha256:
                raise RuntimeError("verifier changed while copying")
            selected_case = Path(case_file)
            if selected_case.is_symlink() or not selected_case.is_file() or selected_case.stat().st_size > _MAX_VERIFIER_BYTES:
                raise RuntimeError("selected case is missing, oversized, or a symlink")
            case_bytes = selected_case.read_bytes()
            if len(case_bytes) > _MAX_VERIFIER_BYTES or hashlib.sha256(case_bytes).hexdigest() != expected_case_sha256:
                raise RuntimeError("selected case digest does not match")
            if (tests / "case.input").exists():
                raise RuntimeError("verifier reserves case.input for the selected case")
            (tests / "case.input").write_bytes(case_bytes)
            candidate = scratch / "source"
            candidate.mkdir()
            _materialize(source, commit, candidate)
            with tarfile.open(solution / "source.tar", "w") as archive:
                for item in sorted(candidate.iterdir()):
                    archive.add(item, arcname=item.name, recursive=True)
            (solution / "solve.sh").write_text(
                "#!/bin/sh\nset -eu\nmkdir -p /app/submission\ntar -xf /solution/source.tar -C /app/submission\n"
            )
            (task / "instruction.md").write_text("Stage the frozen candidate for independent verification.\n")
            (task / "task.toml").write_text(
                'artifacts = ["/app/submission"]\n'
                '[agent]\ntimeout_sec = 60\n'
                '[verifier]\nenvironment_mode = "separate"\ntimeout_sec = 60\n'
                f'network_mode = "{network_mode}"\n'
                f'[environment]\ndocker_image = "{image}"\nnetwork_mode = "{network_mode}"\n'
            )
            jobs = destination / "jobs"
            jobs.mkdir()
            config = {
                "job_name": "candidate", "jobs_dir": str(jobs), "n_attempts": 1,
                "n_concurrent_trials": 1, "retry": {"max_retries": 0},
                "agents": [{"name": "oracle"}], "tasks": [{"path": str(task)}],
                "environment": {"type": "docker"}, "quiet": True,
            }
            config_path = destination / "config.json"
            config_path.write_text(json.dumps(config, sort_keys=True, indent=2) + "\n")
            private_home = scratch / "home"
            private_home.mkdir()
            version = _execute([binary, "--version"], scratch, private_home, _remaining(deadline, 30), 1024, scratch)
            if version["status"] == "timeout" and deadline is not None:
                _remaining(deadline, timeout)
            if version["status"] == "timeout":
                raise RuntimeError("Harbor version probe timed out")
            if version["status"] != "passed" or version["stdout"].strip() != "0.26.0":
                raise RuntimeError("Harbor 0.26.0 is required for this adapter")
            run["harbor_version"] = "0.26.0"
            execution_timeout = _remaining(deadline, timeout)
            (destination / "dispatch-intent.json").write_text(json.dumps({
                "state": "dispatching", "commit": commit, "tree": expected_tree,
                "verifier_sha256": expected_verifier_sha256, "case_sha256": expected_case_sha256, "image": image,
            }, sort_keys=True, indent=2) + "\n")
            execution_timeout = _remaining(deadline, execution_timeout)
            dispatched = True
            process_result = _execute([binary, "run", "-c", str(config_path)], scratch,
                                      private_home, execution_timeout, max_output_bytes, scratch)
            run["process"] = process_result
            if process_result["status"] == "timeout":
                run["status"] = "unknown"
                run["error"] = "Harbor timed out after dispatch; containers may still be running"
            elif process_result["status"] != "passed":
                run["status"] = "unknown"
                run["error"] = "Harbor exited unsuccessfully after dispatch"
            else:
                try:
                    _collect(jobs, task, run)
                except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                    # Once launched, an incomplete or failed receipt cannot establish
                    # that no backend work remains. Retain the reservation.
                    run["status"] = "unknown"
                    run["error"] = str(exc)
    except _DeadlineExpired as exc:
        run["status"] = "unknown" if dispatched else "timeout"
        run["error"] = str(exc)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        run["status"] = "unknown" if dispatched else "infra_error"
        run["error"] = str(exc)
    run["duration_seconds"] = time.monotonic() - start
    (destination / "adapter-result.json").write_text(json.dumps(run, sort_keys=True, indent=2) + "\n")
    return run



def measurement_from_rewards(run, required_gates, metric_names):
    """Translate a completed Harbor reward receipt to controller measurement JSON.

    The verifier must emit a numeric ``work_count`` and each explicitly named
    gate and metric in reward.json. Gates must be exactly 0 or 1. Any missing,
    malformed or non-finite value raises ValueError. This establishes shape and
    receipt identity, not that an evaluator's substantive judgment is correct.
    """
    if not isinstance(run, dict) or run.get("status") != "completed":
        raise ValueError("Harbor trial did not complete")
    if not isinstance(required_gates, list) or not required_gates or not isinstance(metric_names, list) or not metric_names:
        raise ValueError("gate and metric names must be nonempty lists")
    names = required_gates + metric_names
    if any(not isinstance(name, str) or not name or name == "work_count" for name in names) or len(set(names)) != len(names):
        raise ValueError("gate and metric names must be unique nonempty strings")
    case_digest = run.get("case_sha256")
    if not isinstance(case_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", case_digest):
        raise ValueError("case digest missing")
    receipt = Path(run.get("case_receipt", ""))
    root = Path(run.get("run_dir", "")).resolve(strict=True)
    if receipt.is_symlink() or not receipt.is_file() or not receipt.resolve().is_relative_to(root):
        raise ValueError("case receipt missing or outside run directory")
    data = receipt.read_bytes()
    if len(data) > 256 or hashlib.sha256(data).hexdigest() != run.get("case_receipt_sha256") or data.decode("ascii").strip() != case_digest:
        raise ValueError("case receipt does not match")
    result_path = Path(run.get("trial_result", ""))
    if result_path.is_symlink() or not result_path.is_file() or not result_path.resolve().is_relative_to(root):
        raise ValueError("trial result missing or outside run directory")
    trial, trial_digest = _read_receipt(result_path)
    if trial_digest != run.get("trial_result_sha256") or trial.get("id") != run.get("harbor_trial_id"):
        raise ValueError("trial receipt does not match")
    if trial.get("reward_valid") is not True or trial.get("exception_info") is not None or trial.get("verifier_environment_mode") != "separate":
        raise ValueError("trial verifier is not eligible")
    rewards = run.get("rewards")
    verifier_result = trial.get("verifier_result")
    if not isinstance(rewards, dict) or not isinstance(verifier_result, dict) or rewards != verifier_result.get("rewards"):
        raise ValueError("rewards do not match the trial receipt")
    for name in names + ["work_count"]:
        value = rewards.get(name)
        if not _finite_number(value):
            raise ValueError("missing or non-finite reward: " + name)
    if any(rewards[name] not in (0, 1) for name in required_gates):
        raise ValueError("gates must be 0 or 1")
    if rewards["work_count"] <= 0:
        raise ValueError("work_count must be positive")
    return {"case_sha256": case_digest, "gates": {name: bool(rewards[name]) for name in required_gates},
            "metrics": {name: rewards[name] for name in metric_names}, "work_count": rewards["work_count"]}
