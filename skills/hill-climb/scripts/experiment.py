#!/usr/bin/env python3
"""Run a small, Git-backed experiment against one registered local target.

The local target executes with host privileges. Treat its verifier and configuration
as trusted, and use an external sandbox for untrusted code.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import time
import math

from json_contract import loads as strict_json_loads
from experiment_git import GitExperiment, _paths, _run
from experiment_ledger import Ledger
from experiment_runner import run_trial
from experiment_harbor_controller import (run_controller_harbor, validate_controller_harbor, verify_controller_harbor)
from experiment_evaluate import _validate_spec, compare, feedback_revision, regrade_matrix, validate_calibration
from experiment_agent_arm import propose_to_arm
from experiment_proposer import ProposalRunner, ScriptedProvider


_BACKEND_UNSET = object()

IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def name(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError("identifier must contain only letters, numbers, hyphen and underscore")
    return value


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_evaluation_fields(evaluation):
    allowed = {"case", "cases", "repetitions", "required_gates", "candidate_only_gates",
               "required_qualitative", "metric", "direction", "min_gain", "noise_floor",
               "deterministic", "guardrails"}
    if not isinstance(evaluation, dict) or set(evaluation) - allowed:
        raise ValueError("unknown or reserved evaluation fields")


def validate_target(registry, target, evaluator, trusted_interpreter=None):
    if not isinstance(registry, dict) or set(registry) != {target}:
        raise ValueError("register exactly the selected target")
    entry = registry[target]
    if (not isinstance(entry, dict) or set(entry) != {"argv", "cwd"} or
            not isinstance(entry["argv"], list) or not entry["argv"] or
            any(not isinstance(arg, str) or not arg or "\x00" in arg for arg in entry["argv"])):
        raise ValueError("target requires a nonempty argument vector and cwd")
    args = list(entry["argv"])
    executable = shutil.which(args[0])
    if executable is None:
        raise ValueError("target executable is unavailable")
    executable = str(Path(executable).resolve(strict=True))
    evaluator = str(Path(evaluator).resolve(strict=True))
    if executable != evaluator:
        if (trusted_interpreter is None or
                str(Path(trusted_interpreter).resolve(strict=True)) != executable or
                len(args) < 2 or str(Path(args[1]).resolve()) != evaluator):
            raise ValueError("evaluator must be executable or the immediate argument of an explicitly trusted interpreter")
        args[1] = evaluator
    args[0] = executable
    return {target: {"argv": args, "cwd": entry["cwd"]}}, {"path": executable, "sha256": digest(executable)}


def freeze_cases(case_files, selection, confirmation):
    if not isinstance(case_files, dict) or set(case_files) != set(selection) | set(confirmation):
        raise ValueError("case_files must identify every selection and confirmation input")
    result = {}
    for case, path in case_files.items():
        resolved = str(Path(path).resolve(strict=True))
        result[case] = {"path": resolved, "sha256": digest(resolved)}
    if {result[c]["sha256"] for c in selection} & {result[c]["sha256"] for c in confirmation}:
        raise ValueError("selection and confirmation cases contain the same input bytes")
    if len({item["sha256"] for item in result.values()}) != len(result):
        raise ValueError("different case identifiers cannot share the same input bytes")
    return result


def retain_cases(root, cases):
    """Retain exact case bytes independently of mutable original paths."""
    directory = root / "case-evidence"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink():
        raise ValueError("case evidence directory cannot be a symlink")
    for item in cases.values():
        data = Path(item["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("case input changed while retaining evidence")
        destination = directory / item["sha256"]
        try:
            with destination.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if destination.is_symlink() or digest(destination) != item["sha256"]:
                raise ValueError("retained case evidence does not match")


def target_digest(registry, executable, dependencies=None, backend=None):
    payload = {"registry": registry, "executable": executable, "dependencies": dependencies or []}
    if backend is not None:
        payload["backend"] = backend
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def calibration_from_runs(root, experiment, records, evaluator_digest, command_digest):
    if not isinstance(records, list) or len(records) < 2:
        raise ValueError("calibration needs labeled settled run records")
    if any(not isinstance(record, dict) or set(record) != {"id", "run_key", "gate", "expected"} for record in records):
        raise ValueError("calibration labels must reference actual run records")
    state = Ledger(root / "ledger.sqlite3").status(experiment)
    runs = {item["run_key"]: item for item in state["runs"]}
    receipts = {item["run_key"]: item["details"] for item in state["events"] if item["operation"] == "settle"}
    observations, identities = [], set()
    for record in records:
        key = name(record["run_key"])
        path = root / "calibrations" / (key + ".json")
        saved = read(path)
        if (runs.get(key, {}).get("status") != "settled" or
                receipts.get(key, {}).get("receipt_sha256") != digest(path) or
                saved["evaluator_sha256"] != evaluator_digest or saved["command_sha256"] != command_digest or
                saved["config_digest"] != config_digest(root)):
            raise ValueError("calibration run is missing, unsettled or belongs to a different evaluator")
        if type(record["expected"]) is not bool:
            raise ValueError("calibration expected label must be boolean")
        result = saved["result"]
        if result["status"] != "passed" or result["stdout_truncated"]:
            raise ValueError("calibration run did not produce complete output")
        if "backend" in saved:
            verify_controller_harbor(result, saved["backend"], saved["evaluator"],
                                     case_sha256=saved["case_sha256"],
                                     required_gates=saved["gates"], metric_names=saved["metrics"])
        payload = strict_json_loads(result["stdout"])
        if not isinstance(payload, dict) or payload.get("case_sha256") != saved["case_sha256"]:
            raise ValueError("calibration output does not attest the case input")
        observed = payload.get("gates", {}).get(record["gate"])
        identities.add((saved["identity"]["commit"], saved["case_sha256"]))
        observations.append({"id": record["id"], "expected": record["expected"], "observed": observed})
    if len(identities) != len(records):
        raise ValueError("calibration examples must identify distinct artifacts")
    result = validate_calibration(observations)
    result["runs"] = [record["run_key"] for record in records]
    return result


def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def read(path):
    with Path(path).open(encoding="utf-8") as stream:
        return strict_json_loads(stream.read())


def config_for(root):
    if not (root / "ledger.sqlite3").is_file():
        raise ValueError("experiment ledger has not been initialized")
    with sqlite3.connect(root / "ledger.sqlite3") as db:
        row = db.execute("SELECT digest, path FROM controller_config WHERE id=1").fetchone()
    if row is None:
        raise ValueError("missing experiment configuration")
    path = (root / row[1]).resolve()
    if not path.is_relative_to(root) or row[0] != digest(path):
        raise ValueError("frozen experiment configuration changed")
    config = read(path)
    if config.get("version") != 1:
        raise ValueError("unsupported experiment configuration")
    return config


def check_inputs(config):
    if "backend" in config:
        validate_controller_harbor(config["backend"], config["evaluator"])
    for key in ("contract", "evaluator", "executable"):
        if digest(config[key]["path"]) != config[key]["sha256"]:
            raise ValueError(f"{key} file changed; start a revised comparison")
    for item in config.get("evaluator_dependencies", []):
        if digest(item["path"]) != item["sha256"]:
            raise ValueError("evaluator dependency changed; start a revised comparison")
    for item in config["case_files"].values():
        if digest(item["path"]) != item["sha256"]:
            raise ValueError("case input changed; start a revised comparison")
    if "backend" not in config:
        check_native_config(config["evaluator"]["path"], config["registry"], config["target"],
                            config.get("evaluator_dependencies", []))


def dependency_manifest(paths):
    if not isinstance(paths, list):
        raise ValueError("evaluator_dependencies must be a list of file paths")
    resolved = [str(Path(path).resolve(strict=True)) for path in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("duplicate evaluator dependency")
    return [{"path": path, "sha256": digest(path)} for path in resolved]


def check_native_config(evaluator, registry, target, dependencies):
    """Bind the bundled native adapter's external command configuration."""
    native = Path(__file__).with_name("experiment_native_check.py")
    if not native.is_file():
        raise ValueError("bundled native-check adapter is missing")
    if digest(evaluator) != digest(native):
        return
    argv = registry[target]["argv"]
    prefix = 1 if Path(argv[0]).resolve() == Path(evaluator).resolve() else 2
    arguments = argv[prefix:]
    if len(arguments) % 2:
        raise ValueError("native-check accepts only explicit option-value pairs")
    options = {}
    for index in range(0, len(arguments), 2):
        option, value = arguments[index:index + 2]
        if option not in ("--config", "--case-file", "--case") or option in options:
            raise ValueError("native-check accepts each explicit option only once")
        options[option] = value
    if "--config" not in options or options.get("--case-file") != "{{case_file}}":
        raise ValueError("native-check requires --config and the bound --case-file")
    if "--case" in options and options["--case"] != "{{case}}":
        raise ValueError("native-check --case must use the assigned case")
    if not Path(options["--config"]).is_absolute():
        raise ValueError("native-check config path must be absolute")
    path = str(Path(options["--config"]).resolve(strict=True))
    matching = [item for item in dependencies if item["path"] == path]
    if len(matching) != 1 or matching[0]["sha256"] != digest(path):
        raise ValueError("native-check config must be a frozen evaluator dependency")
    helper = str(Path(evaluator).with_name("json_contract.py").resolve(strict=True))
    matching = [item for item in dependencies if item["path"] == helper]
    if len(matching) != 1 or matching[0]["sha256"] != digest(helper):
        raise ValueError("native-check json_contract.py must be a frozen evaluator dependency")


def commit_identity(git, commit):
    commit = git._commit(commit)
    tree = git._git("rev-parse", "--verify", commit + "^{tree}").stdout.strip()
    return {"commit": commit, "tree": tree}


def baseline_identity(git, config):
    return commit_identity(git, git.resolve_integration(config["experiment"]))


def config_digest(root):
    with sqlite3.connect(root / "ledger.sqlite3") as db:
        return db.execute("SELECT digest FROM controller_config WHERE id=1").fetchone()[0]


def record_promotion_intent(root, decision_id, intent):
    """Record an immutable intent before attempting the Git ref transaction."""
    decision_id = name(decision_id)
    path = root / "promotions" / (decision_id + ".json")
    if path.exists() or path.is_symlink():
        raise ValueError("promotion intent file already exists")
    payload = json.dumps(intent, sort_keys=True, separators=(",", ":"), allow_nan=False)
    checksum = hashlib.sha256(payload.encode()).hexdigest()
    with sqlite3.connect(root / "ledger.sqlite3", isolation_level=None) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS controller_promotion_intents "
                   "(decision TEXT PRIMARY KEY, payload TEXT NOT NULL, sha256 TEXT NOT NULL)")
        try:
            db.execute("INSERT INTO controller_promotion_intents(decision,payload,sha256) VALUES(?,?,?)",
                       (decision_id, payload, checksum))
        except sqlite3.IntegrityError as exc:
            db.rollback()
            raise ValueError("promotion intent already exists; use recover") from exc
        db.commit()
    # SQLite is authoritative if interrupted before publishing the readable copy.
    write_new(path, intent)


def load_promotion_intent(root, decision_id):
    decision_id = name(decision_id)
    try:
        with sqlite3.connect(root / "ledger.sqlite3") as db:
            row = db.execute("SELECT payload, sha256 FROM controller_promotion_intents "
                             "WHERE decision=?", (decision_id,)).fetchone()
    except sqlite3.OperationalError as exc:
        raise ValueError("promotion intent is missing its ledger binding") from exc
    if row is None or hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
        raise ValueError("promotion intent is missing or changed in the ledger")
    intent = strict_json_loads(row[0])
    path = root / "promotions" / (decision_id + ".json")
    if path.is_symlink():
        raise ValueError("promotion intent file was replaced")
    if path.exists():
        if read(path) != intent:
            raise ValueError("promotion intent file differs from the ledger")
    else:
        write_new(path, intent)
    return intent


def validate_promotion_intent(root, config, git, decision_id, intent):
    required = {"expected", "candidate", "state", "expected_generation", "new_generation",
                "decision_sha256", "config_sha256"}
    if not isinstance(intent, dict) or set(intent) != required or intent["state"] != "intent":
        raise ValueError("invalid promotion intent")
    decision_path = root / "decisions" / (name(decision_id) + ".json")
    if digest(decision_path) != intent["decision_sha256"]:
        raise ValueError("promotion decision changed after the intent")
    if config_digest(root) != intent["config_sha256"]:
        raise ValueError("promotion configuration changed after the intent")
    saved = read(decision_path)
    if (saved["result"]["decision"] != "eligible" or
            saved["spec"]["baseline"]["commit"] != intent["expected"] or
            saved["spec"]["candidate"]["commit"] != intent["candidate"] or
            saved["generation"] != intent["expected_generation"]):
        raise ValueError("promotion intent does not match the eligible decision")
    expected_generation, new_generation = intent["expected_generation"], intent["new_generation"]
    object_format = git._git("rev-parse", "--show-object-format").stdout.strip()
    length = {"sha1": 40, "sha256": 64}[object_format]
    if (not isinstance(expected_generation, str) or not isinstance(new_generation, str) or
            not re.fullmatch(rf"[0-9a-f]{{{length}}}", expected_generation) or
            not re.fullmatch(rf"[0-9a-f]{{{length}}}", new_generation) or
            expected_generation == new_generation):
        raise ValueError("invalid promotion generations")
    if git._git("cat-file", "-t", new_generation).stdout.strip() != "blob":
        raise ValueError("new promotion generation is not a Git blob")
    check_inputs(config)
    return saved


def remaining_time(root, config):
    """Track the last wall time and fail closed on expiration or rollback."""
    now = time.time()
    if not math.isfinite(now) or not math.isfinite(config["deadline_epoch"]):
        raise ValueError("experiment clock is invalid")
    with sqlite3.connect(root / "ledger.sqlite3", isolation_level=None) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT last_observed FROM controller_clock WHERE id=1").fetchone()
        if row is None or not math.isfinite(row[0]) or now < row[0]:
            db.rollback()
            raise ValueError("experiment clock moved backwards or is missing")
        db.execute("UPDATE controller_clock SET last_observed=? WHERE id=1", (now,))
        db.commit()
    remaining = config["deadline_epoch"] - now
    if remaining <= 0:
        raise ValueError("experiment deadline expired")
    return remaining


def harbor_measurement_names(evaluation):
    gates = evaluation["required_gates"] + evaluation.get("candidate_only_gates", [])
    metrics = list(dict.fromkeys([evaluation["metric"]] + [item["metric"] for item in evaluation.get("guardrails", [])]))
    if not gates or not metrics or set(gates) & set(metrics) or "work_count" in gates + metrics:
        raise ValueError("Harbor gate and metric names must be distinct and cannot use work_count")
    return gates, metrics


def run_selected(root, config, git, identity, case, rep, key, deadline, *,
                 backend=_BACKEND_UNSET, evaluator=None, registry=None, case_file=None, evaluation=None):
    backend = config.get("backend") if backend is _BACKEND_UNSET else backend
    evaluator = config["evaluator"] if evaluator is None else evaluator
    case_file = config["case_files"][case] if case_file is None else case_file
    evaluation = config["evaluation"] if evaluation is None else evaluation
    if backend is not None:
        gates, metrics = harbor_measurement_names(evaluation)
        return run_controller_harbor(git.repo, identity["commit"], identity["tree"], backend,
                                     evaluator, [config["target"]], config["target"],
                                     case_file["path"], case_file["sha256"], root / "harbor-runs" / key,
                                     gates, metrics, deadline=deadline)
    registry = config["registry"] if registry is None else registry
    entry = registry[config["target"]]
    argv = [case if arg == "{{case}}" else str(rep) if arg == "{{rep}}"
            else case_file["path"] if arg == "{{case_file}}"
            else case_file["sha256"] if arg == "{{case_sha256}}" else arg
            for arg in entry["argv"]]
    selected = {config["target"]: {"argv": argv, "cwd": entry["cwd"]}}
    return run_trial(git.repo, identity["commit"], identity["tree"], selected,
                     [config["target"]], config["target"], deadline=deadline)


def settle_result(ledger, experiment, key, result, receipt):
    if result["status"] == "unknown":
        return ledger.uncertain(experiment, key, reason=result.get("error") or "uncertain backend outcome")
    return ledger.settle(experiment, key, actual_tokens=0, receipt_sha256=digest(receipt))


def selection_claim(root, config, git, side, identity, case, rep):
    """Identify one frozen selection attempt in the current integration round."""
    return {"config_digest": config_digest(root), "generation": git.generation(config["experiment"]),
            "side": side, "tree": identity["tree"],
            "case_sha256": config["case_files"][case]["sha256"], "rep": rep}


def approved_identity(root, config, git, arm):
    arm = name(arm)
    identity = git.resolve(config["experiment"], arm)
    approval_path = root / "approvals" / arm / (identity["commit"] + ".json")
    try:
        approval = read(approval_path)
    except FileNotFoundError as error:
        raise ValueError("arm tip has not passed scoped freeze") from error
    if approval != {"identity": identity, "paths": config["paths"]}:
        raise ValueError("scoped freeze approval does not match arm")
    return identity


def evaluation_spec(config, baseline, candidate, split="selection"):
    evaluation = config["evaluation"]
    check_evaluation_fields(evaluation)
    assignments = evaluation if split == "selection" else config["confirmation"]
    return {
        **{key: value for key, value in evaluation.items()
           if key not in ("cases", "repetitions")},
        "version": 1,
        "contract": config["contract"]["sha256"],
        "evaluator": config["evaluator"]["sha256"],
        "baseline": baseline,
        "candidate": candidate,
        "assignments": [
            {"case": case, "rep": rep}
            for case in assignments["cases"]
            for rep in range(assignments["repetitions"])
        ],
    }


def initialize(request, root):
    experiment = name(request["experiment"])
    paths = request["paths"]
    backend = request.get("backend")
    registry = request.get("registry", {})
    target = name(request["target"])
    evaluation = request["evaluation"]
    if not isinstance(paths, list) or not paths:
        raise ValueError("paths must be a nonempty list")
    evaluator = str(Path(request["evaluator_file"]).resolve(strict=True))
    contract = str(Path(request["contract_file"]).resolve(strict=True))
    evaluator_identity = {"path": evaluator, "sha256": digest(evaluator)}
    if backend is not None:
        if registry or request.get("evaluator_dependencies"):
            raise ValueError("Harbor owns verifier execution and cannot use a local target registry")
        validate_controller_harbor(backend, evaluator_identity)
        registry = {}
        executable = {"path": backend["harbor_bin"], "sha256": backend["harbor_bin_sha256"]}
        entry = None
    else:
        registry, executable = validate_target(registry, target, evaluator, request.get("trusted_interpreter"))
        entry = registry[target]
    check_evaluation_fields(evaluation)
    if not isinstance(evaluation, dict):
        raise ValueError("evaluation must be an object")
    repetitions = evaluation.get("repetitions")
    if type(repetitions) is not int or not 1 <= repetitions <= 100:
        raise ValueError("repetitions must be between 1 and 100")
    evaluation = dict(evaluation)
    if "case" in evaluation:
        if "cases" in evaluation:
            raise ValueError("choose case or cases, not both")
        evaluation["cases"] = [evaluation.pop("case")]
    cases = evaluation.get("cases")
    if (not isinstance(cases, list) or not cases or
            any(not isinstance(case, str) or not case.strip() for case in cases) or
            len(set(cases)) != len(cases)):
        raise ValueError("cases must be a nonempty unique list of strings")
    confirmation = request.get("confirmation")
    if confirmation is not None:
        if not isinstance(confirmation, dict) or set(confirmation) != {"cases", "repetitions"}:
            raise ValueError("confirmation must specify cases and repetitions")
        heldout = confirmation["cases"]
        if (not isinstance(heldout, list) or not heldout or
                any(not isinstance(case, str) or not case.strip() for case in heldout) or
                len(set(heldout)) != len(heldout) or set(heldout) & set(cases)):
            raise ValueError("confirmation cases must be nonempty, unique, and disjoint from selection")
        if type(confirmation["repetitions"]) is not int or not 1 <= confirmation["repetitions"] <= 100:
            raise ValueError("confirmation repetitions must be between 1 and 100")
    if entry is not None and (len(cases) > 1 or confirmation is not None) and "{{case}}" not in entry["argv"]:
        raise ValueError("multi-case targets must pass {{case}} as an argument")
    if entry is not None and "{{case_file}}" not in entry["argv"]:
        raise ValueError("target must pass {{case_file}} to the evaluator")
    if backend is not None and evaluation.get("required_qualitative"):
        raise ValueError("Harbor rewards do not support structured qualitative evidence")
    case_files = freeze_cases(request.get("case_files"), cases,
                              [] if confirmation is None else confirmation["cases"])
    max_trials = request["max_trials"]
    max_tokens = request["max_tokens"]
    max_proposals = request.get("max_proposals", 5)
    if type(max_trials) is not int or max_trials < 1 or type(max_tokens) is not int or max_tokens != 0:
        raise ValueError("the local runner requires max_tokens=0 and a trusted non-model target")
    if type(max_proposals) is not int or not 1 <= max_proposals <= 100:
        raise ValueError("max_proposals must be between 1 and 100")
    elapsed = request.get("max_elapsed_seconds", 1800)
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed <= 0:
        raise ValueError("max_elapsed_seconds must be a positive finite number")
    started = time.time()
    if not math.isfinite(started) or not math.isfinite(started + elapsed):
        raise ValueError("experiment deadline is invalid")
    config = {
        "version": 1, "experiment": experiment, "base": request["base"],
        "paths": paths, "target": target, "registry": registry, "evaluation": evaluation,
        "contract": {"path": contract, "sha256": digest(contract)},
        "evaluator": {"path": evaluator, "sha256": digest(evaluator)},
        "executable": executable, "case_files": case_files,
        "evaluator_dependencies": dependency_manifest(request.get("evaluator_dependencies", [])),
        "max_trials": max_trials, "max_tokens": max_tokens, "max_proposals": max_proposals,
        "started_at_epoch": started, "deadline_epoch": started + elapsed,
    }
    if backend is not None:
        config["backend"] = backend
    if confirmation is not None:
        config["confirmation"] = confirmation
    if backend is None:
        check_native_config(evaluator, registry, target, config["evaluator_dependencies"])
    # Check the comparison contract before creating any workspace.
    identity = {"commit": request["base"], "tree": request["base"]}
    _validate_spec(evaluation_spec(config, identity, identity))
    if backend is not None:
        harbor_measurement_names(config["evaluation"])
    git = GitExperiment.create(request["source"], root)
    retain_cases(root, config["case_files"])
    baseline = commit_identity(git, config["base"])
    git.initialize_integration(experiment, baseline["commit"])
    Ledger(root / "ledger.sqlite3").initialize(experiment, max_trials=max_trials, max_tokens=max_tokens)
    Ledger(root / "ledger.sqlite3").configure_proposals(experiment, max_proposals=max_proposals)
    write_new(root / "experiment.json", config)
    with sqlite3.connect(root / "ledger.sqlite3") as db:
        db.execute("CREATE TABLE controller_config (id INTEGER PRIMARY KEY CHECK (id=1), digest TEXT NOT NULL, path TEXT NOT NULL)")
        db.execute("INSERT INTO controller_config(id, digest, path) VALUES (1, ?, ?)",
                   (digest(root / "experiment.json"), "experiment.json"))
        db.execute("CREATE TABLE controller_clock (id INTEGER PRIMARY KEY CHECK (id=1), last_observed REAL NOT NULL)")
        db.execute("INSERT INTO controller_clock(id, last_observed) VALUES (1, ?)", (started,))
    return {"root": str(root), "baseline": baseline, "experiment": experiment}


def rows_for(root, config, keys, side, identity, split="selection", revision=None, generation=None):
    if not isinstance(keys, list):
        raise ValueError("run keys must be a list")
    rows = []
    ledger_status = Ledger(root / "ledger.sqlite3").status(config["experiment"])
    runs = {item["run_key"]: item for item in ledger_status["runs"]}
    settlements = {item["run_key"]: item["details"] for item in ledger_status["events"]
                   if item["operation"] == "settle"}
    for key in keys:
        name(key)
        run_path = root / "runs" / (key + ".json")
        record = read(run_path)
        if (runs.get(key, {}).get("status") != "settled" or
                settlements.get(key, {}).get("receipt_sha256") != digest(run_path)):
            raise ValueError("run receipt is not bound to a settled ledger entry")
        if record.get("config_digest") != (config_digest(root) if revision is None else revision):
            raise ValueError("run belongs to a different experiment revision")
        current_generation = GitExperiment.open(root).generation(config["experiment"]) if generation is None else generation
        if record.get("generation") != current_generation:
            raise ValueError("run belongs to a different integration generation")
        result = record["result"]
        if "backend" in config and result.get("status") == "passed":
            gates, metrics = harbor_measurement_names(config["evaluation"])
            verify_controller_harbor(result, config["backend"], config["evaluator"],
                                     case_sha256=record["case_sha256"], required_gates=gates, metric_names=metrics)
        if record.get("case_sha256") != config["case_files"][record["case"]]["sha256"]:
            raise ValueError("run case input differs from frozen case manifest")
        if record.get("split", "selection") != split:
            raise ValueError("run belongs to a different evaluation split")
        if record["side"] != side:
            raise ValueError("run belongs to a different comparison side")
        source_identity = record.get("identity")
        if (not isinstance(source_identity, dict) or set(source_identity) != {"commit", "tree"} or
                source_identity.get("tree") != identity["tree"]):
            raise ValueError("run belongs to a different candidate tree")
        if (result.get("commit") != source_identity["commit"] or
                result.get("tree") != source_identity["tree"]):
            raise ValueError("trial backend identity differs from its run receipt")
        provenance = {"kind": "direct" if source_identity == identity else "same-tree",
                      "run_key": key, "source": source_identity}
        try:
            artifact_path = root / "evidence" / (key + ".json")
            if digest(artifact_path) != record["artifact_sha256"]:
                raise ValueError("evaluator artifact changed")
            artifact = artifact_path.read_text(encoding="utf-8")
            if artifact != result["stdout"]:
                raise ValueError("evaluator output and receipt differ")
            measurement = strict_json_loads(artifact)
            if not isinstance(measurement, dict) or result["stdout_truncated"]:
                raise ValueError("incomplete evaluator output")
            if measurement.get("case_sha256") != record["case_sha256"]:
                raise ValueError("evaluator did not attest the case input digest")
        except (ValueError, KeyError):
            measurement = {}
        row = {
            **identity, "contract": record["contract"],
            "evaluator": record["evaluator"], "case": record["case"],
            "rep": record["rep"], "status": "completed" if result["status"] == "passed" else result["status"],
            "gates": measurement.get("gates"), "metrics": measurement.get("metrics"),
            "work_count": measurement.get("work_count"),
            "artifacts": [{"path": key + ".json", "sha256": record["artifact_sha256"]}],
            "provenance": provenance,
        }
        qualitative = measurement.get("qualitative")
        if isinstance(qualitative, dict):
            # `self` refers to the retained, hashed evaluator output for this run.
            # It lets a grader cite evidence embedded in its own receipt without
            # knowing the controller's run key in advance.
            qualitative = {
                criterion: ({**judgment, "evidence": [
                    key + ".json" if reference == "self" else reference
                    for reference in judgment["evidence"]
                ]} if isinstance(judgment, dict) and isinstance(judgment.get("evidence"), list)
                    else judgment)
                for criterion, judgment in qualitative.items()
            }
        if qualitative is not None:
            row["qualitative"] = qualitative
        rows.append(row)
    return rows


def compare_runs(root, config, git, arm, baseline_keys, candidate_keys, split="selection"):
    check_inputs(config)
    baseline = baseline_identity(git, config)
    candidate = approved_identity(root, config, git, arm)
    if candidate["tree"] == baseline["tree"]:
        raise ValueError("candidate tree is identical to baseline")
    spec = evaluation_spec(config, baseline, candidate, split)
    before = rows_for(root, config, baseline_keys, "baseline", baseline, split)
    after = rows_for(root, config, candidate_keys, "candidate", candidate, split)
    result = compare(spec, before, after, root / "evidence")
    return {"result": result, "spec": spec, "baseline": before, "candidate": after}


def selection_path(root, git, config):
    return root / "selections" / (git.generation(config["experiment"]) + "-" + config_digest(root) + ".json")


def confirmation_path(root, git, config):
    return root / "confirmations" / (git.generation(config["experiment"]) + "-" + config_digest(root) + ".json")


def check_case_separation(root, config):
    """Reject cases already exposed on the opposite side, across generations."""
    selection = set(config["evaluation"]["cases"])
    confirmation = set(config.get("confirmation", {}).get("cases", []))
    if selection & confirmation:
        raise ValueError("selection and confirmation cases must be disjoint")
    exposed_confirmation = set()
    exposed_confirmation_inputs = set()
    for path in (root / "confirmation-claims").glob("*/*.json"):
        record = read(path)
        exposed_confirmation.add(record["case"])
        if "case_sha256" not in record:
            raise ValueError("legacy confirmation exposure lacks a case digest")
        exposed_confirmation_inputs.add(record["case_sha256"])
    exposed_selection = set()
    exposed_selection_inputs = set()
    for path in (root / "selection-exposures").glob("*.json"):
        record = read(path)
        exposed_selection.add(record["case"])
        if "case_sha256" not in record:
            raise ValueError("legacy selection exposure lacks a case digest")
        exposed_selection_inputs.add(record["case_sha256"])
    for path in (root / "runs").glob("*.json"):
        record = read(path)
        if record.get("split", "selection") == "selection":
            exposed_selection.add(record["case"])
            if "case_sha256" not in record:
                raise ValueError("legacy selection run lacks a case digest")
            exposed_selection_inputs.add(record["case_sha256"])
    if selection & exposed_confirmation or confirmation & (exposed_confirmation | exposed_selection):
        raise ValueError("selection or confirmation case was previously exposed")
    selection_inputs = {config["case_files"][c]["sha256"] for c in selection}
    confirmation_inputs = {config["case_files"][c]["sha256"] for c in confirmation}
    if selection_inputs & exposed_confirmation_inputs or confirmation_inputs & (exposed_confirmation_inputs | exposed_selection_inputs):
        raise ValueError("selection or confirmation input bytes were previously exposed")


def validate_revised_cases(config):
    evaluation = config["evaluation"]
    if not isinstance(evaluation, dict):
        raise ValueError("evaluation must be an object")
    repetitions, cases = evaluation.get("repetitions"), evaluation.get("cases")
    if (type(repetitions) is not int or not 1 <= repetitions <= 100 or
            not isinstance(cases, list) or not cases or
            any(not isinstance(case, str) or not case.strip() for case in cases) or
            len(cases) != len(set(cases))):
        raise ValueError("invalid selection assignments")
    confirmation = config.get("confirmation")
    if confirmation is not None:
        if not isinstance(confirmation, dict) or set(confirmation) != {"cases", "repetitions"}:
            raise ValueError("confirmation must specify cases and repetitions")
        cases2, reps2 = confirmation["cases"], confirmation["repetitions"]
        if (not isinstance(cases2, list) or not cases2 or
                any(not isinstance(case, str) or not case.strip() for case in cases2) or
                len(cases2) != len(set(cases2)) or type(reps2) is not int or not 1 <= reps2 <= 100):
            raise ValueError("invalid confirmation assignments")
    if "backend" not in config:
        entry = config["registry"][config["target"]]
        if (not isinstance(entry, dict) or set(entry) != {"argv", "cwd"} or
                not isinstance(entry["argv"], list) or not entry["argv"]):
            raise ValueError("invalid target")
        if (len(cases) > 1 or confirmation is not None) and "{{case}}" not in entry["argv"]:
            raise ValueError("multi-case targets must pass {{case}} as an argument")
        if "{{case_file}}" not in entry["argv"]:
            raise ValueError("target must pass {{case_file}} to the evaluator")
    elif evaluation.get("required_qualitative"):
        raise ValueError("Harbor rewards do not support structured qualitative evidence")


def selected_finalist(root, config, git):
    if "confirmation" not in config:
        raise ValueError("confirmation is not configured")
    selection = read(selection_path(root, git, config))
    decision_path = root / "decisions" / (selection["decision"] + ".json")
    if selection["config_digest"] != config_digest(root) or digest(decision_path) != selection["decision_digest"]:
        raise ValueError("selection or configuration changed")
    decision = read(decision_path)
    assessment = compare_runs(root, config, git, decision["arm"], decision["baseline_keys"], decision["candidate_keys"])
    if (decision["generation"] != git.generation(config["experiment"]) or
            decision["result"]["decision"] != "eligible" or
            assessment != {key: decision[key] for key in ("result", "spec", "baseline", "candidate")}):
        raise ValueError("selected finalist or its evidence changed")
    return selection, decision


def require_confirmation(root, config, git, decision_id):
    selection, decision = selected_finalist(root, config, git)
    if selection["decision"] != decision_id:
        raise ValueError("decision is not the selected finalist")
    confirmed = read(confirmation_path(root, git, config))
    assessment = compare_runs(root, config, git, decision["arm"],
                              confirmed["baseline_keys"], confirmed["candidate_keys"], "confirmation")
    if (confirmed["selection_digest"] != digest(selection_path(root, git, config)) or
            confirmed["result"]["decision"] != "eligible" or
            assessment != {key: confirmed[key] for key in ("result", "spec", "baseline", "candidate")}):
        raise ValueError("confirmation did not establish eligibility or changed")


def run(request, root, config, git, ledger):
    remaining_time(root, config)
    check_inputs(config)
    split = request.get("split", "selection")
    if split not in ("selection", "confirmation"):
        raise ValueError("unknown evaluation split")
    selected = selection_path(root, git, config).exists()
    if split == "selection":
        if selected:
            raise ValueError("selection is locked after selecting a finalist")
        check_case_separation(root, config)
        assignments = config["evaluation"]
    else:
        selection, decision = selected_finalist(root, config, git)
        if confirmation_path(root, git, config).exists():
            raise ValueError("confirmation has already been evaluated")
        if request.get("side") == "candidate" and request.get("arm") != decision["arm"]:
            raise ValueError("confirmation requires the selected arm")
        assignments = config["confirmation"]
    side = request["side"]
    rep = request["rep"]
    if side not in ("baseline", "candidate"):
        raise ValueError("side must be baseline or candidate")
    if type(rep) is not int or not 0 <= rep < assignments["repetitions"]:
        raise ValueError("rep outside the frozen assignment")
    cases = assignments["cases"]
    case = request.get("case", cases[0] if len(cases) == 1 else None)
    if case not in cases:
        raise ValueError("case outside the frozen assignments")
    case_file = config["case_files"][case]
    key = name(request["run_key"])
    identity = (baseline_identity(git, config) if side == "baseline"
                else approved_identity(root, config, git, request["arm"]))
    result_path = root / "runs" / (key + ".json")
    if result_path.exists():
        raise ValueError("run key already has a receipt")
    claim_path = None
    if split == "confirmation":
        # Each side/case/repetition can run once, avoiding cherry-picking.
        claim = json.dumps([side, case, rep], separators=(",", ":"), ensure_ascii=False)
        claim_id = hashlib.sha256(claim.encode()).hexdigest()
        claim_path = root / "confirmation-claims" / (git.generation(config["experiment"]) + "-" + config_digest(root)) / (claim_id + ".json")
        write_new(claim_path, {"side": side, "case": case, "case_sha256": case_file["sha256"], "rep": rep, "run_key": key})
    try:
        claim = selection_claim(root, config, git, side, identity, case, rep) if split == "selection" else None
        ledger.reserve(config["experiment"], key, tokens=0, selection_claim=claim)
    except Exception:
        if claim_path is not None:
            claim_path.unlink()
        raise
    try:
        deadline = time.monotonic() + remaining_time(root, config)
    except (OSError, ValueError, sqlite3.Error):
        ledger.cancel(config["experiment"], key, reason="deadline before dispatch")
        if claim_path is not None:
            claim_path.unlink()
        raise
    if split == "selection":
        case_id = hashlib.sha256((case + "\0" + case_file["sha256"]).encode()).hexdigest()
        exposure = root / "selection-exposures" / (case_id + ".json")
        if not exposure.exists():
            write_new(exposure, {"case": case, "case_sha256": case_file["sha256"]})
    grant = ledger.dispatch(config["experiment"], key)
    if not grant["dispatch_granted"]:
        raise ValueError("run already dispatched; reconcile before retrying")
    result = run_selected(root, config, git, identity, case, rep, key, deadline)
    try:
        check_inputs(config)
    except (OSError, ValueError) as error:
        if result["status"] != "unknown":
            result["status"] = "infra_error"
        result["error"] = str(error)
    artifact_path = root / "evidence" / (key + ".json")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_path.open("x", encoding="utf-8") as stream:
        stream.write(result["stdout"])
        stream.flush()
        os.fsync(stream.fileno())
    record = {
        "side": side, "case": case, "rep": rep, "identity": identity, "split": split,
        "generation": git.generation(config["experiment"]),
        "case_sha256": case_file["sha256"],
        "config_digest": config_digest(root),
        "contract": config["contract"]["sha256"], "evaluator": config["evaluator"]["sha256"],
        "result": result, "artifact_sha256": digest(artifact_path),
    }
    write_new(result_path, record)
    settle_result(ledger, config["experiment"], key, result, result_path)
    return record


def calibration_run(request, root, config, git, ledger):
    """Execute the proposed verifier on a labeled reference source and case."""
    remaining_time(root, config)
    check_inputs(config)
    evaluator = str(Path(request["evaluator_file"]).resolve(strict=True))
    backend = request.get("backend", config.get("backend"))
    evaluator_identity = {"path": evaluator, "sha256": digest(evaluator)}
    if backend is not None:
        if request.get("registry") or request.get("evaluator_dependencies"):
            raise ValueError("Harbor calibration cannot use a local target registry")
        validate_controller_harbor(backend, evaluator_identity)
        registry, dependencies = {}, []
        executable = {"path": backend["harbor_bin"], "sha256": backend["harbor_bin_sha256"]}
    else:
        registry, executable = validate_target(request["registry"], config["target"], evaluator,
                                               request.get("trusted_interpreter"))
        dependencies = dependency_manifest(request.get("evaluator_dependencies", [item["path"] for item in config.get("evaluator_dependencies", [])]))
        check_native_config(evaluator, registry, config["target"], dependencies)
        entry = registry[config["target"]]
        if "{{case_file}}" not in entry["argv"]:
            raise ValueError("calibration evaluator must receive {{case_file}}")
    case = request["case"]
    if not isinstance(case, str) or not case.strip():
        raise ValueError("calibration case must be named")
    case_path = str(Path(request["case_file"]).resolve(strict=True))
    case_hash = digest(case_path)
    current_holdout = {config["case_files"][name]["sha256"] for name in config.get("confirmation", {}).get("cases", [])}
    previous_holdout = {read(path)["case_sha256"] for path in (root / "confirmation-claims").glob("*/*.json")}
    if case_hash in current_holdout | previous_holdout:
        raise ValueError("calibration cannot consume a confirmation input")
    evaluation = request.get("evaluation", config["evaluation"])
    check_evaluation_fields(evaluation)
    if backend is not None:
        if evaluation.get("required_qualitative"):
            raise ValueError("Harbor rewards do not support structured qualitative evidence")
        harbor_measurement_names(evaluation)
    evaluator_hash = digest(evaluator)
    identity = commit_identity(git, request["commit"])
    key = name(request["run_key"])
    path = root / "calibrations" / (key + ".json")
    if path.exists():
        raise ValueError("calibration run key already exists")
    ledger.reserve(config["experiment"], key, tokens=0)
    try:
        deadline = time.monotonic() + remaining_time(root, config)
    except (OSError, ValueError, sqlite3.Error):
        ledger.cancel(config["experiment"], key, reason="deadline before dispatch")
        raise
    exposure_id = hashlib.sha256((case + "\0" + case_hash).encode()).hexdigest()
    exposure = root / "selection-exposures" / (exposure_id + ".json")
    if not exposure.exists():
        write_new(exposure, {"case": case, "case_sha256": case_hash})
    if not ledger.dispatch(config["experiment"], key)["dispatch_granted"]:
        raise ValueError("calibration already dispatched")
    result = run_selected(root, config, git, identity, case, 0, key, deadline,
                          backend=backend, evaluator=evaluator_identity, registry=registry,
                          case_file={"path": case_path, "sha256": case_hash}, evaluation=evaluation)
    try:
        check_inputs(config)
        if digest(evaluator) != evaluator_hash or digest(case_path) != case_hash or digest(executable["path"]) != executable["sha256"]:
            raise ValueError("calibration inputs changed during execution")
        for item in dependencies:
            if digest(item["path"]) != item["sha256"]:
                raise ValueError("calibration dependency changed during execution")
    except (OSError, ValueError) as error:
        if result["status"] != "unknown":
            result["status"] = "infra_error"
        result["error"] = str(error)
    record = {"identity": identity, "case": case, "case_sha256": case_hash, "result": result,
              "config_digest": config_digest(root), "evaluator_sha256": evaluator_hash,
              "command_sha256": target_digest(registry, executable, dependencies, backend)}
    if backend is not None:
        gates, metrics = harbor_measurement_names(evaluation)
        record.update({"backend": backend, "evaluator": evaluator_identity, "gates": gates, "metrics": metrics})
    write_new(path, record)
    settle_result(ledger, config["experiment"], key, result, path)
    return record


@contextmanager
def controller_lock(root, exclusive):
    # All CLI operations cooperate; external worktree writers need separate
    # quiescence before freezing or retiring their arm.
    with (root / "controller.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def draft(request):
    """Write a reviewable brief using supplied facts without starting an experiment."""
    source = Path(request["source"]).resolve(strict=True)
    top = Path(_run(["-C", source, "rev-parse", "--show-toplevel"]).stdout.strip()).resolve()
    output_value = request["output"]
    if not isinstance(output_value, str) or not output_value.strip():
        raise ValueError("output must be a nonempty path outside the source checkout")
    output = Path(output_value).resolve()
    git_dir = Path(_run(["-C", top, "rev-parse", "--absolute-git-dir"]).stdout.strip()).resolve()
    common = Path(_run(["-C", top, "rev-parse", "--git-common-dir"]).stdout.strip())
    common = (top / common).resolve()
    if any(output == directory or output.is_relative_to(directory) for directory in (top, git_dir, common)):
        raise ValueError("output must be outside the source checkout and Git metadata")
    paths = _paths(request["paths"])
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate edit paths")
    for path in paths:
        parts = Path(path).parts
        resolved = (top / path).resolve()
        if any(part.casefold() == ".git" for part in parts) or not resolved.is_relative_to(top):
            raise ValueError("edit paths must remain within the source checkout")
    for field in ("goal", "target", "reason"):
        value = request[field]
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise ValueError(f"{field} must be nonempty text")
    commit = request.get("base")
    if commit is None:
        commit = _run(["-C", top, "rev-parse", "--verify", "HEAD^{commit}"]).stdout.strip()
    fmt = _run(["-C", top, "rev-parse", "--show-object-format"]).stdout.strip()
    length = {"sha1": 40, "sha256": 64}.get(fmt)
    if not isinstance(commit, str) or length is None or not re.fullmatch(rf"[0-9a-f]{{{length}}}", commit):
        raise ValueError("base must be a full lowercase Git commit ID")
    verified = _run(["-C", top, "rev-parse", "--verify", "--end-of-options", commit + "^{commit}"]).stdout.strip()
    if verified != commit:
        raise ValueError("base must directly identify a commit")
    template = Path(__file__).resolve().parents[1] / "templates" / "task-harness.json"
    brief = read(template)
    brief["outcome"]["user_goal"] = request["goal"]
    brief["integration"].update({
        "repository": str(top), "base_commit": commit, "editable_paths": paths,
        "targets": [{"id": request["target"], "reason": request["reason"]}],
    })
    brief["search"]["incumbent"] = commit
    write_new(output, brief)
    return {"draft": str(output), "base": commit}


def execute(request):
    if not isinstance(request, dict):
        raise ValueError("request must be a JSON object")
    action = request["action"]
    if action == "draft":
        return draft(request)
    # Parallel operations own their own locking; invoking them under the
    # controller lock would deadlock. Status deliberately remains readable
    # while a batch is running.
    if action in ("parallel", "parallel-status", "parallel-recover"):
        from experiment_parallel import run_batch, batch_status, recover_reserved
        if action == "parallel":
            return run_batch(request)
        if set(request) != {"action", "root", "batch"}:
            raise ValueError("batch status/recovery accepts only root and batch")
        if action == "parallel-status":
            return batch_status(request["root"], request["batch"])
        return recover_reserved(request["root"], request["batch"])
    root = Path(request["root"]).resolve()
    if action == "init":
        return initialize(request, root)
    exclusive = action not in ("status", "compare", "calibrate", "regrade")
    with controller_lock(root, exclusive):
        return execute_locked(request, root)


def execute_locked(request, root):
    action = request["action"]
    config = config_for(root)
    git = GitExperiment.open(root)
    experiment = config["experiment"]
    ledger = Ledger(root / "ledger.sqlite3")
    if action == "handoff":
        if request.get("writers_stopped") is not True:
            raise ValueError("confirm all delivery worktree writers have stopped")
        from experiment_handoff import handoff_locked
        return handoff_locked(sys.modules[__name__], root, config, git,
                              request["decision"], request["delivery"])
    if action == "status":
        status = {"ledger": ledger.status(experiment), "integration": git.resolve_integration(experiment)}
        if selection_path(root, git, config).exists():
            status["selection"] = read(selection_path(root, git, config))
            if confirmation_path(root, git, config).exists():
                status["confirmation"] = read(confirmation_path(root, git, config))["result"]
        return status
    if action in ("allocate", "freeze", "propose") and selection_path(root, git, config).exists():
        raise ValueError("selection is locked after selecting a finalist")
    if action == "revise" and selection_path(root, git, config).exists():
        confirmation = confirmation_path(root, git, config)
        if not confirmation.is_file() or read(confirmation)["result"]["decision"] == "eligible":
            raise ValueError("selection is locked pending or after eligible confirmation")
        if "confirmation" not in request:
            raise ValueError("failed confirmation requires fresh confirmation cases")
    if action == "allocate":
        path = git.allocate(experiment, name(request["arm"]), git.resolve_integration(experiment))
        return {"worktree": str(path), "identity": git.resolve(experiment, request["arm"])}
    if action == "propose":
        # The native request exposes only a deterministic, zero-model provider.
        # Trusted host code can inject a broker via the Python proposer API.
        allowed = {"action", "root", "arm", "expected", "edits", "prompt", "run_key",
                   "timeout", "message", "writers_stopped"}
        if set(request) - allowed:
            raise ValueError("unknown proposer field or untrusted provider configuration")
        check_inputs(config)
        remaining = remaining_time(root, config)
        # Older experiments predate the separately metered proposal allowance.
        ledger.configure_proposals(experiment, max_proposals=config.get("max_proposals", 5))
        timeout = request.get("timeout", min(30.0, remaining))
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or
                not math.isfinite(timeout) or timeout <= 0 or timeout > remaining):
            raise ValueError("proposal timeout must be within the experiment deadline")
        edits = request.get("edits")
        if not isinstance(edits, list) or not edits:
            raise ValueError("scripted proposal needs an array of edits")
        converted = {}
        for edit in edits:
            if not isinstance(edit, dict) or set(edit) != {"path", "content"}:
                raise ValueError("each scripted edit must specify path and text content or null")
            path, content = edit["path"], edit["content"]
            if not isinstance(path, str) or path in converted or (content is not None and not isinstance(content, str)):
                raise ValueError("scripted paths must be unique and contents must be text or null")
            converted[path] = content.encode("utf-8") if content is not None else None
        runner = ProposalRunner(ledger, {"scripted": ScriptedProvider(converted)})
        def freeze_proposal(arm, message):
            check_inputs(config)
            remaining_time(root, config)
            return execute_locked({"action": "freeze", "arm": arm, "message": message,
                                   "writers_stopped": True}, root)
        return propose_to_arm(
            git=git, ledger=ledger, experiment=experiment, arm=name(request["arm"]),
            expected=request["expected"], paths=config["paths"], runner=runner,
            provider="scripted", prompt=request.get("prompt", "Apply the reviewed scripted edit"),
            run_key=request["run_key"], max_tokens=0, timeout=timeout,
            message=request["message"], freeze=freeze_proposal,
            writers_stopped=request.get("writers_stopped"),
        )
    if action == "freeze":
        if request.get("writers_stopped") is not True:
            raise ValueError("confirm all arm writers have stopped")
        arm = name(request["arm"])
        identity = git.freeze(experiment, arm, config["paths"], request["message"])
        approval_path = root / "approvals" / arm / (identity["commit"] + ".json")
        approval = {"identity": identity, "paths": config["paths"]}
        if approval_path.exists():
            if read(approval_path) != approval:
                raise ValueError("existing scoped freeze approval differs")
        else:
            write_new(approval_path, approval)
        return identity
    if action == "run":
        return run(request, root, config, git, ledger)
    if action == "calibration-run":
        return calibration_run(request, root, config, git, ledger)
    if action == "recover-run":
        key = name(request["run_key"])
        run_path = root / "runs" / (key + ".json")
        record = read(run_path)
        if record["result"]["status"] == "unknown":
            raise ValueError("uncertain backend outcome requires independent reconciliation")
        if "backend" in config and record["result"]["status"] == "passed":
            gates, metrics = harbor_measurement_names(config["evaluation"])
            verify_controller_harbor(record["result"], config["backend"], config["evaluator"],
                                     case_sha256=record["case_sha256"], required_gates=gates, metric_names=metrics)
        artifact_path = root / "evidence" / (key + ".json")
        if (record.get("config_digest") != config_digest(root) or
                digest(artifact_path) != record.get("artifact_sha256") or
                artifact_path.read_text(encoding="utf-8") != record["result"]["stdout"]):
            raise ValueError("run receipt or artifact does not match")
        return ledger.settle(experiment, key, actual_tokens=0, receipt_sha256=digest(run_path))
    if action == "compare":
        if selection_path(root, git, config).exists():
            raise ValueError("selection is locked after selecting a finalist")
        decision = name(request["decision"])
        assessment = compare_runs(root, config, git, request["arm"],
                                  request["baseline"], request["candidate"])
        write_new(root / "decisions" / (decision + ".json"), {
            "arm": request["arm"], "baseline_keys": request["baseline"],
            "candidate_keys": request["candidate"],
            "generation": git.generation(experiment), **assessment,
        })
        return assessment["result"]
    if action == "select":
        if "confirmation" not in config:
            raise ValueError("confirmation is not configured")
        check_case_separation(root, config)
        decision_id = name(request["decision"])
        decision_path = root / "decisions" / (decision_id + ".json")
        decision = read(decision_path)
        assessment = compare_runs(root, config, git, decision["arm"], decision["baseline_keys"], decision["candidate_keys"])
        if (decision["generation"] != git.generation(experiment) or decision["result"]["decision"] != "eligible" or
                assessment != {key: decision[key] for key in ("result", "spec", "baseline", "candidate")}):
            raise ValueError("selection decision no longer qualifies")
        selection = {"decision": decision_id, "decision_digest": digest(decision_path),
                     "config_digest": config_digest(root)}
        write_new(selection_path(root, git, config), selection)
        return {"decision": decision_id, "candidate": decision["spec"]["candidate"]}
    if action == "confirm":
        selection, decision = selected_finalist(root, config, git)
        assessment = compare_runs(root, config, git, decision["arm"], request["baseline"], request["candidate"], "confirmation")
        write_new(confirmation_path(root, git, config), {
            "selection_digest": digest(selection_path(root, git, config)),
            "baseline_keys": request["baseline"], "candidate_keys": request["candidate"], **assessment,
        })
        return assessment["result"]
    if action == "promote":
        if "confirmation" in config:
            require_confirmation(root, config, git, name(request["decision"]))
        decision = read(root / "decisions" / (name(request["decision"]) + ".json"))
        arm = name(request["arm"])
        if decision["arm"] != arm or decision["result"]["decision"] != "eligible":
            raise ValueError("decision does not establish eligibility for this arm")
        assessment = compare_runs(root, config, git, arm, decision["baseline_keys"], decision["candidate_keys"])
        if assessment != {key: decision[key] for key in ("result", "spec", "baseline", "candidate")}:
            raise ValueError("decision or evidence changed since comparison")
        expected = decision["spec"]["baseline"]["commit"]
        candidate = decision["spec"]["candidate"]["commit"]
        expected_generation = decision["generation"]
        next_generation = git.new_generation()
        intent = {"expected": expected, "candidate": candidate, "state": "intent",
                  "expected_generation": expected_generation, "new_generation": next_generation,
                  "decision_sha256": digest(root / "decisions" / (request["decision"] + ".json")),
                  "config_sha256": config_digest(root)}
        validate_promotion_intent(root, config, git, request["decision"], intent)
        record_promotion_intent(root, request["decision"], intent)
        commit = git.promote_with_marker(experiment, expected, candidate, request["decision"],
                                         expected_generation, next_generation)
        write_new(root / "promotions" / (request["decision"] + ".completed.json"),
                  {"expected": expected, "candidate": commit, "state": "completed"})
        return {"commit": commit}
    if action == "recover":
        decision = name(request["decision"])
        intent = load_promotion_intent(root, decision)
        saved = validate_promotion_intent(root, config, git, decision, intent)
        marker = git.promotion_marker(experiment, decision)
        current = git.resolve_integration(experiment)
        generation = git.generation(experiment)
        if (marker is None and current == intent["expected"] and
                generation == intent["expected_generation"] and request.get("retry") is True):
            if "confirmation" in config:
                require_confirmation(root, config, git, decision)
            assessment = compare_runs(root, config, git, saved["arm"],
                                      saved["baseline_keys"], saved["candidate_keys"])
            if (saved["result"]["decision"] != "eligible" or
                    assessment != {key: saved[key] for key in ("result", "spec", "baseline", "candidate")}):
                raise ValueError("decision no longer qualifies for recovery")
            git.promote_with_marker(experiment, intent["expected"], intent["candidate"], decision,
                                    intent["expected_generation"], intent["new_generation"])
            marker = git.promotion_marker(experiment, decision)
            current = git.resolve_integration(experiment)
            generation = git.generation(experiment)
        if (marker != intent["candidate"] or current != intent["candidate"] or
                generation != intent["new_generation"]):
            return {"state": "unresolved", "current": current, "marker": marker,
                    "generation": generation}
        completed = root / "promotions" / (decision + ".completed.json")
        completion = {"expected": intent["expected"], "candidate": intent["candidate"],
                      "state": "completed"}
        if completed.is_symlink():
            raise ValueError("promotion completion was replaced")
        if completed.exists():
            if read(completed) != completion:
                raise ValueError("promotion completion does not match the intent")
        else:
            write_new(completed, completion)
        return {"state": "completed", "commit": current}
    if action == "retire":
        if selection_path(root, git, config).exists():
            _, decision = selected_finalist(root, config, git)
            if request.get("arm") == decision["arm"]:
                raise ValueError("cannot retire the selected finalist")
        if request.get("writers_stopped") is not True:
            raise ValueError("confirm all arm writers have stopped")
        receipt = git.retire(experiment, name(request["arm"]), request["expected"],
                             archive=request.get("archive", False))
        return {"archive": receipt}
    if action == "feedback":
        record = feedback_revision(request["id"], request["observation"], request["interpretation"],
                                   request["counterexample"], request["old_contract"],
                                   request["new_contract"], request["changes"])
        write_new(root / "feedback" / (name(request["id"]) + ".json"), record)
        return record
    if action == "calibrate":
        return validate_calibration(request["records"])
    if action == "revise":
        feedback = read(root / "feedback" / (name(request["feedback"]) + ".json"))
        if feedback["old_contract"] != config["contract"]["sha256"]:
            raise ValueError("feedback does not apply to the active contract")
        contract_path = str(Path(request["contract_file"]).resolve(strict=True))
        evaluator_path = str(Path(request["evaluator_file"]).resolve(strict=True))
        if digest(contract_path) != feedback["new_contract"]:
            raise ValueError("new contract does not match feedback revision")
        backend = request.get("backend", config.get("backend"))
        if backend is not None:
            if request.get("registry") or request.get("evaluator_dependencies"):
                raise ValueError("Harbor revision cannot use a local target registry")
            validate_controller_harbor(backend, {"path": evaluator_path, "sha256": digest(evaluator_path)})
            registry = {}
            executable = {"path": backend["harbor_bin"], "sha256": backend["harbor_bin_sha256"]}
        else:
            registry, executable = validate_target(request["registry"], config["target"], evaluator_path,
                                                   request.get("trusted_interpreter"))
        updated = dict(config)
        if backend is not None:
            updated["backend"] = backend
            updated["evaluator_dependencies"] = []
        else:
            updated.pop("backend", None)
        updated["contract"] = {"path": contract_path, "sha256": digest(contract_path)}
        updated["evaluator"] = {"path": evaluator_path, "sha256": digest(evaluator_path)}
        updated["executable"] = executable
        updated["registry"] = registry
        if "evaluator_dependencies" in request:
            updated["evaluator_dependencies"] = dependency_manifest(request["evaluator_dependencies"])
        if backend is None:
            check_native_config(evaluator_path, registry, config["target"], updated.get("evaluator_dependencies", []))
        # Preserve the comparison rules unless a new one is explicitly supplied.
        updated["evaluation"] = dict(request.get("evaluation", config["evaluation"]))
        check_evaluation_fields(updated["evaluation"])
        if "case" in updated["evaluation"]:
            if "cases" in updated["evaluation"]:
                raise ValueError("choose case or cases, not both")
            updated["evaluation"]["cases"] = [updated["evaluation"].pop("case")]
        if "confirmation" in request:
            if request["confirmation"] is None:
                raise ValueError("confirmation cannot be null")
            updated["confirmation"] = request["confirmation"]
        if selection_path(root, git, config).exists():
            confirmation = request["confirmation"]
            if not isinstance(confirmation, dict) or set(confirmation) != {"cases", "repetitions"}:
                raise ValueError("confirmation must specify cases and repetitions")
            new_cases = confirmation["cases"]
            if (not isinstance(new_cases, list) or not new_cases or
                    any(not isinstance(case, str) or not case.strip() for case in new_cases) or
                    len(set(new_cases)) != len(new_cases) or
                    type(confirmation["repetitions"]) is not int or
                    not 1 <= confirmation["repetitions"] <= 100):
                raise ValueError("invalid fresh confirmation assignments")
            used_cases = set()
            for path in [root / "experiment.json", *(root / "revisions").glob("*.json")]:
                previous = read(path)
                used_cases.update(previous.get("confirmation", {}).get("cases", []))
            selection_cases = updated["evaluation"].get("cases", [])
            if (set(new_cases) & (set(selection_cases) | used_cases) or
                    set(selection_cases) & used_cases):
                raise ValueError("fresh confirmation and selection cases must exclude exposed confirmation cases")
            if backend is None and "{{case}}" not in registry[config["target"]]["argv"]:
                raise ValueError("confirmation target must pass {{case}}")
            updated["confirmation"] = confirmation
        validate_revised_cases(updated)
        case_paths = request.get("case_files", {key: value["path"] for key, value in config["case_files"].items()})
        updated["case_files"] = freeze_cases(case_paths, updated["evaluation"]["cases"],
                                              updated.get("confirmation", {}).get("cases", []))
        retain_cases(root, updated["case_files"])
        check_case_separation(root, updated)
        identity = baseline_identity(git, config)
        _validate_spec(evaluation_spec(updated, identity, identity))
        if backend is not None:
            harbor_measurement_names(updated["evaluation"])
        labels = request["calibration"]
        permitted_gates = set(updated["evaluation"]["required_gates"] + updated["evaluation"].get("candidate_only_gates", []))
        if (not isinstance(labels, list) or not labels or any(not isinstance(label, dict) or label.get("gate") not in permitted_gates for label in labels) or
                len({label["gate"] for label in labels}) != 1):
            raise ValueError("calibration labels must exercise one required gate")
        calibration = calibration_from_runs(root, experiment, labels, digest(evaluator_path),
                                            target_digest(registry, executable, updated.get("evaluator_dependencies", []), backend))
        if not calibration["qualified"]:
            raise ValueError("new evaluator calibration did not qualify")
        content = json.dumps(updated, sort_keys=True, allow_nan=False) + "\n"
        sha = hashlib.sha256(content.encode()).hexdigest()
        if sha == config_digest(root):
            raise ValueError("revision must change the harness configuration")
        if (root / "selections" / (git.generation(experiment) + "-" + sha + ".json")).exists():
            raise ValueError("revision cannot reactivate an earlier selection")
        relative = Path("revisions") / (sha + ".json")
        revision_path = root / relative
        revision_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with revision_path.open("x", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if digest(revision_path) != sha:
                raise ValueError("revision artifact collision")
        applied_path = root / "feedback" / (request["feedback"] + "." + sha + ".json")
        if not applied_path.exists():
            write_new(applied_path, {"revision": sha, "calibration": calibration})
        with sqlite3.connect(root / "ledger.sqlite3", isolation_level=None) as db:
            db.execute("BEGIN IMMEDIATE")
            pending = db.execute(
                "SELECT COUNT(*) FROM runs WHERE experiment=? AND status IN ('reserved','dispatched','uncertain')",
                (experiment,)).fetchone()[0]
            if pending:
                db.rollback()
                raise ValueError("finish or reconcile outstanding runs before revision")
            old = db.execute("SELECT digest FROM controller_config WHERE id=1").fetchone()[0]
            db.execute("UPDATE controller_config SET digest=?, path=? WHERE id=1 AND digest=?",
                       (sha, str(relative), old))
            db.commit()
        return {"revision": sha, "calibration": calibration}
    if action == "regrade":
        return regrade_matrix(request["old_spec"], request["new_spec"],
                              request["old_baseline"], request["old_candidate"],
                              request["new_baseline"], request["new_candidate"],
                              request["evidence_root"])
    if action == "regrade-capture":
        from experiment_regrade import capture
        return capture(root, git, request["capture"], request["old_decision"], request["new_decision"])
    raise ValueError("unknown experiment action")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, help="JSON request file")
    args = parser.parse_args()
    try:
        print(json.dumps(execute(read(args.request)), sort_keys=True, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
