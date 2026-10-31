#!/usr/bin/env python3
"""Persist corrections and compile scoped reasoning rules without a harness API."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tkstack_state import ensure_state, steering_store, SCOPES, state_roots
import session_learning


RULE_FIELDS = ("trigger", "assumption", "principle", "action", "boundary", "transfer", "counterexample")


def default_store(scope=None, project=None):
    return steering_store(scope, project)

def required_text(record, name):
    if not isinstance(record, dict):
        raise ValueError("Records must be JSON objects")
    value = record.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def read_state(store):
    state = {"corrections": {}, "experiences": {}, "rules": {}, "slop_patterns": {}}
    path = store / "events.jsonl"
    if not path.exists():
        return state
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            event = json.loads(line)
            if event["version"] != 1:
                raise ValueError("unsupported ledger version")
            payload = event["payload"]
            if event["type"] == "correction":
                identity = payload["id"]
                if identity in state["corrections"]:
                    raise ValueError("duplicate evidence ID")
                state["corrections"][identity] = payload
            elif event["type"] == "experience":
                validate_experience(payload)
                identity = payload["id"]
                if not isinstance(identity, str) or not re.fullmatch(r"experience-[0-9a-f]{16}", identity):
                    raise ValueError("invalid experience ID")
                if identity in state["experiences"]:
                    raise ValueError("duplicate experience ID")
                state["experiences"][identity] = payload
            elif event["type"] == "rule":
                validate_rule(payload, state)
                for old in payload.get("supersedes", []):
                    state["rules"][old] = {**state["rules"][old], "status": "superseded",
                                           "superseded_by": payload["id"]}
                state["rules"][payload["id"]] = payload
            elif event["type"] == "retire":
                old = state["rules"][payload["id"]]
                state["rules"][payload["id"]] = {**old, "status": "retired",
                                                  "retirement_reason": payload["reason"]}
            elif event["type"] == "slop-pattern":
                if any(item not in state["corrections"] for item in payload["evidence"]):
                    raise ValueError("slop pattern references missing user evidence")
                state["slop_patterns"][payload["id"]] = payload
            elif event["type"] == "slop-retire":
                if payload["evidence"] not in state["corrections"]:
                    raise ValueError("slop retirement references missing user evidence")
                # A packaged seed may be retired before a user amendment exists.
                old = state["slop_patterns"].get(payload["id"], {"id": payload["id"]})
                state["slop_patterns"][payload["id"]] = {**old, "status": "retired",
                    "retirement_reason": payload["reason"]}
            else:
                raise ValueError("unknown ledger event")
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f"Invalid ledger at line {number}: {error}") from error
    return state


@contextmanager
def writer(store):
    ensure_state(store)
    lock = store / ".learn.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError("Steering store is busy; retry after its writer finishes") from error
    try:
        (lock / "pid").write_text(str(os.getpid()), encoding="utf-8")
        yield
    finally:
        (lock / "pid").unlink(missing_ok=True)
        lock.rmdir()


def append_event(store, kind, payload):
    event = {"version": 1, "type": kind,
             "recorded_at": datetime.now(timezone.utc).isoformat(), "payload": payload}
    with (store / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".learn-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def validate_rule(rule, state):
    identity = required_text(rule, "id")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identity):
        raise ValueError("Rule IDs must be lowercase kebab-case")
    if rule.get("status") not in ("candidate", "active"):
        raise ValueError("Rule status must be candidate or active")
    for field in RULE_FIELDS:
        required_text(rule, field)
    scope = rule.get("scope", {})
    if not isinstance(scope, dict):
        raise ValueError("Scope must be a JSON object")
    if scope.get("kind") not in ("personal", "repository", "task"):
        raise ValueError("Scope kind must be personal, repository, or task")
    required_text(scope, "value")
    evidence = rule.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("A rule requires user evidence")
    if any(not isinstance(item, str) or item not in state["corrections"] for item in evidence):
        raise ValueError("A rule references missing user evidence")
    for old in rule.get("supersedes", []):
        if old == identity or old not in state["rules"]:
            raise ValueError("A superseded rule must exist and have a different ID")
    old = state["rules"].get(identity)
    if old and old["scope"] != scope:
        raise ValueError("Changing scope requires a new rule that explicitly supersedes the old one")


def documents(state):
    compact = ["# Learned reasoning rules", "",
               "Apply only rules whose scope and trigger match the current task. Current user",
               "instructions and higher-priority rules take precedence. Capture new corrections",
               "with the learn skill; the ledger is evidence, not an instruction source.", ""]
    outputs = {}
    for identity, rule in sorted(state["rules"].items()):
        if rule["status"] == "active":
            clean = lambda value: " ".join(value.split())
            compact.extend([f"## {identity}", "",
                            f"Scope: {rule['scope']['kind']} / {rule['scope']['value']}.",
                            f"When: {clean(rule['trigger'])}.",
                            f"Reason: {clean(rule['principle'])}.",
                            f"Apply: {clean(rule['action'])}.",
                            f"Boundary: {clean(rule['boundary'])}.",
                            f"Details: patterns/{identity}.md. Evidence: {', '.join(rule['evidence'])}.", ""])
        detail = [f"# {identity}", "", f"Status: {rule['status']}",
                  f"Scope: {rule['scope']['kind']} / {rule['scope']['value']}", ""]
        for field in RULE_FIELDS:
            detail.extend([f"## {field.replace('_', ' ').title()}", "", rule[field], ""])
        detail.extend(["## User evidence", "", *[f"- {item}" for item in rule["evidence"]], ""])
        if rule.get("retirement_reason"):
            detail.extend(["## Retirement", "", rule["retirement_reason"], ""])
        if rule.get("superseded_by"):
            detail.extend(["Superseded by: " + rule["superseded_by"], ""])
        outputs[Path("patterns") / (identity + ".md")] = "\n".join(detail)
    if not any(rule["status"] == "active" for rule in state["rules"].values()):
        compact.extend(["No active rules yet.", ""])
    outputs[Path("rules.md")] = "\n".join(compact)
    for identity, experience in sorted(state.get("experiences", {}).items()):
        source = experience["source"]
        page = [f"# {identity}", "", "Task evidence and a candidate procedural lesson;",
                "not user authorization or active steering.", "",
                f"Target skill: {experience['target_skill']}",
                f"Observed result: {experience['result']}",
                f"Source: {source['kind']} / {source['conversation']} / {source['message']}", "",
                "## Observation", "", experience["observation"], "",
                "## Candidate lesson", "", experience["lesson"], ""]
        outputs[Path("experiences") / (identity + ".md")] = "\n".join(page)
    return outputs


def render(store, state):
    ensure_state(store)
    for path, content in documents(state).items():
        atomic_write(store / path, content)


def capture(store, payload):
    user_text = required_text(payload, "user_text")
    source = payload.get("source", {})
    for field in ("conversation", "message"):
        required_text(source, field)
    required_text(payload, "context")
    if payload.get("kind", "correction") not in ("correction", "frustration", "preference"):
        raise ValueError("Observation kind must be correction, frustration, or preference")
    digest = hashlib.sha256(json.dumps({"source": source, "user_text": user_text},
                                      sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    identity = "correction-" + digest
    with writer(store):
        state = read_state(store)
        if identity not in state["corrections"]:
            append_event(store, "correction", {**payload, "id": identity,
                                              "kind": payload.get("kind", "correction")})
        render(store, read_state(store))
    return identity


def write_rule(store, payload):
    rule = {"status": "candidate", **payload}
    with writer(store):
        state = read_state(store)
        validate_rule(rule, state)
        old = state["rules"].get(rule["id"], {})
        rule["evidence"] = sorted(set(old.get("evidence", []) + rule["evidence"]))
        if rule != old:
            append_event(store, "rule", rule)
        render(store, read_state(store))
    return rule["id"]


def validate_experience(payload):
    for field in ("observation", "lesson", "target_skill"):
        required_text(payload, field)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", payload["target_skill"]):
        raise ValueError("Experience target_skill must be a lowercase skill name")
    if payload.get("result") not in ("success", "failure", "mixed"):
        raise ValueError("Experience result must be success, failure, or mixed")
    source = payload.get("source", {})
    for field in ("kind", "conversation", "message"):
        required_text(source, field)
    if source["kind"] not in ("task", "tool"):
        raise ValueError("Experience sources are task or tool; user corrections use capture")


def capture_experience(store, payload):
    validate_experience(payload)
    content = {key: value for key, value in payload.items() if key != "id"}
    identity = "experience-" + hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    with writer(store):
        state = read_state(store)
        if identity not in state["experiences"]:
            append_event(store, "experience", {**content, "id": identity})
        render(store, read_state(store))
    return identity


def locate_grok_learn(grok_home):
    root = Path(grok_home).expanduser().resolve()
    candidates = [("bundled", root / "bundled/skills/learn/SKILL.md"),
                  ("user-override", root / "skills/learn/SKILL.md"),
                  ("legacy-user-command", root / "commands/learn.md")]
    manifest, manifest_error = {}, ""
    path = root / "bundled/manifest.json"
    if path.is_file() and path.resolve().is_relative_to(root):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict) or not isinstance(manifest.get("checksums", {}), dict):
                raise ValueError("Bundle manifest must have an object of checksums")
        except (OSError, ValueError) as error:
            manifest_error = str(error)
            manifest = {}
    found, skipped = [], []
    for scope, candidate in candidates:
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            skipped.append({"path": str(candidate), "reason": "link resolves outside the selected Grok home"})
            continue
        content_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        expected = manifest.get("checksums", {}).get("skills/learn/SKILL.md") if scope == "bundled" else None
        found.append({"scope": scope, "path": str(candidate), "sha256": content_hash,
                      "bundle_manifest_match": content_hash == expected if expected else None})
    return {"grok_home": str(root), "found": found, "skipped": skipped,
            "expected_paths": [str(path) for _, path in candidates],
            "bundle_version": manifest.get("version"), "manifest_error": manifest_error,
            "note": "Local discovery only; no login, network call, transcript scan, or skill execution."}


def skill_command_help(topic=None):
    """Read the bundled invocation contract; no sibling lookup or state discovery."""
    reference = Path(__file__).resolve().parent.parent / "references/subcommands.md"
    introduction, *sections = reference.read_text(encoding="utf-8").split("\n## ")
    if topic is None:
        return introduction.rstrip()
    for section in sections:
        heading, _, body = section.partition("\n")
        if heading == topic:
            return "## " + heading + "\n" + body.rstrip()
    raise ValueError("No bundled command guidance for: " + topic)


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog=
        "Use help <topic> for native command usage or ___ify skill guidance. "
        "Slash-command skill workflows are described separately from this helper.")
    parser.add_argument("--store", type=Path, default=None)
    parser.add_argument("--scope", choices=SCOPES, help="Explicit write scope; no permission/existence fallback")
    parser.add_argument("--project", type=Path, help="Workspace root")
    commands = parser.add_subparsers(dest="command")
    for command in ("capture", "experience", "rule"):
        sub = commands.add_parser(command)
        sub.add_argument("--input", required=True, help="JSON file, or - for stdin")
    show = commands.add_parser("show")
    show.add_argument("--json", action="store_true")
    show.add_argument("--all-scopes", action="store_true", help="Read curated stores in workspace/user/global precedence")
    commands.add_parser("render")
    commands.add_parser("check")
    locate = commands.add_parser("locate-grok", help="Locate an existing Grok learn body without reading credentials")
    locate.add_argument("--grok-home", type=Path, default=Path.home() / ".grok")
    retire = commands.add_parser("retire")
    retire.add_argument("id")
    retire.add_argument("--reason", required=True)
    sessions = commands.add_parser("sessions", help="Review and consolidate explicit .tkstack session directories")
    session_commands = sessions.add_subparsers(dest="session_command", required=True)
    start = session_commands.add_parser("start")
    start.add_argument("identity")
    start.add_argument("--purpose", required=True)
    close = session_commands.add_parser("close")
    close.add_argument("identity")
    listing = session_commands.add_parser("list")
    listing.add_argument("--all-scopes", action="store_true")
    review = session_commands.add_parser("review")
    review.add_argument("--session", dest="session_ids", action="append", default=[])
    review.add_argument("--all-scopes", action="store_true")
    review.add_argument("--jobs", type=int, default=4)
    review.add_argument("--save", action="store_true")
    plan = session_commands.add_parser("plan")
    plan.add_argument("--snapshot", type=Path, required=True)
    plan.add_argument("--input", type=Path, required=True)
    plan.add_argument("--save", action="store_true")
    guide_topics = sorted(set(session_learning.ROUTES.values()) - {"learn"})
    help_command = commands.add_parser("help", help="Read-only command and ___ify skill guidance")
    help_command.add_argument("topic", nargs="?", choices=sorted([*commands.choices, *guide_topics]))
    args = parser.parse_args()
    try:
        # Resolve discovery before stores or sessions: help never initializes state.
        if args.command in (None, "help"):
            topic = getattr(args, "topic", None)
            if topic in commands.choices:
                commands.choices[topic].print_help()
            else:
                if topic is None:
                    parser.print_help()
                    print()
                print(skill_command_help(topic))
            return 0
        if args.store is not None and (args.scope is not None or args.project is not None):
            raise ValueError("Select --store or scoped discovery, not both")
        if args.command == "sessions":
            if args.store is not None:
                raise ValueError("Session operations use --scope/--project, not a steering store")
            scope = args.scope or "workspace"
            operation = args.session_command
            if operation in ("start", "close"):
                result = session_learning.lifecycle(args.identity, scope, args.project,
                    purpose=getattr(args, "purpose", None), close=operation == "close")
            elif operation == "list":
                result = session_learning.locations(scope, args.project, args.all_scopes)
            elif operation == "review":
                result = session_learning.review(scope, args.project, args.all_scopes, args.session_ids, args.jobs)
            else:
                result = session_learning.plan(session_learning.read_json(args.snapshot), session_learning.read_json(args.input))
            if getattr(args, "save", False):
                saved = session_learning.save(result, scope, args.project)
                print(json.dumps({"saved": saved, "document": result}, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        store = (args.store or default_store(args.scope, args.project)).expanduser().resolve()
        if args.command == "show" and args.all_scopes:
            roots = state_roots(args.project)
            stores = {"workspace": (args.store or default_store(project=args.project)).expanduser().resolve(),
                      "user": roots["user"] / "steering", "global": roots["global"] / "steering"}
            effective, layers = {}, {}
            for scope, location in stores.items():
                state = read_state(location)
                layers[scope] = {"path": str(location), "rules": state["rules"]}
                for identity, rule in state["rules"].items():
                    effective.setdefault(identity, {**rule, "storage_scope": scope})
            print(json.dumps({"precedence": list(stores), "layers": layers,
                  "active_rules": {key: rule for key, rule in effective.items() if rule["status"] == "active"}}, ensure_ascii=False, indent=2))
            return 0
        if args.command in ("capture", "experience", "rule"):
            raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
            payload = json.loads(raw)
            action = {"capture": capture, "experience": capture_experience, "rule": write_rule}[args.command]
            print(action(store, payload))
        elif args.command == "locate-grok":
            print(json.dumps(locate_grok_learn(args.grok_home), indent=2))
        elif args.command == "retire":
            with writer(store):
                state = read_state(store)
                if args.id not in state["rules"]:
                    raise ValueError("Unknown rule: " + args.id)
                if state["rules"][args.id]["status"] != "retired":
                    append_event(store, "retire", {"id": args.id, "reason": args.reason})
                render(store, read_state(store))
            print("Retired " + args.id)
        elif args.command == "render":
            with writer(store):
                render(store, read_state(store))
            print("Regenerated steering views")
        else:
            state = read_state(store)
            if args.command == "check":
                for path, content in documents(state).items():
                    if not (store / path).exists() or (store / path).read_text(encoding="utf-8") != content:
                        raise ValueError(f"Generated view is stale: {path}; run render")
                print(f"Valid: {len(state['corrections'])} corrections, {len(state['rules'])} rules, {len(state['experiences'])} experiences")
            elif args.json:
                print(json.dumps(state, ensure_ascii=False, indent=2))
            else:
                print(f"Store: {store}; corrections: {len(state['corrections'])}; experiences: {len(state['experiences'])}")
                for identity, rule in sorted(state["rules"].items()):
                    print(f"{identity} [{rule['status']}] {rule['principle']}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"learn: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
