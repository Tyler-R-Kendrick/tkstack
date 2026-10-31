#!/usr/bin/env python3
"""Pure JSON rule evaluation, replay, and a Claude command-hook adapter."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import re
import shlex
import sys
sys.dont_write_bytecode = True


EVENTS = {"before-tool": "PreToolUse", "before-stop": "Stop"}
OPERATORS = {"equals", "one_of", "contains", "starts_with", "ends_with", "exists"}
LIMIT = 1024 * 1024


def reject_constant(value):
    raise ValueError(f"Non-finite JSON constant is not supported: {value}")


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def read_json(path):
    with path.open("rb") as handle:
        raw = handle.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError("JSON exceeds the 1 MiB input limit")
    return json.loads(raw, parse_constant=reject_constant, object_pairs_hook=unique_fields)


def validate(policy):
    if not isinstance(policy, dict) or set(policy) != {"version", "failure_mode", "rules"} or type(policy["version"]) is not int or policy["version"] != 1:
        raise ValueError("Policy requires version 1, failure_mode, and rules")
    if policy["failure_mode"] not in ("block", "warn"):
        raise ValueError("failure_mode must explicitly be block or warn")
    if not isinstance(policy["rules"], list) or len(policy["rules"]) > 128:
        raise ValueError("Use at most 128 rules")
    ids = set()
    for rule in policy["rules"]:
        if set(rule) != {"id", "event", "enabled", "action", "conditions", "message"}:
            raise ValueError("Rule has missing or unknown fields")
        identity = rule["id"]
        if not isinstance(identity, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identity) or identity in ids:
            raise ValueError("Rule IDs must be unique kebab-case strings")
        ids.add(identity)
        if rule["event"] not in EVENTS or rule["action"] not in ("warn", "block") or type(rule["enabled"]) is not bool:
            raise ValueError("Invalid rule event, action, or enabled flag")
        if not isinstance(rule["message"], str) or not rule["message"].strip():
            raise ValueError("Rule message must explain the matched condition")
        conditions = rule["conditions"]
        if not isinstance(conditions, list) or not 1 <= len(conditions) <= 16:
            raise ValueError("Each rule requires 1 to 16 AND conditions")
        for condition in conditions:
            if set(condition) != {"field", "operator", "value"}:
                raise ValueError("Condition requires field, operator, and value")
            if not isinstance(condition["field"], str) or not re.fullmatch(r"[a-zA-Z_][\w]*(?:\.[a-zA-Z_][\w]*)*", condition["field"]):
                raise ValueError("Use dot-separated JSON object field names")
            operator, value = condition["operator"], condition["value"]
            if operator not in OPERATORS:
                raise ValueError("Unsupported operator; predicates never execute code or arbitrary regex")
            if operator == "exists" and type(value) is not bool:
                raise ValueError("exists requires a boolean")
            if operator in ("contains", "starts_with", "ends_with") and (not isinstance(value, str) or not value):
                raise ValueError("String predicates require a nonempty literal")
            if operator == "one_of" and (not isinstance(value, list) or not value):
                raise ValueError("one_of requires nonempty literal alternatives")
            literals = value if operator == "one_of" else [value]
            if operator in ("equals", "one_of") and any(type(v) not in (str, int, float, bool, type(None)) for v in literals):
                raise ValueError("Equality predicates require JSON scalar literals")
            if any(type(v) is float and not math.isfinite(v) for v in literals):
                raise ValueError("Equality predicates require finite scalar literals")
    return policy


def matches(condition, fields):
    value = fields
    present = True
    for key in condition["field"].split("."):
        if not isinstance(value, dict) or key not in value:
            present = False
            break
        value = value[key]
    expected, operator = condition["value"], condition["operator"]
    if operator == "exists":
        return present == expected
    if not present:
        return False
    equal = lambda other: type(value) is type(other) and value == other
    if operator == "equals":
        return equal(expected)
    if operator == "one_of":
        return any(equal(other) for other in expected)
    if not isinstance(value, str):
        return False
    if operator == "contains":
        return expected in value
    return value.startswith(expected) if operator == "starts_with" else value.endswith(expected)


def evaluate(policy, event):
    validate(policy)
    if set(event) != {"event", "fields"} or event["event"] not in EVENTS or not isinstance(event["fields"], dict):
        raise ValueError("Portable event requires a supported event and fields object")
    if event["event"] == "before-stop" and event["fields"].get("stop_hook_active") is True:
        return {"decision": "allow", "matches": [], "messages": [], "reason_codes": ["stop-reentry"]}
    selected = [rule for rule in sorted(policy["rules"], key=lambda r: r["id"])
        if rule["enabled"] and rule["event"] == event["event"]
        and all(matches(condition, event["fields"]) for condition in rule["conditions"])]
    decision = "block" if any(rule["action"] == "block" for rule in selected) else "warn" if selected else "allow"
    return {"decision": decision, "matches": [r["id"] for r in selected],
            "messages": [r["message"] for r in selected], "reason_codes": []}


def claude_event(payload):
    event = {value: key for key, value in EVENTS.items()}.get(payload.get("hook_event_name"))
    if event is None:
        raise ValueError("Claude adapter supports only PreToolUse and Stop")
    if event == "before-tool":
        if not isinstance(payload.get("tool_name"), str) or not isinstance(payload.get("tool_input"), dict):
            raise ValueError("PreToolUse requires tool_name and tool_input")
    elif type(payload.get("stop_hook_active")) is not bool:
        raise ValueError("Stop requires the boolean stop_hook_active guard")
    return {"event": event, "fields": payload}


def claude_output(result, event):
    if result["decision"] == "allow":
        return {}
    message = "\n".join(f"[{identity}] {message}" for identity, message in zip(result["matches"], result["messages"]))
    output = {"systemMessage": message}
    if result["decision"] == "block":
        if event == "before-tool":
            output["hookSpecificOutput"] = {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                            "permissionDecisionReason": message}
        else:
            output.update(decision="block", reason=message)
    return output


def fragment(policy, rules_path):
    validate(policy)
    command = shlex.join([sys.executable, str(Path(__file__).resolve()), "run", "--rules", str(rules_path.resolve()), "--adapter", "claude"])
    return {"hooks": {EVENTS[event]: [{"hooks": [{"type": "command", "command": command, "timeout": 5}]}]
            for event in sorted({r["event"] for r in policy["rules"] if r["enabled"]})}}


def replay(policy, cases, jobs):
    validate(policy)
    if type(jobs) is not int or not 1 <= jobs <= 32:
        raise ValueError("Replay jobs must be between 1 and 32")
    if not isinstance(cases, list) or not cases or len(cases) > 128:
        raise ValueError("Replay requires 1 to 128 cases")
    ids = [case["id"] for case in cases]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Replay case IDs must be unique nonempty strings")
    def run(case):
        expected = case["expected"]
        if set(expected) != {"decision", "matches"} or expected["decision"] not in ("allow", "warn", "block") or not isinstance(expected["matches"], list):
            raise ValueError("Expected result requires explicit decision and matched IDs")
        result = evaluate(policy, case["input"])
        actual = {key: result[key] for key in ("decision", "matches")}
        return {"id": case["id"], "passed": actual == expected, "actual": actual, "expected": expected}
    # map preserves input order; workers only read shared policy and their own case.
    with ThreadPoolExecutor(max_workers=min(jobs, len(cases))) as pool:
        results = list(pool.map(run, sorted(cases, key=lambda case: case["id"])))
    return {"passed": all(r["passed"] for r in results), "cases": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "emit", "run", "replay"):
        child = sub.add_parser(command)
        child.add_argument("--rules", type=Path, required=True)
        if command == "run":
            child.add_argument("--adapter", choices=("portable", "claude"), default="portable")
        if command == "replay":
            child.add_argument("--cases", type=Path, required=True)
            child.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    policy = None
    try:
        policy = validate(read_json(args.rules))
        if args.command == "check":
            result = {"valid": True, "rules": len(policy["rules"])}
        elif args.command == "emit":
            result = fragment(policy, args.rules)
        elif args.command == "replay":
            result = replay(policy, read_json(args.cases), args.jobs)
        else:
            raw = sys.stdin.buffer.read(LIMIT + 1)
            if len(raw) > LIMIT:
                raise ValueError("Event exceeds the 1 MiB input limit")
            payload = json.loads(raw, parse_constant=reject_constant, object_pairs_hook=unique_fields)
            event = claude_event(payload) if args.adapter == "claude" else payload
            result = evaluate(policy, event)
            if args.adapter == "claude":
                result = claude_output(result, event["event"])
        print(json.dumps(result, indent=2))
        return 2 if args.command == "replay" and not result["passed"] else 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        message = f"hookify: {error}"
        if args.command == "run" and args.adapter == "claude":
            if policy is not None and policy["failure_mode"] == "warn":
                print(json.dumps({"systemMessage": message}))
                return 0
            print(message, file=sys.stderr)
            return 2
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
