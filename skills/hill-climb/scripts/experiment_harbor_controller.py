"""Explicit Harbor backend bridge for the experiment controller.

A completed Harbor run is converted to the same measurement protocol used by
local runs. Backend selection, budgeting and settlement belong to the caller.
The adapter uses Oracle staging and never invokes a model.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re

from experiment_harbor import measurement_from_rewards, run_harbor_trial, verifier_digest
from json_contract import loads as strict_loads


_HASH = re.compile(r"[0-9a-f]{64}\Z")
_IMAGE = re.compile(r"(?:[A-Za-z0-9._:/-]+@)?sha256:[0-9a-f]{64}\Z")
_BACKEND_KEYS = {"kind", "verifier_dir", "verifier_sha256", "image", "harbor_bin",
                 "harbor_bin_sha256", "network_mode", "timeout_seconds"}


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_controller_harbor(backend, evaluator):
    """Verify pinned backend and its identity with the controller evaluator.

    Call at configuration freeze and before/after each trial and replay. The
    executable digest pins its entrypoint, not a Python environment's complete
    dependency set. Deploy Harbor in a separately locked environment.
    """
    if not isinstance(backend, dict) or set(backend) != _BACKEND_KEYS or backend["kind"] != "harbor":
        raise ValueError("invalid Harbor backend configuration")
    for key in ("verifier_sha256", "harbor_bin_sha256"):
        if not isinstance(backend[key], str) or not _HASH.fullmatch(backend[key]):
            raise ValueError("invalid Harbor backend digest")
    if not isinstance(backend["image"], str) or not _IMAGE.fullmatch(backend["image"]):
        raise ValueError("Harbor image must be pinned by SHA-256")
    if backend["network_mode"] not in ("no-network", "public"):
        raise ValueError("invalid Harbor network policy")
    timeout = backend["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("invalid Harbor timeout")
    if not isinstance(evaluator, dict) or set(evaluator) != {"path", "sha256"}:
        raise ValueError("invalid frozen evaluator identity")
    if not all(isinstance(backend[key], str) and Path(backend[key]).is_absolute()
               for key in ("verifier_dir", "harbor_bin")):
        raise ValueError("Harbor backend paths must be absolute")
    verifier = Path(backend["verifier_dir"]).resolve(strict=True)
    evaluator_path = Path(evaluator["path"]).resolve(strict=True)
    if evaluator_path != (verifier / "test.sh").resolve(strict=True):
        raise ValueError("frozen evaluator must be verifier_dir/test.sh")
    if _digest(evaluator_path) != evaluator["sha256"]:
        raise ValueError("frozen evaluator changed")
    if verifier_digest(verifier) != backend["verifier_sha256"]:
        raise ValueError("frozen Harbor verifier changed")
    binary = Path(backend["harbor_bin"]).resolve(strict=True)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError("Harbor executable is unavailable")
    if _digest(binary) != backend["harbor_bin_sha256"]:
        raise ValueError("frozen Harbor executable changed")
    return True


def run_controller_harbor(repo, commit, tree, backend, evaluator, allowed_targets,
                          target, case_file, case_sha256, run_dir, required_gates,
                          metric_names, *, deadline=None):
    """Execute the selected Harbor backend once and return local-runner fields.

    The caller must reserve and dispatch exactly once. It must retain an
    ``unknown`` result as uncertain and charged until independently reconciled.
    No fallback execution or automatic retry occurs here.
    """
    result = {
        "status": "infra_error", "exit_code": None, "stdout": "", "stderr": "",
        "stdout_bytes": 0, "stderr_bytes": 0, "stdout_truncated": False,
        "stderr_truncated": False, "commit": commit, "tree": tree,
        "target": target, "error": None, "duration_seconds": 0,
    }
    try:
        if not isinstance(allowed_targets, (list, tuple)) or list(allowed_targets) != [target]:
            raise ValueError("Harbor trial must name exactly the declared target")
        if not isinstance(target, str) or not target:
            raise ValueError("target is required")
        validate_controller_harbor(backend, evaluator)
    except (OSError, ValueError, TypeError) as exc:
        result["error"] = str(exc)
        return result
    try:
        native = run_harbor_trial(
            repo, commit, tree, backend["verifier_dir"], backend["verifier_sha256"],
            backend["image"], run_dir, case_file=case_file, expected_case_sha256=case_sha256,
            harbor_bin=backend["harbor_bin"], timeout=backend["timeout_seconds"],
            network_mode=backend["network_mode"], deadline=deadline,
        )
    except Exception as exc:
        # The boundary may have dispatched even if the adapter failed to return.
        result["status"] = "unknown"
        result["error"] = "Harbor adapter failed without a terminal receipt: " + str(exc)
        return result
    result["harbor"] = native
    result["duration_seconds"] = native.get("duration_seconds", 0)
    result["error"] = native.get("error")
    receipt = Path(run_dir) / "adapter-result.json"
    if receipt.is_file() and not receipt.is_symlink():
        result["harbor_receipt_sha256"] = _digest(receipt)
    if native.get("status") == "unknown":
        result["status"] = "unknown"
        return result
    if native.get("status") != "completed":
        result["status"] = "timeout" if native.get("status") == "timeout" else "infra_error"
        return result
    try:
        validate_controller_harbor(backend, evaluator)
        measurement = measurement_from_rewards(native, required_gates, metric_names)
        if native.get("commit") != commit or native.get("tree") != tree or measurement["case_sha256"] != case_sha256:
            raise ValueError("Harbor candidate or case identity changed")
        payload = json.dumps(measurement, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        result.update({"status": "passed", "exit_code": 0, "stdout": payload,
                       "stdout_bytes": len(payload.encode("utf-8")), "error": None})
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result["error"] = str(exc)
    return result


def verify_controller_harbor(result, backend, evaluator, *, case_sha256,
                             required_gates, metric_names):
    """Recheck all referenced Harbor receipts before using a measurement."""
    validate_controller_harbor(backend, evaluator)
    if not isinstance(result, dict) or result.get("status") != "passed" or result.get("exit_code") != 0:
        raise ValueError("Harbor result is not a completed measurement")
    native = result.get("harbor")
    if not isinstance(native, dict) or native.get("status") != "completed":
        raise ValueError("Harbor provenance missing")
    if (native.get("verifier_sha256") != backend["verifier_sha256"] or
            native.get("image") != backend["image"] or
            native.get("network_mode") != backend["network_mode"] or
            native.get("commit") != result.get("commit") or native.get("tree") != result.get("tree")):
        raise ValueError("Harbor provenance differs from frozen configuration")
    run_dir = Path(native["run_dir"]).resolve(strict=True)
    adapter_receipt = run_dir / "adapter-result.json"
    if adapter_receipt.is_symlink() or _digest(adapter_receipt) != result.get("harbor_receipt_sha256"):
        raise ValueError("Harbor adapter receipt changed")
    if strict_loads(adapter_receipt.read_bytes()) != native:
        raise ValueError("Harbor adapter receipt differs from recorded provenance")
    manifest = Path(native["artifact_manifest"])
    if (manifest.is_symlink() or not manifest.resolve(strict=True).is_relative_to(run_dir) or
            _digest(manifest) != native.get("artifact_manifest_sha256")):
        raise ValueError("Harbor artifact manifest changed")
    measurement = measurement_from_rewards(native, required_gates, metric_names)
    if measurement["case_sha256"] != case_sha256:
        raise ValueError("Harbor case differs from frozen assignment")
    stdout = result.get("stdout")
    if (not isinstance(stdout, str) or result.get("stdout_truncated") is not False or
            result.get("stdout_bytes") != len(stdout.encode("utf-8")) or
            strict_loads(stdout) != measurement):
        raise ValueError("Harbor measurement differs from receipt")
    return True
