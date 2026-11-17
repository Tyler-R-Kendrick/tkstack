"""Bounded sequential adapter from explicit request files to the experiment CLI."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from urllib.parse import quote

MAX_REQUESTS = 16
MAX_REQUEST_BYTES = 256 * 1024
MAX_RESULT_BYTES = 1024 * 1024
ACTIONS = frozenset({
    "init", "status", "allocate", "freeze", "run", "compare", "promote",
    "recover", "recover-run", "retire", "feedback", "calibrate", "revise",
    "regrade", "regrade-capture", "select", "confirm", "calibration-run", "handoff", "propose",
    "parallel", "parallel-status", "parallel-recover",
})


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _json(data):
    def invalid(value):
        raise ValueError(f"non-finite JSON value: {value}")
    return json.loads(data, object_pairs_hook=_pairs, parse_constant=invalid)


def _active_target(root):
    database = root / "ledger.sqlite3"
    if not database.is_file():
        raise ValueError("experiment root has no ledger")
    uri = "file:" + quote(str(database), safe="/") + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        row = db.execute("SELECT digest, path FROM controller_config WHERE id=1").fetchone()
    if not row:
        raise ValueError("experiment has no active configuration")
    config_path = (root / row[1]).resolve(strict=True)
    if not config_path.is_relative_to(root):
        raise ValueError("active configuration escapes experiment root")
    data = config_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != row[0]:
        raise ValueError("experiment configuration digest changed")
    return _json(data)["target"]


def prepare(request_dir, root, target, request_paths):
    """Validate the whole input list and snapshot its bytes before effects."""
    request_dir = Path(request_dir).resolve(strict=True)
    root = Path(root).resolve()
    if not request_dir.is_dir():
        raise ValueError("request directory is not a directory")
    if not isinstance(target, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", target):
        raise ValueError("a valid selected target is required")
    if not isinstance(request_paths, list) or not 1 <= len(request_paths) <= MAX_REQUESTS:
        raise ValueError(f"provide between 1 and {MAX_REQUESTS} request files")
    if any(not isinstance(name, str) or not name for name in request_paths):
        raise ValueError("request paths must be nonempty strings")
    if root.exists() and _active_target(root) != target:
        raise ValueError("selected target does not match the active experiment")
    seen = set()
    snapshots = []
    for relative in request_paths:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("request path must stay inside the request directory")
        resolved = (request_dir / path).resolve(strict=True)
        if not resolved.is_relative_to(request_dir) or not resolved.is_file() or resolved in seen:
            raise ValueError("request path escapes, duplicates, or is not a file")
        seen.add(resolved)
        raw = resolved.read_bytes()
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("request file exceeds the size limit")
        request = _json(raw)
        if not isinstance(request, dict) or request.get("action") not in ACTIONS:
            raise ValueError("request must specify a supported experiment action")
        if not isinstance(request.get("root"), str) or Path(request["root"]).resolve() != root:
            raise ValueError("request root does not match the selected experiment")
        if request["action"] == "init" and request.get("target") != target:
            raise ValueError("init target does not match the selected target")
        if request["action"] == "revise" and "registry" in request:
            registry = request["registry"]
            if not isinstance(registry, dict) or set(registry) not in ({target}, set()):
                raise ValueError("revised registry must retain the selected target")
        snapshots.append((relative, raw, hashlib.sha256(raw).hexdigest(), request["action"]))
    return snapshots


def _outcome(action, value):
    if not isinstance(value, dict):
        raise ValueError("controller response must be a JSON object")
    if action in ("run", "calibration-run") and value.get("result", {}).get("status") != "passed":
        raise ValueError("trial did not pass")
    if action == "parallel" and value.get("status") != "complete":
        raise ValueError("parallel batch is incomplete")
    if action == "propose" and value.get("status") != "frozen":
        raise ValueError("proposal did not freeze an arm")
    if action == "regrade-capture" and value.get("result", {}).get("decision") != "complete":
        raise ValueError("regrade capture is incomplete")
    if action == "handoff" and value.get("state") != "staged":
        raise ValueError("handoff did not stage the evaluated tree")
    if action == "compare" and value.get("decision") != "eligible":
        raise ValueError("comparison is not eligible")
    if action == "confirm" and value.get("decision", value.get("result", {}).get("decision")) != "eligible":
        raise ValueError("confirmation is not eligible")
    if action == "calibrate" and value.get("qualified") is not True:
        raise ValueError("calibration is not qualified")
    if action in ("recover", "recover-run") and value.get("state", value.get("status")) not in ("completed", "settled"):
        raise ValueError("recovery remains unresolved")
    if action == "regrade" and value.get("decision") != "complete":
        raise ValueError("regrading is incomplete")


def _run(request_dir, root, target, request_paths, controller, timeout):
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
        raise ValueError("timeout must be greater than zero and at most 3600 seconds")
    snapshots = prepare(request_dir, root, target, request_paths)
    if timeout < 120 and any(item[3] in ("run", "calibration-run", "parallel", "propose") for item in snapshots):
        raise ValueError("run actions require a wrapper timeout of at least 120 seconds")
    controller = Path(controller).resolve(strict=True)
    receipts = []
    with tempfile.TemporaryDirectory(prefix="tkstack-maf-requests-") as temp:
        temp = Path(temp)
        for index, (relative, raw, request_hash, action) in enumerate(snapshots):
            snapshot = temp / (str(index) + ".json")
            snapshot.write_bytes(raw)
            with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                try:
                    result = subprocess.run(
                        [sys.executable, str(controller), "--request", str(snapshot)],
                        stdout=out, stderr=err, timeout=timeout, check=False,
                    )
                except subprocess.TimeoutExpired as error:
                    raise ValueError(
                        f"stage {index} ({action}) timed out; reconcile its effects and inspect descendant processes"
                    ) from error
                if out.tell() > MAX_RESULT_BYTES or err.tell() > MAX_RESULT_BYTES:
                    raise ValueError(f"stage {index} ({action}) output exceeds the limit")
                out.seek(0)
                err.seek(0)
                stdout, stderr = out.read(), err.read()
            if result.returncode:
                detail = stderr.decode("utf-8", "replace").strip()
                raise ValueError(f"stage {index} ({action}) failed: {detail}")
            try:
                response = _json(stdout)
                _outcome(action, response)
            except (ValueError, TypeError, KeyError) as error:
                raise ValueError(f"stage {index} ({action}) failed: {error}") from error
            receipts.append({"index": index, "action": action, "request": relative,
                             "request_sha256": request_hash, "response": response})
    return receipts


async def execute_requests(request_dir, root, target, request_paths, controller, timeout):
    """Execute sequentially and return ordered controller receipts."""
    return await asyncio.to_thread(_run, request_dir, root, target, request_paths, controller, timeout)
