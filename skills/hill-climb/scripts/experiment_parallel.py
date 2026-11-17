#!/usr/bin/env python3
"""Run a bounded, preallocated batch of frozen local experiment trials.

This is a data interface to the existing controller, not a workflow language.
The selected target executes with host privileges. Each trial gets a separate
source export. Host-level isolation and measurement independence are the
operator's responsibility.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

import experiment
from experiment_git import GitExperiment
from experiment_ledger import Ledger, _now, _insert_selection_claim
from experiment_runner import run_trial
from json_contract import loads


MAX_TRIALS = 128
MAX_WORKERS = 16


def reserve_batch(ledger, experiment_id, batch, keys, metadata=None, selection_claims=None):
    """Reserve all trial slots in one transaction, or reserve none."""
    experiment.name(experiment_id)
    experiment.name(batch)
    if not isinstance(keys, list) or not keys or len(keys) > MAX_TRIALS:
        raise ValueError("batch must contain a bounded, nonempty list of run keys")
    keys = [experiment.name(key) for key in keys]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate run key")
    if selection_claims is not None and (not isinstance(selection_claims, dict) or set(selection_claims) != set(keys)):
        raise ValueError("selection claims must cover the batch")
    connection = ledger._connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        budget = ledger._experiment(connection, experiment_id)
        if budget["overrun"]:
            raise ValueError("experiment is stopped after a provider overrun")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS parallel_batches "
            "(experiment TEXT NOT NULL, batch TEXT NOT NULL, run_keys TEXT NOT NULL, metadata TEXT NOT NULL, "
            "PRIMARY KEY (experiment, batch), "
            "FOREIGN KEY (experiment) REFERENCES experiments(experiment))"
        )
        existing_batch = connection.execute(
            "SELECT 1 FROM parallel_batches WHERE experiment=? AND batch=?", (experiment_id, batch)
        ).fetchone()
        if existing_batch:
            raise ValueError("batch already exists")
        rows = connection.execute("SELECT * FROM runs WHERE experiment=?", (experiment_id,)).fetchall()
        if set(keys) & {row["run_key"] for row in rows}:
            raise ValueError("run key already exists")
        totals = ledger._totals(rows)
        if totals["settled_trials"] + totals["reserved_trials"] + len(keys) > budget["max_trials"]:
            raise ValueError("experiment budget exhausted")
        if metadata is None:
            metadata = {"run_keys": keys}
        serialized = json.dumps(metadata, sort_keys=True, allow_nan=False)
        connection.execute(
            "INSERT INTO parallel_batches(experiment,batch,run_keys,metadata) VALUES (?,?,?,?)",
            (experiment_id, batch, json.dumps(keys), serialized),
        )
        for key in keys:
            connection.execute(
                "INSERT INTO runs(experiment,run_key,reserved_tokens,trial_units,status,created_at) "
                "VALUES (?,?,0,1,'reserved',?)", (experiment_id, key, _now())
            )
            if selection_claims is not None:
                _insert_selection_claim(connection, experiment_id, key, selection_claims[key])
            ledger._event(connection, experiment_id, key, "reserve",
                          {"tokens": 0, "trial_units": 1, "batch": batch})
        connection.commit()
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def _prepare(root, config, git, trials):
    if not isinstance(trials, list) or not 1 <= len(trials) <= MAX_TRIALS:
        raise ValueError(f"trials must contain 1..{MAX_TRIALS} assignments")
    splits = {trial.get("split", "selection") for trial in trials if isinstance(trial, dict)}
    if len(splits) != 1 or not splits <= {"selection", "confirmation"}:
        raise ValueError("batch must contain one valid evaluation split")
    split = next(iter(splits))
    selected = experiment.selection_path(root, git, config).exists()
    if split == "selection":
        if selected:
            raise ValueError("selection is locked after selecting a finalist")
        experiment.check_case_separation(root, config)
        assignments = config["evaluation"]
        decision = None
    else:
        _, decision = experiment.selected_finalist(root, config, git)
        if experiment.confirmation_path(root, git, config).exists():
            raise ValueError("confirmation has already been evaluated")
        assignments = config["confirmation"]
    prepared = []
    seen = set()
    for trial in trials:
        if not isinstance(trial, dict):
            raise ValueError("each trial must be an object")
        if set(trial) - {"side", "arm", "case", "rep", "run_key", "split"}:
            raise ValueError("trial contains undeclared fields")
        side, rep = trial["side"], trial["rep"]
        if side not in ("baseline", "candidate"):
            raise ValueError("side must be baseline or candidate")
        if side == "baseline" and "arm" in trial:
            raise ValueError("baseline trial must not name an arm")
        if type(rep) is not int or not 0 <= rep < assignments["repetitions"]:
            raise ValueError("rep outside the frozen assignment")
        cases = assignments["cases"]
        case = trial.get("case", cases[0] if len(cases) == 1 else None)
        if case not in cases:
            raise ValueError("case outside the frozen assignments")
        key = experiment.name(trial["run_key"])
        arm = experiment.name(trial["arm"]) if side == "candidate" else None
        if decision is not None and side == "candidate" and arm != decision["arm"]:
            raise ValueError("confirmation requires the selected arm")
        identity = (experiment.baseline_identity(git, config) if side == "baseline"
                    else experiment.approved_identity(root, config, git, arm))
        assignment = (side, identity["commit"], case, rep)
        if assignment in seen:
            raise ValueError("duplicate trial assignment")
        seen.add(assignment)
        if (root / "runs" / (key + ".json")).exists() or (root / "evidence" / (key + ".json")).exists():
            raise ValueError("run key already has an artifact")
        case_file = config["case_files"][case]
        claim = None
        if split == "confirmation":
            # Same identity as the single-trial controller, so both paths enforce
            # one attempt for each confirmation side/case/rep.
            text = json.dumps([side, case, rep], separators=(",", ":"), ensure_ascii=False)
            claim_id = hashlib.sha256(text.encode()).hexdigest()
            claim = root / "confirmation-claims" / (
                git.generation(config["experiment"]) + "-" + experiment.config_digest(root)
            ) / (claim_id + ".json")
            if claim.exists():
                raise ValueError("confirmation assignment was already claimed")
        prepared.append({"side": side, "rep": rep, "case": case, "run_key": key, "arm": arm,
                         "identity": identity, "split": split, "case_file": case_file, "claim": claim})
    keys = [trial["run_key"] for trial in prepared]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate run key")
    return prepared


def _run_one(root, config, git, ledger, config_id, deadline, trial):
    key, experiment_id = trial["run_key"], config["experiment"]
    dispatched = False
    try:
        if time.monotonic() >= deadline:
            ledger.cancel(experiment_id, key, reason="deadline before dispatch")
            if trial["claim"] is not None:
                trial["claim"].unlink()
            return {"run_key": key, "status": "not_started", "error": "deadline before dispatch"}
        grant = ledger.dispatch(experiment_id, key)
        if not grant["dispatch_granted"]:
            return {"run_key": key, "status": "uncertain",
                    "error": "run already dispatched; reconcile before retrying"}
        dispatched = True
        case, rep, case_file = trial["case"], trial["rep"], trial["case_file"]
        identity = trial["identity"]
        if "backend" in config:
            result = experiment.run_selected(root, config, git, identity, case, rep, key, deadline)
        else:
            entry = config["registry"][config["target"]]
            argv = [case if item == "{{case}}" else str(rep) if item == "{{rep}}"
                    else case_file["path"] if item == "{{case_file}}"
                    else case_file["sha256"] if item == "{{case_sha256}}" else item
                    for item in entry["argv"]]
            registry = {config["target"]: {"argv": argv, "cwd": entry["cwd"]}}
            result = run_trial(git.repo, identity["commit"], identity["tree"], registry,
                               [config["target"]], config["target"], deadline=deadline)
        try:
            experiment.check_inputs(config)
            if experiment.config_digest(root) != config_id:
                raise ValueError("experiment configuration changed during trial")
        except (OSError, ValueError, sqlite3.Error) as error:
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
            "side": trial["side"], "case": case, "rep": rep, "identity": identity,
            "generation": git.generation(config["experiment"]),
            "split": trial["split"], "case_sha256": case_file["sha256"],
            "config_digest": config_id, "contract": config["contract"]["sha256"],
            "evaluator": config["evaluator"]["sha256"], "result": result,
            "artifact_sha256": experiment.digest(artifact_path),
        }
        result_path = root / "runs" / (key + ".json")
        experiment.write_new(result_path, record)
        experiment.settle_result(ledger, experiment_id, key, result, result_path)
        return {"run_key": key, **record}
    except Exception as error:
        # A dispatched operation may have run even if its response was lost.
        # Keep its reservation charged and never issue a duplicate dispatch.
        status = "uncertain"
        try:
            if dispatched:
                ledger.uncertain(experiment_id, key, reason=f"batch worker failed: {type(error).__name__}")
            else:
                ledger.cancel(experiment_id, key, reason="worker failed before dispatch")
                if trial["claim"] is not None:
                    trial["claim"].unlink(missing_ok=True)
                status = "not_started"
        except (ValueError, OSError, sqlite3.Error):
            # If dispatch or cancellation has an unknown outcome, do not report
            # that no operation started or release its reservation ourselves.
            pass
        return {"run_key": key, "status": status,
                "error": f"{type(error).__name__}: {error}"}


def run_batch(request):
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    if set(request) - {"root", "batch", "max_workers", "trials", "action"}:
        raise ValueError("request contains undeclared fields")
    if request.get("action", "parallel") != "parallel":
        raise ValueError("action must be parallel")
    root = Path(request["root"]).resolve(strict=True)
    if not (root / "ledger.sqlite3").is_file():
        raise ValueError("experiment ledger has not been initialized")
    batch = experiment.name(request["batch"])
    workers = request["max_workers"]
    if type(workers) is not int or not 1 <= workers <= MAX_WORKERS:
        raise ValueError(f"max_workers must be between 1 and {MAX_WORKERS}")
    with experiment.controller_lock(root, True):
        config = experiment.config_for(root)
        experiment.check_inputs(config)
        remaining = experiment.remaining_time(root, config)
        deadline = time.monotonic() + remaining
        git = GitExperiment.open(root)
        ledger = Ledger(root / "ledger.sqlite3")
        config_id = experiment.config_digest(root)
        trials = _prepare(root, config, git, request["trials"])
        keys = [trial["run_key"] for trial in trials]
        manifest = {
            "config_digest": config_id, "generation": git.generation(config["experiment"]),
            "target": config["target"],
            "deadline_epoch": config["deadline_epoch"], "max_workers": min(workers, len(trials)),
            "assignments": [
                {"side": trial["side"], "arm": trial["arm"], "case": trial["case"],
                 "case_sha256": trial["case_file"]["sha256"], "rep": trial["rep"],
                 "run_key": trial["run_key"], "split": trial["split"],
                 "identity": trial["identity"]}
                for trial in trials
            ],
        }
        claims = None
        if trials[0]["split"] == "selection":
            claims = {trial["run_key"]: experiment.selection_claim(root, config, git, trial["side"],
                      trial["identity"], trial["case"], trial["rep"]) for trial in trials}
        reserve_batch(ledger, config["experiment"], batch, keys, metadata=manifest, selection_claims=claims)
        created_claims = []
        try:
            for trial in trials:
                if trial["claim"] is not None:
                    experiment.write_new(trial["claim"], {
                        "side": trial["side"], "case": trial["case"],
                        "case_sha256": trial["case_file"]["sha256"],
                        "rep": trial["rep"], "run_key": trial["run_key"],
                    })
                    created_claims.append(trial["claim"])
                else:
                    case_id = hashlib.sha256(
                        (trial["case"] + "\0" + trial["case_file"]["sha256"]).encode()
                    ).hexdigest()
                    exposure = root / "selection-exposures" / (case_id + ".json")
                    if not exposure.exists():
                        experiment.write_new(exposure, {"case": trial["case"],
                                                       "case_sha256": trial["case_file"]["sha256"]})
        except Exception:
            for key in keys:
                ledger.cancel(config["experiment"], key, reason="batch setup failed before dispatch")
            for claim in created_claims:
                claim.unlink(missing_ok=True)
            raise
        with ThreadPoolExecutor(max_workers=min(workers, len(trials))) as pool:
            futures = [pool.submit(_run_one, root, config, git, ledger, config_id, deadline, trial)
                       for trial in trials]
            results = [future.result() for future in futures]
        complete = all(item.get("result", {}).get("status") == "passed" for item in results)
        return {"batch": batch, "status": "complete" if complete else "partial",
                "max_workers": min(workers, len(trials)), "trials": results}


def batch_status(root, batch):
    """Read a consistent manifest and ledger snapshot, including during a batch."""
    root = Path(root).resolve(strict=True)
    batch = experiment.name(batch)
    if not (root / "ledger.sqlite3").is_file():
        raise ValueError("experiment ledger has not been initialized")
    config = experiment.config_for(root)
    ledger = Ledger(root / "ledger.sqlite3")
    connection = ledger._connect()
    try:
        connection.execute("BEGIN")
        row = connection.execute(
            "SELECT run_keys,metadata FROM parallel_batches WHERE experiment=? AND batch=?",
            (config["experiment"], batch),
        ).fetchone()
        if row is None:
            raise ValueError("unknown batch")
        keys = json.loads(row["run_keys"])
        metadata = json.loads(row["metadata"])
        rows = connection.execute(
            "SELECT * FROM runs WHERE experiment=?", (config["experiment"],)
        ).fetchall()
        runs = {item["run_key"]: dict(item) for item in rows}
        result = {"batch": batch, "manifest": metadata,
                  "runs": [runs[key] for key in keys]}
        connection.commit()
        return result
    except sqlite3.OperationalError as error:
        if connection.in_transaction:
            connection.rollback()
        raise ValueError("unknown batch") from error
    finally:
        connection.close()


def recover_reserved(root, batch):
    """Release only slots that are still durably reserved and never dispatched.

    The exclusive controller lock ensures no cooperating batch is still
    dispatching. Dispatched and uncertain slots remain charged.
    Confirmation claims are retained for explicit review.
    """
    root = Path(root).resolve(strict=True)
    batch = experiment.name(batch)
    if not (root / "ledger.sqlite3").is_file():
        raise ValueError("experiment ledger has not been initialized")
    with experiment.controller_lock(root, True):
        state = batch_status(root, batch)
        config = experiment.config_for(root)
        ledger = Ledger(root / "ledger.sqlite3")
        released, retained = [], []
        for row in state["runs"]:
            if row["status"] == "reserved":
                ledger.cancel(config["experiment"], row["run_key"],
                              reason="recover undispatched parallel reservation")
                released.append(row["run_key"])
            elif row["status"] in ("dispatched", "uncertain"):
                retained.append(row["run_key"])
        return {"batch": batch, "released": released, "retained_for_reconciliation": retained,
                "confirmation_claims": "retained for explicit review"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    try:
        raw = Path(args.request).read_bytes()
        if len(raw) > 1024 * 1024:
            raise ValueError("request exceeds 1 MiB")
        request = loads(raw.decode("utf-8"))
        if isinstance(request, dict) and request.get("action") in ("status", "recover"):
            if set(request) != {"action", "root", "batch"}:
                raise ValueError("batch status/recovery accepts only root and batch")
            if request["action"] == "status":
                result = batch_status(request["root"], request["batch"])
            else:
                result = recover_reserved(request["root"], request["batch"])
        else:
            result = run_batch(request)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, sqlite3.Error) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
