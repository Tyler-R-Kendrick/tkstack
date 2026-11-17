#!/usr/bin/env python3
"""Use an optional GEPA engine to search supplied local text proposals.

The adapter executes the experiment's registered target through the existing
controller. It makes no model calls and cannot enforce a model-provider budget.
Suggestions still require the normal paired comparison and confirmation.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path, PurePosixPath
import sys

import experiment
from experiment_git import GitExperiment, _paths, _inside_scope
from experiment_ledger import Ledger
from json_contract import loads


MAX_ARTIFACT_BYTES = 1024 * 1024


class EvaluationBudgetExhausted(Exception):
    pass


class ProposalBudgetExhausted(Exception):
    pass


class Quiet:
    def log(self, message):
        pass


def _positive_int(value, name):
    if type(value) is not int or not 0 < value <= 10_000:
        raise ValueError(f"{name} must be an integer between 1 and 10000")
    return value


def _case_list(value, name, available):
    if (not isinstance(value, list) or not value or
            any(not isinstance(item, str) or item not in available for item in value) or
            len(value) != len(set(value))):
        raise ValueError(f"{name} must be a nonempty unique list of declared selection cases")
    return value


def _artifact_path(value, allowed):
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("artifact_path must name a repository file")
    _paths([value])
    path = PurePosixPath(value)
    if path.as_posix() in (".", "") or not _inside_scope(path.as_posix(), _paths(allowed)):
        raise ValueError("artifact_path must be inside the declared editable scope")
    return path.as_posix()


def _write_candidate(worktree, relative, text):
    root = Path(worktree).resolve(strict=True)
    path = root
    for component in PurePosixPath(relative).parts[:-1]:
        path = path / component
        if path.is_symlink():
            raise ValueError("candidate path traverses a symlink")
        path.mkdir(exist_ok=True)
    target = path / PurePosixPath(relative).name
    if target.is_symlink() or not target.resolve().is_relative_to(root):
        raise ValueError("candidate path escapes the worktree")
    if target.exists() and (not target.is_file() or target.stat().st_nlink != 1):
        raise ValueError("candidate path must be an unshared regular file")
    target.write_text(text, encoding="utf-8")


def _load_gepa():
    try:
        version = importlib.metadata.version("gepa")
        if version != "0.1.4":
            raise ValueError(f"GEPA 0.1.4 is required; found {version}")
        from gepa.optimize_anything import (
            EngineConfig, GEPAConfig, ReflectionConfig, TrackingConfig, optimize_anything,
        )
    except (ImportError, importlib.metadata.PackageNotFoundError) as error:
        raise ValueError("GEPA is unavailable; install gepa==0.1.4 in an isolated environment") from error
    return EngineConfig, GEPAConfig, ReflectionConfig, TrackingConfig, optimize_anything


def optimize(request):
    from experiment_runner import cancellation_scope
    with cancellation_scope():
        return _optimize(request)


def _optimize(request):
    if not isinstance(request, dict):
        raise ValueError("request must be a JSON object")
    if request.get("max_model_tokens") != 0 or type(request.get("max_model_tokens")) is not int:
        raise ValueError("model-provider token budgets require a provider-enforced adapter; this local proposer makes no model calls")
    search = experiment.name(request["search"])
    search_tag = hashlib.sha256(search.encode("utf-8")).hexdigest()[:20]
    root = Path(request["root"]).resolve(strict=True)
    max_evaluations = _positive_int(request["max_evaluations"], "max_evaluations")
    max_proposals = _positive_int(request["max_proposals"], "max_proposals")
    proposed = request["proposals"]
    if (not isinstance(proposed, list) or len(proposed) > 100 or len(proposed) < max_proposals or
            any(not isinstance(item, str) or len(item.encode("utf-8")) > MAX_ARTIFACT_BYTES for item in proposed)):
        raise ValueError("proposals must contain at least max_proposals bounded text candidates")
    objective = request.get("objective", "Improve the registered task quality metric.")
    if not isinstance(objective, str) or not objective.strip() or len(objective) > 10000:
        raise ValueError("objective must be nonempty bounded text")
    limits = request["metric_range"]
    if (not isinstance(limits, list) or len(limits) != 2 or
            any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in limits) or
            limits[0] >= limits[1]):
        raise ValueError("metric_range must contain finite lower and upper bounds")
    config = experiment.config_for(root)
    experiment.check_inputs(config)
    git = GitExperiment.open(root)
    artifact = _artifact_path(request["artifact_path"], config["paths"])
    available = config["evaluation"]["cases"]
    training = _case_list(request["training_cases"], "training_cases", available)
    selection = _case_list(request["selection_cases"], "selection_cases", available)
    if set(training) & set(selection):
        raise ValueError("training and selection cases must be disjoint")
    training_hashes = {config["case_files"][case]["sha256"] for case in training}
    selection_hashes = {config["case_files"][case]["sha256"] for case in selection}
    if training_hashes & selection_hashes:
        raise ValueError("training and selection case bytes must be disjoint")
    if experiment.selection_path(root, git, config).exists():
        raise ValueError("a finalist has already been selected")
    ledger = Ledger(root / "ledger.sqlite3")
    ledger.configure_proposals(config["experiment"], max_proposals=config.get("max_proposals", 5))
    status = ledger.status(config["experiment"])
    remaining = status["max_trials"] - status["settled_trials"] - status["reserved_trials"]
    if max_proposals > status["max_proposals"] - status["proposal_count"]:
        raise ValueError("experiment proposal budget exhausted or too small for this search")
    if max_evaluations > remaining:
        raise ValueError("search evaluation budget exceeds remaining experiment trials")
    EngineConfig, GEPAConfig, ReflectionConfig, TrackingConfig, optimize_anything = _load_gepa()
    base = experiment.baseline_identity(git, config)["commit"]
    generation = git.generation(config["experiment"])
    seed = git._git("show", f"{base}:{artifact}").stdout
    if len(seed.encode("utf-8")) > MAX_ARTIFACT_BYTES:
        raise ValueError("seed artifact exceeds the size limit")

    search_dir = root / "optimizer" / search
    search_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    lock_path = root / "optimizer.lock"
    calls = 0
    proposals_made = 0
    candidates = {}
    config_id = experiment.config_digest(root)
    lower, upper = limits

    with experiment.controller_lock(root, True), lock_path.open("a+") as lock, (search_dir / "trace.jsonl").open("x", encoding="utf-8") as trace:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (experiment.config_digest(root) != config_id or
                git.resolve_integration(config["experiment"]) != base or
                git.generation(config["experiment"]) != generation):
            raise ValueError("experiment changed before search could acquire ownership")
        experiment.remaining_time(root, config)
        current = ledger.status(config["experiment"])
        if max_proposals > current["max_proposals"] - current["proposal_count"]:
            raise ValueError("experiment proposal budget exhausted or too small for this search")

        def log(event):
            trace.write(json.dumps(event, sort_keys=True, allow_nan=False) + "\n")
            trace.flush()
            os.fsync(trace.fileno())

        def arm_for(candidate):
            candidate_bytes = candidate.encode("utf-8")
            if len(candidate_bytes) > MAX_ARTIFACT_BYTES:
                raise ValueError("candidate exceeds the size limit")
            identity = hashlib.sha256(candidate_bytes).hexdigest()
            if identity in candidates:
                return candidates[identity]
            arm = "g-" + search_tag + "-" + identity[:24]
            created = experiment.execute_locked({"action": "allocate", "root": str(root), "arm": arm}, root)
            _write_candidate(created["worktree"], artifact, candidate)
            frozen = experiment.execute_locked({
                "action": "freeze", "root": str(root), "arm": arm,
                "message": "Freeze GEPA experiment candidate", "writers_stopped": True,
            }, root)
            candidates[identity] = {"arm": arm, **frozen}
            log({"event": "candidate", "sha256": identity, "arm": arm, **frozen})
            return candidates[identity]

        def evaluator(candidate, example):
            nonlocal calls
            if (experiment.config_digest(root) != config_id or
                    git.resolve_integration(config["experiment"]) != base or
                    git.generation(config["experiment"]) != generation):
                raise ValueError("experiment changed during search")
            experiment.remaining_time(root, config)
            entry = arm_for(candidate)
            identity = {"commit": entry["commit"], "tree": entry["tree"]}
            claim = experiment.selection_claim(root, config, git, "candidate", identity, example, 0)
            prior = ledger.selection_run(config["experiment"], claim)
            if prior:
                if prior["status"] != "settled":
                    raise ValueError("selection assignment is not settled; reconcile before reuse")
                run_key = experiment.name(prior["run_key"])
                receipt_path = root / "runs" / (run_key + ".json")
                result = experiment.read(receipt_path)
                state = ledger.status(config["experiment"])
                settlements = [event for event in state["events"]
                               if event["run_key"] == run_key and event["operation"] == "settle"]
                artifact_path = root / "evidence" / (run_key + ".json")
                if (len(settlements) != 1 or settlements[0]["details"]["receipt_sha256"] != experiment.digest(receipt_path)
                        or result.get("config_digest") != config_id or result.get("generation") != generation
                        or result.get("side") != "candidate"
                        or result.get("case") != example or result.get("rep") != 0
                        or result.get("split", "selection") != "selection"
                        or result.get("identity", {}).get("tree") != entry["tree"]
                        or experiment.digest(artifact_path) != result.get("artifact_sha256")
                        or artifact_path.read_text(encoding="utf-8") != result["result"]["stdout"]):
                    raise ValueError("cached selection receipt does not match its ledger assignment")
                log({"event": "reuse", "run_key": run_key, "tree": entry["tree"]})
            else:
                if calls >= max_evaluations:
                    raise EvaluationBudgetExhausted("evaluation allowance exhausted")
                calls += 1
                run_key = "g-" + search_tag + "-" + str(calls)
                result = experiment.execute_locked({
                    "action": "run", "root": str(root), "side": "candidate",
                    "arm": entry["arm"], "case": example, "rep": 0, "run_key": run_key,
                }, root)
            execution = result["result"]
            if execution["status"] != "passed" or execution["stdout_truncated"]:
                raise ValueError(f"experiment trial {run_key} did not complete successfully")
            if "backend" in config:
                gates, metrics = experiment.harbor_measurement_names(config["evaluation"])
                experiment.verify_controller_harbor(
                    execution, config["backend"], config["evaluator"],
                    case_sha256=config["case_files"][example]["sha256"],
                    required_gates=gates, metric_names=metrics,
                )
            measurement = loads(execution["stdout"])
            if not isinstance(measurement, dict):
                raise ValueError("evaluator output must be an object")
            case_digest = config["case_files"][example]["sha256"]
            if (result.get("case_sha256") != case_digest or
                    measurement.get("case_sha256") != case_digest):
                raise ValueError("evaluator did not attest the frozen case input")
            gates = measurement.get("gates")
            required = config["evaluation"]["required_gates"] + config["evaluation"].get("candidate_only_gates", [])
            if not isinstance(gates, dict) or any(type(gates.get(gate)) is not bool for gate in required):
                raise ValueError("required gate evidence is missing")
            work = measurement.get("work_count")
            metric = measurement.get("metrics", {}).get(config["evaluation"]["metric"])
            if (isinstance(work, bool) or not isinstance(work, (int, float)) or not math.isfinite(work) or work <= 0 or
                    isinstance(metric, bool) or not isinstance(metric, (int, float)) or not math.isfinite(metric) or
                    not lower <= metric <= upper):
                raise ValueError("trial has invalid work count or metric")
            score = (metric - lower) / (upper - lower)
            if config["evaluation"]["direction"] == "lower":
                score = 1 - score
            gates_pass = all(gates[gate] for gate in required)
            if not gates_pass:
                score = 0.0
            feedback = {"case": example, "case_sha256": case_digest, "run_key": run_key, "arm": entry["arm"],
                        "gates": gates, "metric": metric, "work_count": work,
                        "artifact_sha256": result["artifact_sha256"]}
            log({"event": "evaluation", "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
                 "score": score, **feedback})
            return score, feedback

        def proposer(candidate, reflective_dataset, components_to_update):
            nonlocal proposals_made
            if proposals_made >= max_proposals:
                raise ProposalBudgetExhausted("local proposal allowance exhausted")
            if not isinstance(components_to_update, list) or len(components_to_update) != 1:
                raise ValueError("local text proposer requires one selected component")
            component = components_to_update[0]
            if component not in candidate or not isinstance(candidate[component], str):
                raise ValueError("GEPA candidate is missing its text component")
            experiment.remaining_time(root, config)
            index = proposals_made + 1
            run_key = "gp-" + search_tag + "-" + str(index)
            # Check before reserving as Ledger.reserve is intentionally idempotent.
            # The controller lock serializes cooperating users of this experiment.
            if any(row["run_key"] == run_key for row in ledger.status(config["experiment"])["runs"]):
                raise ValueError("proposal run key already exists")
            try:
                reservation = ledger.reserve(config["experiment"], run_key, tokens=0,
                                             trial_units=0, proposal=True)
            except ValueError as error:
                if "proposal budget exhausted" in str(error).lower():
                    raise ProposalBudgetExhausted(str(error)) from error
                raise
            if reservation["status"] != "reserved":
                raise ValueError("proposal reservation is not available")
            grant = ledger.dispatch(config["experiment"], run_key)
            if not grant["dispatch_granted"]:
                raise ValueError("proposal already dispatched; reconcile before retrying")
            proposals_made = index
            try:
                proposal = proposed[index - 1]
                receipt = {
                    "kind": "gepa-local-proposal", "search": search, "index": index,
                    "config_digest": config_id, "component": component,
                    "parent_sha256": hashlib.sha256(candidate[component].encode()).hexdigest(),
                    "proposal_sha256": hashlib.sha256(proposal.encode()).hexdigest(),
                    "usage_tokens": 0,
                }
                receipt_path = search_dir / "proposals" / (str(index) + ".json")
                experiment.write_new(receipt_path, receipt)
                ledger.settle(config["experiment"], run_key, actual_tokens=0,
                              receipt_sha256=experiment.digest(receipt_path))
            except BaseException:
                try:
                    ledger.uncertain(config["experiment"], run_key,
                                     "GEPA proposal outcome requires reconciliation")
                except (OSError, ValueError):
                    pass
                raise
            log({"event": "proposal", "index": index, "run_key": run_key,
                 "sha256": receipt["proposal_sha256"], "receipt": str(receipt_path)})
            return {component: proposal}

        log({"event": "start", "base": base, "generation": generation, "config_digest": config_id,
             "artifact_path": artifact, "training_cases": training, "selection_cases": selection,
             "max_evaluations": max_evaluations, "max_proposals": max_proposals,
             "gepa_version": "0.1.4", "model_tokens": 0})
        try:
            result = optimize_anything(
                seed_candidate=seed, evaluator=evaluator, dataset=training, valset=selection,
                objective=objective,
                config=GEPAConfig(
                    engine=EngineConfig(max_metric_calls=max_evaluations,
                                        max_candidate_proposals=max_proposals,
                                        parallel=False, use_cloudpickle=False,
                                        raise_on_exception=True, display_progress_bar=False),
                    reflection=ReflectionConfig(reflection_lm=None, custom_candidate_proposer=proposer,
                                                reflection_minibatch_size=1),
                    tracking=TrackingConfig(logger=Quiet()),
                ),
            )
            text = result.best_candidate
            entry = candidates.get(hashlib.sha256(text.encode("utf-8")).hexdigest())
            if entry is None:
                raise ValueError("GEPA returned a candidate without an evaluated Git arm")
            result_data = {"status": "complete", "suggestion": {"candidate": text, **entry}}
        except EvaluationBudgetExhausted:
            result_data = {"status": "budget_exhausted", "suggestion": None}
        except ProposalBudgetExhausted:
            result_data = {"status": "proposal_budget_exhausted", "suggestion": None}
        except Exception as error:
            log({"event": "error", "kind": type(error).__name__, "message": str(error)})
            raise
        finally:
            log({"event": "stop", "evaluations": calls, "proposals": proposals_made})
            fcntl.flock(lock, fcntl.LOCK_UN)
    return {**result_data, "evaluations": calls, "proposals": proposals_made,
            "trace": str(search_dir / "trace.jsonl"),
            "limitations": "GEPA's suggestion is exploratory; compare gates and confirm independently before promotion. No model or provider budget is managed."}


def main():
    with experiment.cancellation_handler():
        return _main()


def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    try:
        data = Path(args.request).read_bytes()
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("request exceeds 8 MiB")
        request = loads(data.decode("utf-8"))
        print(json.dumps(optimize(request), sort_keys=True, allow_nan=False))
        return 0
    except KeyboardInterrupt:
        print('experiment interrupted; inspect ledger before retrying', file=sys.stderr)
        return 130
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
