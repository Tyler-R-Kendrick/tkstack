#!/usr/bin/env python3
"""Compare paired experiment receipts; never run, edit, or adopt a candidate."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
sys.dont_write_bytecode = True


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Measurements must be finite numbers")
    return value


def hashed(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_receipt(record, base):
    path = (base / record["path"]).resolve()
    if not path.is_file() or hashed(path) != record.get("sha256"):
        raise ValueError(f"Missing or changed evidence: {path}")
    return path


def validate_plan(plan, base):
    if plan["version"] != 1 or plan["direction"] not in ("higher", "lower"):
        raise ValueError("Invalid plan version or direction")
    if number(plan["min_gain"]) <= number(plan["noise_floor"]) or plan["noise_floor"] < 0:
        raise ValueError("Actionable gain must exceed the nonnegative baseline noise floor")
    if not isinstance(plan.get("noise_evidence"), str) or not plan["noise_evidence"].strip():
        raise ValueError("Baseline noise requires an evidence description")
    if type(plan["reps"]) is not int or plan["reps"] < 1:
        raise ValueError("Reps must be a positive integer")
    splits = plan["splits"]
    seen = set()
    for name in ("train", "selection", "confirm"):
        ids = splits[name]
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or not i for i in ids):
            raise ValueError("Each split requires nonempty case IDs")
        if len(set(ids)) != len(ids) or seen & set(ids):
            raise ValueError("Case splits must be unique and disjoint")
        seen.update(ids)
    frozen = plan["frozen_files"]
    if not isinstance(frozen, list) or not frozen:
        raise ValueError("List the frozen runner, grader, data, and dependencies")
    for receipt in frozen:
        file_receipt(receipt, base)
    guard_names = set()
    for guard in plan["guardrails"]:
        if guard["direction"] not in ("higher", "lower") or number(guard["tolerance"]) < 0:
            raise ValueError("Invalid guardrail")
        if guard["metric"] == plan["metric"] or guard["metric"] in guard_names:
            raise ValueError("Guardrails must name distinct non-target metrics")
        guard_names.add(guard["metric"])


def read_results(path, plan, split):
    expected = {(identity, rep) for identity in plan["splits"][split] for rep in range(plan["reps"])}
    allowed = {(identity, rep) for ids in plan["splits"].values() for identity in ids for rep in range(plan["reps"])}
    rows = {}
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if type(row["rep"]) is not int:
            raise ValueError("Rep must be an integer")
        key = (row["case"], row["rep"])
        if key not in allowed or key in rows:
            raise ValueError("Unknown or duplicate case/rep result")
        for metric in [plan["metric"], *[g["metric"] for g in plan["guardrails"]]]:
            number(row["metrics"][metric])
        if type(row["gate_passed"]) is not bool:
            raise ValueError("Every result requires a boolean regression gate")
        if number(row["error_count"]) < 0 or number(row["work_count"]) <= 0:
            raise ValueError("Results require positive work and nonnegative errors")
        file_receipt(row["evidence"], path.resolve().parent)
        if plan.get("model_based"):
            if not isinstance(row.get("model"), str) or not row["model"].strip():
                raise ValueError("Model-based results require the actual served model")
            for metric in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"):
                if number(row["usage"][metric]) < 0:
                    raise ValueError("Token usage cannot be negative")
            if not isinstance(row.get("grade"), dict) or not row["grade"]:
                raise ValueError("Model-based results require the same-call grade dict")
        rows[key] = row
    if expected - set(rows):
        raise ValueError("Incomplete result coverage for selected split")
    return {key: rows[key] for key in expected}


def paired_metric(baseline, candidate, metric, direction):
    sign = 1 if direction == "higher" else -1
    ids = sorted({identity for identity, _ in baseline})
    deltas = [statistics.mean(sign * (candidate[key]["metrics"][metric] - baseline[key]["metrics"][metric])
                for key in baseline if key[0] == identity) for identity in ids]
    half_width = None
    if len(deltas) > 1:
        # Case means are the independent units; repeated draws of one case are not extra cases.
        critical = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262,
                    2.228, 2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101,
                    2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052,
                    2.048, 2.045, 2.042]
        df = len(deltas) - 1
        t = critical[df - 1] if df <= 30 else 1.96
        half_width = t * statistics.stdev(deltas) / math.sqrt(len(deltas))
    before = statistics.mean(row["metrics"][metric] for row in baseline.values())
    after = statistics.mean(row["metrics"][metric] for row in candidate.values())
    return {"before": before, "after": after, "gain": statistics.mean(deltas),
            "paired_95_half_width": half_width, "independent_cases": len(ids)}


def compare(plan_path, baseline_path, candidate_path, split):
    plan = json.loads(plan_path.read_text())
    validate_plan(plan, plan_path.resolve().parent)
    if split not in ("selection", "confirm"):
        raise ValueError("Only selection or confirm can support a decision")
    baseline = read_results(baseline_path, plan, split)
    candidate = read_results(candidate_path, plan, split)
    if any(not r["gate_passed"] or r["error_count"] for r in baseline.values()):
        raise ValueError("Baseline must have a green gate and no harness errors")
    target = paired_metric(baseline, candidate, plan["metric"], plan["direction"])
    uncertainty = max(plan["noise_floor"], target["paired_95_half_width"] or 0)
    reasons = []
    if target["gain"] <= max(plan["min_gain"], uncertainty):
        reasons.append("Target improvement does not exceed actionable gain and noise")
    if any(not r["gate_passed"] or r["error_count"] for r in candidate.values()):
        reasons.append("Candidate regression gate or harness errors")
    if any(candidate[key]["work_count"] != baseline[key]["work_count"] for key in baseline):
        reasons.append("Candidate changed the amount of measured work")
    guards = {}
    for guard in plan["guardrails"]:
        measured = paired_metric(baseline, candidate, guard["metric"], guard["direction"])
        guards[guard["metric"]] = measured
        lower = measured["gain"] - (measured["paired_95_half_width"] or 0)
        if lower < -guard["tolerance"]:
            reasons.append(f"Guardrail not established: {guard['metric']}")
    return {"decision": "reject" if reasons else "eligible", "split": split,
            "claim": "selection evidence" if split == "selection" else "confirmation evidence; holdout isolation must be independently checked",
            "target": target, "guardrails": guards, "reasons": reasons,
            "receipts": {"plan": hashed(plan_path), "baseline": hashed(baseline_path), "candidate": hashed(candidate_path)},
            "limits": "Supplied receipts and numeric gates only; no verification of semantic correctness, actual execution, independent cases, or untouched holdout. Single-case results have no case-level interval."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--split", choices=("selection", "confirm"), default="selection")
    args = parser.parse_args()
    try:
        result = compare(args.plan, args.baseline, args.candidate, args.split)
        print(json.dumps(result, indent=2))
        return 0 if result["decision"] == "eligible" else 2
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"hill-climb: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
