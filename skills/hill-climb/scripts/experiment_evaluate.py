#!/usr/bin/env python3
"""Validate paired evidence and calibration records for experiment decisions.

These functions check supplied evidence and numeric contracts. They do not
execute an evaluator or establish that a human or model judgment is correct.
"""

import hashlib
import importlib.util
import math
from pathlib import Path
import re
import statistics


_helper_spec = importlib.util.spec_from_file_location(
    "hill_climb_measurement", Path(__file__).with_name("hill_climb.py")
)
_helper = importlib.util.module_from_spec(_helper_spec)
_helper_spec.loader.exec_module(_helper)


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def _digest(value, name, lengths=(64,)):
    if not isinstance(value, str) or len(value) not in lengths or not re.fullmatch(r"[0-9a-f]+", value):
        raise ValueError(f"{name} must be a lowercase hexadecimal digest")
    return value


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


def _identity(value, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must identify a commit and tree")
    commit = _digest(value.get("commit"), f"{name}.commit", (40, 64))
    tree = _digest(value.get("tree"), f"{name}.tree", (40, 64))
    if len(commit) != len(tree):
        raise ValueError(f"{name} commit and tree use different Git object formats")
    return {"commit": commit, "tree": tree}


def _assignments(spec):
    rows = spec.get("assignments")
    if not isinstance(rows, list) or not rows:
        raise ValueError("assignments must be a nonempty list")
    keys = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("assignment must be an object")
        case = _text(row.get("case"), "case")
        rep = row.get("rep")
        if type(rep) is not int or rep < 0:
            raise ValueError("rep must be a nonnegative integer")
        keys.append((case, rep))
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate assignment")
    return set(keys)


def _validate_spec(spec):
    if not isinstance(spec, dict) or spec.get("version") != 1:
        raise ValueError("unsupported experiment specification")
    _digest(spec.get("contract"), "contract")
    _digest(spec.get("evaluator"), "evaluator")
    _identity(spec.get("baseline"), "baseline")
    _identity(spec.get("candidate"), "candidate")
    expected = _assignments(spec)
    gates = spec.get("required_gates")
    candidate_only = spec.get("candidate_only_gates", [])
    for names in (gates, candidate_only):
        if not isinstance(names, list):
            raise ValueError("gate classes must be lists")
        for gate in names:
            _text(gate, "gate")
        if len(names) != len(set(names)):
            raise ValueError("gate names must be unique")
    if not gates and not candidate_only:
        raise ValueError("at least one required gate is needed")
    if set(gates) & set(candidate_only):
        raise ValueError("preservation and candidate-only gates must be disjoint")
    _text(spec.get("metric"), "metric")
    if spec.get("direction") not in ("higher", "lower"):
        raise ValueError("direction must be higher or lower")
    if _number(spec.get("min_gain"), "min_gain") <= 0:
        raise ValueError("min_gain must be positive")
    if _number(spec.get("noise_floor"), "noise_floor") < 0:
        raise ValueError("noise_floor cannot be negative")
    if type(spec.get("deterministic")) is not bool:
        raise ValueError("deterministic must be a boolean")
    qualitative = spec.get("required_qualitative", [])
    if not isinstance(qualitative, list) or len(qualitative) != len(set(qualitative)):
        raise ValueError("required qualitative criteria must be a unique list")
    for criterion in qualitative:
        _text(criterion, "qualitative criterion")
    guards = spec.get("guardrails", [])
    if not isinstance(guards, list):
        raise ValueError("guardrails must be a list")
    guard_names = set()
    for guard in guards:
        if not isinstance(guard, dict):
            raise ValueError("guardrail must be an object")
        name = _text(guard.get("metric"), "guardrail metric")
        if name == spec["metric"] or name in guard_names or guard.get("direction") not in ("higher", "lower"):
            raise ValueError("guardrails must be distinct and have a valid direction")
        if _number(guard.get("tolerance"), "guardrail tolerance") < 0:
            raise ValueError("guardrail tolerance must be nonnegative")
        guard_names.add(name)
    return expected


def _checked_artifacts(row, root):
    receipts = row.get("artifacts")
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("missing evidence artifacts")
    result = {}
    root = Path(root).resolve(strict=True)
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ValueError("invalid evidence receipt")
        name = _text(receipt.get("path"), "artifact path")
        path = (root / name).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("artifact must be a file under the evidence root")
        digest = _digest(receipt.get("sha256"), "artifact sha256")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("evidence artifact digest mismatch")
        if name in result:
            raise ValueError("duplicate evidence artifact")
        result[name] = digest
    return result


def _rows(spec, rows, role, expected, root):
    if not isinstance(rows, list):
        raise ValueError(f"{role} evidence must be a list")
    found = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("evidence must be an object")
        key = (_text(row.get("case"), "case"), row.get("rep"))
        if type(key[1]) is not int or key not in expected or key in found:
            raise ValueError("unknown or duplicate assignment")
        target = _identity(row, role)
        if target != _identity(spec[role], role):
            raise ValueError(f"{role} commit or tree mismatch")
        provenance = row.get("provenance")
        if provenance is not None:
            if not isinstance(provenance, dict) or set(provenance) != {"kind", "run_key", "source"}:
                raise ValueError("invalid trial provenance")
            _text(provenance["run_key"], "provenance run key")
            source = _identity(provenance["source"], "provenance source")
            kind = "direct" if source == target else "same-tree"
            if source["tree"] != target["tree"] or provenance["kind"] != kind:
                raise ValueError("trial provenance does not establish tree equivalence")
        if row.get("contract") != spec["contract"] or row.get("evaluator") != spec["evaluator"]:
            raise ValueError("mixed contract or evaluator revision")
        if row.get("status") != "completed":
            raise ValueError("trial did not complete")
        gates = row.get("gates")
        if not isinstance(gates, dict):
            raise ValueError("required gates missing")
        for name in spec["required_gates"] + spec.get("candidate_only_gates", []):
            if type(gates.get(name)) is not bool:
                raise ValueError(f"gate {name} missing or abstained")
        metrics = row.get("metrics")
        if not isinstance(metrics, dict):
            raise ValueError("metrics missing")
        _number(metrics.get(spec["metric"]), spec["metric"])
        for guard in spec.get("guardrails", []):
            _number(metrics.get(guard["metric"]), guard["metric"])
        if _number(row.get("work_count"), "work_count") <= 0:
            raise ValueError("work_count must be positive")
        artifacts = _checked_artifacts(row, root)
        qualitative = row.get("qualitative", {})
        if not isinstance(qualitative, dict):
            raise ValueError("qualitative judgments must be an object")
        if any(name not in qualitative for name in spec.get("required_qualitative", [])):
            raise ValueError("required qualitative judgment missing")
        for criterion, judgment in qualitative.items():
            _text(criterion, "qualitative criterion")
            if not isinstance(judgment, dict) or judgment.get("rating") is None:
                raise ValueError("qualitative judgment abstained")
            _number(judgment["rating"], "rating")
            _text(judgment.get("rationale"), "rationale")
            cited = judgment.get("evidence")
            if not isinstance(cited, list) or not cited or any(name not in artifacts for name in cited):
                raise ValueError("qualitative judgment lacks referenced evidence")
            if criterion == spec["metric"] and judgment["rating"] != metrics[criterion]:
                raise ValueError("qualitative rating and metric disagree")
        found[key] = row
    if set(found) != expected:
        raise ValueError("incomplete assignment coverage")
    return found


def compare(spec, baseline_rows, candidate_rows, evidence_root):
    """Compare complete paired records against a frozen spec; no side effects."""
    expected = _validate_spec(spec)
    try:
        baseline = _rows(spec, baseline_rows, "baseline", expected, evidence_root)
        candidate = _rows(spec, candidate_rows, "candidate", expected, evidence_root)
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {"decision": "inconclusive", "reasons": [str(error)]}
    if any(not all(row["gates"][gate] for gate in spec["required_gates"]) for row in baseline.values()):
        return {"decision": "inconclusive", "reasons": ["baseline required gate failed"]}
    candidate_gates = spec["required_gates"] + spec.get("candidate_only_gates", [])
    if any(not all(row["gates"][gate] for gate in candidate_gates) for row in candidate.values()):
        return {"decision": "reject", "reasons": ["candidate required gate failed"]}
    if any(baseline[key]["work_count"] != candidate[key]["work_count"] for key in expected):
        return {"decision": "inconclusive", "reasons": ["paired trials performed different amounts of work"]}
    target = _helper.paired_metric(baseline, candidate, spec["metric"], spec["direction"])
    if not spec["deterministic"] and target["independent_cases"] < 2:
        return {"decision": "inconclusive", "target": target, "reasons": ["insufficient independent cases"]}
    observed_noise = 0.0
    if not spec["deterministic"]:
        cases = sorted({case for case, _ in expected})
        samples = [[baseline[key]["metrics"][spec["metric"]] for key in expected if key[0] == case]
                   for case in cases]
        if spec["noise_floor"] <= 0 or any(len(sample) < 2 for sample in samples):
            return {"decision": "inconclusive", "target": target,
                    "reasons": ["stochastic comparison needs a positive noise floor and repeated baseline for every case"]}
        observed_noise = max(statistics.stdev(sample) for sample in samples)
    guards = {}
    for guard in spec.get("guardrails", []):
        measured = _helper.paired_metric(baseline, candidate, guard["metric"], guard["direction"])
        guards[guard["metric"]] = measured
        sign = 1 if guard["direction"] == "higher" else -1
        for case in sorted({case for case, _ in expected}):
            changes = [sign * (candidate[key]["metrics"][guard["metric"]] - baseline[key]["metrics"][guard["metric"]])
                       for key in expected if key[0] == case]
            if statistics.mean(changes) < -guard["tolerance"]:
                return {"decision": "reject" if spec["deterministic"] else "inconclusive",
                        "target": target, "guardrails": guards,
                        "reasons": [f"guardrail {guard['metric']} regressed for case {case}"]}
        if measured["gain"] < -guard["tolerance"]:
            return {"decision": "reject", "target": target, "guardrails": guards,
                    "reasons": [f"guardrail {guard['metric']} regressed"]}
        if measured["gain"] - (measured["paired_95_half_width"] or 0) < -guard["tolerance"]:
            return {"decision": "inconclusive", "target": target, "guardrails": guards,
                    "reasons": [f"guardrail {guard['metric']} not established"]}
    if target["gain"] < spec["min_gain"]:
        return {"decision": "reject", "target": target, "reasons": ["gain below meaningful improvement"]}
    half_width = target["paired_95_half_width"] or 0
    if target["gain"] - half_width < spec["min_gain"] or target["gain"] <= max(spec["noise_floor"], observed_noise):
        return {"decision": "inconclusive", "target": target, "observed_baseline_noise": observed_noise,
                "reasons": ["gain not established beyond uncertainty"]}
    return {"decision": "eligible", "target": target, "guardrails": guards, "reasons": [],
            "observed_baseline_noise": observed_noise,
            "limitations": "Numeric eligibility only; semantic correctness, evaluator independence and holdout isolation require separate review."}


def feedback_revision(feedback_id, observation, interpretation, counterexample, old_contract, new_contract, changes):
    """Record a proposed feedback-driven contract change without applying it."""
    for value, name in ((feedback_id, "feedback id"), (observation, "observation"),
                        (interpretation, "interpretation"), (counterexample, "counterexample")):
        _text(value, name)
    _digest(old_contract, "old contract")
    _digest(new_contract, "new contract")
    if not isinstance(changes, list) or not changes:
        raise ValueError("feedback must identify affected artifacts")
    for change in changes:
        _text(change, "change")
    return {"id": feedback_id, "observation": observation, "interpretation": interpretation,
            "counterexample": counterexample, "old_contract": old_contract,
            "new_contract": new_contract, "changes": list(changes), "status": "proposed"}


def validate_calibration(records):
    """Compare evaluator results to supplied labels; labels require independent review."""
    if not isinstance(records, list) or not records:
        raise ValueError("calibration records required")
    seen = set()
    mismatches = []
    labels = set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("invalid calibration record")
        identity = _text(row.get("id"), "calibration id")
        if identity in seen or type(row.get("expected")) is not bool:
            raise ValueError("calibration IDs must be unique with boolean labels")
        seen.add(identity)
        labels.add(row["expected"])
        if type(row.get("observed")) is not bool or row["observed"] != row["expected"]:
            mismatches.append(identity)
    matched = labels == {True, False} and not mismatches
    return {"qualified": matched, "boolean_labels_match": matched, "scope": {"kind": "boolean_examples"},
            "examples": len(records), "mismatches_or_abstentions": mismatches,
            "limitations": "Boolean labels alone do not qualify an evaluator. Supplied labels and examples are not independently verified."}


def regrade_matrix(old_spec, new_spec, old_baseline, old_candidate, new_baseline, new_candidate, evidence_root):
    """Check both revisions grade the same saved outputs and report both decisions."""
    try:
        old_expected = _validate_spec(old_spec)
        new_expected = _validate_spec(new_spec)
        if old_expected != new_expected or any(old_spec[role] != new_spec[role] for role in ("baseline", "candidate")):
            raise ValueError("regrade must use the same assignments and candidate trees")
        checked = {}
        for role, old, new in (("baseline", old_baseline, new_baseline), ("candidate", old_candidate, new_candidate)):
            before = _rows(old_spec, old, role, old_expected, evidence_root)
            after = _rows(new_spec, new, role, new_expected, evidence_root)
            checked[role] = (before, after)
            for key in old_expected:
                old_case = _digest(before[key].get("case_sha256"), "old case sha256")
                new_case = _digest(after[key].get("case_sha256"), "new case sha256")
                if old_case != new_case:
                    raise ValueError("regrade substituted the case input")
                for row in (before[key], after[key]):
                    case_receipt = row.get("case_artifact")
                    case_artifacts = _checked_artifacts({"artifacts": [case_receipt]}, evidence_root)
                    if list(case_artifacts.values()) != [row["case_sha256"]]:
                        raise ValueError("case receipt differs from the case digest")
                old_submissions = _checked_artifacts({"artifacts": before[key].get("submission_artifacts")}, evidence_root)
                new_submissions = _checked_artifacts({"artifacts": after[key].get("submission_artifacts")}, evidence_root)
                if sorted(old_submissions.values()) != sorted(new_submissions.values()):
                    raise ValueError("regrade substituted the underlying artifacts")
        for key in old_expected:
            if checked["baseline"][0][key]["case_sha256"] != checked["candidate"][0][key]["case_sha256"]:
                raise ValueError("paired submissions used different case input bytes")
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {"decision": "inconclusive", "reasons": [str(error)]}
    return {"decision": "complete", "old": compare(old_spec, old_baseline, old_candidate, evidence_root),
            "new": compare(new_spec, new_baseline, new_candidate, evidence_root),
            "limitations": "Same artifact bytes checked; evaluator execution and label quality are not independently verified."}
