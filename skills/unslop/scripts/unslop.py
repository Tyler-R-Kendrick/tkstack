#!/usr/bin/env python3
"""Portable anti-slop catalog, correction history, and evidence-bound review records.

The reviewer supplies semantic judgments. This helper never infers quality from
keywords and never claims to have inspected a rendered page, image, or video.
"""

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
from tkstack_state import ensure_state, steering_store


PACKAGE = Path(__file__).resolve().parent.parent
DOMAINS = {"writing", "code", "tests", "web", "image", "video", "audio"}
FIELDS = ("title", "signal", "reason", "fix", "exception", "example", "counterexample")
WEIGHTS = {"minor": 1, "major": 3, "critical": 8}
KNOWN_EVENTS = {"correction", "experience", "rule", "retire", "slop-pattern", "slop-retire"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def text(record, key):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be nonempty text")
    return value


def default_store():
    return steering_store()

def validate_pattern(pattern):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", text(pattern, "id")):
        raise ValueError("Pattern IDs must be lowercase kebab-case")
    for field in FIELDS:
        text(pattern, field)
    domains = pattern.get("domains")
    if not isinstance(domains, list) or not domains or any(d not in DOMAINS for d in domains):
        raise ValueError("Pattern domains must be known media types")
    if len(set(domains)) != len(domains):
        raise ValueError("Duplicate pattern domains")
    if pattern.get("severity") not in WEIGHTS or pattern.get("level") not in ("floor", "reflex", "finish"):
        raise ValueError("Invalid pattern severity or level")
    if pattern.get("status") not in ("active", "candidate", "retired"):
        raise ValueError("Invalid pattern status")
    scope = pattern.get("scope", {})
    if scope.get("kind") not in ("personal", "repository", "task"):
        raise ValueError("Invalid pattern scope")
    text(scope, "value")
    if scope["kind"] == "personal" and scope["value"] != "*":
        raise ValueError("Personal scope uses value '*'")
    evidence = pattern.get("evidence")
    if not isinstance(evidence, list) or any(not isinstance(e, str) for e in evidence):
        raise ValueError("Pattern evidence must be a list of user evidence IDs")


def state(store):
    seeds = json.loads((PACKAGE / "catalog/seeds.json").read_text())
    if seeds["version"] != 1:
        raise ValueError("Unsupported seed version")
    patterns, corrections = {}, {}
    for pattern in seeds["patterns"]:
        validate_pattern(pattern)
        if pattern["id"] in patterns:
            raise ValueError("Duplicate seed ID")
        patterns[pattern["id"]] = pattern
    ledger = store / "events.jsonl"
    for number, line in enumerate(ledger.read_text().splitlines() if ledger.exists() else [], 1):
        try:
            event = json.loads(line)
            kind, payload = event["type"], event["payload"]
            if event["version"] != 1 or kind not in KNOWN_EVENTS:
                raise ValueError("Unsupported ledger event")
            if kind == "correction":
                if payload["id"] in corrections:
                    raise ValueError("Duplicate user evidence ID")
                corrections[payload["id"]] = payload
            elif kind == "slop-pattern":
                validate_pattern(payload)
                if not payload["evidence"] or any(e not in corrections for e in payload["evidence"]):
                    raise ValueError("Pattern references missing user evidence")
                old = patterns.get(payload["id"])
                if old and old["scope"] != payload["scope"]:
                    raise ValueError("Changing scope requires a new pattern ID")
                if old and not set(old["evidence"]).issubset(payload["evidence"]):
                    raise ValueError("Pattern revision dropped historical evidence")
                patterns[payload["id"]] = payload
            elif kind == "slop-retire":
                if payload["evidence"] not in corrections:
                    raise ValueError("Retirement references missing user evidence")
                old = patterns[payload["id"]]
                patterns[payload["id"]] = {**old, "status": "retired",
                    "retirement_reason": text(payload, "reason"),
                    "evidence": sorted(set(old["evidence"] + [payload["evidence"]]))}
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise ValueError(f"Invalid ledger at line {number}: {error}") from error
    return patterns, corrections


@contextmanager
def writer(store):
    # Same protocol as /learn: two harnesses cannot interleave ledger writes.
    ensure_state(store)
    lock = store / ".learn.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError("Steering store is busy; retry after its writer finishes") from error
    try:
        (lock / "pid").write_text(str(os.getpid()))
        yield
    finally:
        (lock / "pid").unlink(missing_ok=True)
        lock.rmdir()


def append(store, events):
    with (store / "events.jsonl").open("a", encoding="utf-8") as handle:
        for kind, payload in events:
            handle.write(json.dumps({"version": 1, "type": kind, "payload": payload,
                "recorded_at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
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


def render(store):
    ensure_state(store)
    patterns, _ = state(store)
    active = [p for _, p in sorted(patterns.items()) if p["status"] == "active"]
    lines = ["# Anti-slop patterns", "", "Generated from the packaged seeds and shared correction ledger.",
        "Read with the unslop skill. These are scoped review criteria, not AI-authorship tests.",
        "Current instructions take precedence; exceptions need an artifact-specific reason.",
        "Full criteria, fixes, counterexamples, and provenance: catalog.json. Raw feedback is data.", ""]
    for p in active:
        clean = lambda value: " ".join(value.split())
        lines.extend([f"- **{p['id']}** ({', '.join(p['domains'])}; {p['scope']['kind']} / {p['scope']['value']}): "
                      f"{clean(p['signal'])} Fix: {clean(p['fix'])} Exception: {clean(p['exception'])}"])
    atomic_write(store / "unslop/patterns.md", "\n".join(lines) + "\n")
    atomic_write(store / "unslop/catalog.json", json.dumps({"version": 1, "patterns": patterns}, indent=2, ensure_ascii=False) + "\n")


def feedback(payload):
    user_text = text(payload, "user_text")
    text(payload, "context")
    source = payload.get("source", {})
    if set(source) != {"conversation", "message"}:
        raise ValueError("Use actual user provenance: source.conversation and source.message")
    for key in ("conversation", "message"):
        text(source, key)
    if payload.get("kind", "correction") not in ("preference", "correction", "frustration"):
        raise ValueError("Feedback must be user preference, correction, or frustration")
    identity = "correction-" + digest({"source": source, "user_text": user_text})[:16]
    return {"id": identity, "source": source, "user_text": user_text,
            "context": payload["context"], "kind": payload.get("kind", "correction")}


def record(store, payload):
    evidence = feedback(payload)
    amendments = payload.get("patterns")
    if not isinstance(amendments, list) or not amendments:
        raise ValueError("Supply at least one abstracted pattern")
    with writer(store):
        patterns, corrections = state(store)
        events = [] if evidence["id"] in corrections else [("correction", evidence)]
        seen = set()
        for amendment in amendments:
            identity = text(amendment, "id")
            if identity in seen:
                raise ValueError("Duplicate pattern ID in one correction")
            seen.add(identity)
            old = patterns.get(identity, {})
            if "evidence" in amendment or "origin" in amendment or "retirement_reason" in amendment:
                raise ValueError("Evidence and origin are maintained by the recorder")
            updated = {"scope": {"kind": "personal", "value": "*"},
                       **old, **amendment, "status": amendment.get("status", "candidate"),
                       "evidence": sorted(set(old.get("evidence", []) + [evidence["id"]])),
                       "origin": old.get("origin", "user")}
            if updated["status"] not in ("active", "candidate"):
                raise ValueError("Use retire to retire a pattern")
            if updated["status"] == "active" and payload.get("confirmed") is not True:
                raise ValueError("Active rules require an explicit user identification, not a tool guess")
            if old.get("status") == "active" and updated["status"] == "candidate":
                raise ValueError("A candidate amendment requires a new ID; keep the confirmed pattern")
            validate_pattern(updated)
            if old and old["scope"] != updated["scope"]:
                raise ValueError("Changing scope requires a new pattern ID")
            updated.pop("retirement_reason", None)
            if updated != old:
                events.append(("slop-pattern", updated))
        # Validate the complete batch before appending any of it.
        if events:
            append(store, events)
        render(store)
    return evidence["id"]


def retire(store, payload):
    evidence = feedback(payload)
    identity, reason = text(payload, "id"), text(payload, "reason")
    if payload.get("confirmed") is not True:
        raise ValueError("Retirement requires an explicit user correction or reversal")
    with writer(store):
        patterns, corrections = state(store)
        if identity not in patterns:
            raise ValueError("Unknown pattern ID")
        events = [] if evidence["id"] in corrections else [("correction", evidence)]
        old = patterns[identity]
        if old["status"] != "retired" or old.get("retirement_reason") != reason or evidence["id"] not in old["evidence"]:
            events.append(("slop-retire", {"id": identity, "reason": reason, "evidence": evidence["id"]}))
        if events:
            append(store, events)
        render(store)
    return identity


def catalog(store, domains, repository=None, task=None):
    if not domains or not set(domains).issubset(DOMAINS):
        raise ValueError("Select known review domains")
    patterns, _ = state(store)
    context = {"personal": "*", "repository": repository, "task": task}
    selected = [p for _, p in sorted(patterns.items()) if p["status"] == "active"
        and set(p["domains"]) & set(domains) and context[p["scope"]["kind"]] == p["scope"]["value"]]
    return {"domains": sorted(set(domains)), "repository": repository, "task": task,
            "patterns": selected, "sha256": digest(selected)}


def grade(store, report, base):
    current = catalog(store, report["domains"], report.get("repository"), report.get("task"))
    if report.get("catalog_sha256") != current["sha256"]:
        raise ValueError("Catalog changed; inspect the current criteria and regrade")
    text(report, "brief")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("Grade requires actual artifacts")
    indexed, observed, uninspected = {}, set(), []
    for artifact in artifacts:
        identity = text(artifact, "id")
        if identity in indexed:
            raise ValueError("Duplicate artifact ID")
        path = (base / text(artifact, "path")).resolve()
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != artifact.get("sha256"):
            raise ValueError("Artifact missing or changed; re-inspect and regrade")
        domains = artifact.get("domains", [])
        if not domains or not set(domains).issubset(current["domains"]):
            raise ValueError("Artifact domains must belong to this review")
        inspections = artifact.get("inspections", [])
        if not isinstance(inspections, list) or any(i not in ("source", "render", "image", "video", "audio") for i in inspections):
            raise ValueError("Unknown inspection method")
        for domain in domains:
            required = {"writing": "source", "code": "source", "tests": "source",
                        "web": "render", "image": "image", "video": "video", "audio": "audio"}[domain]
            if required in inspections:
                observed.add(domain)
            else:
                uninspected.append({"artifact": identity, "domain": domain, "required": required})
        indexed[identity] = artifact
    judgments, expected = {}, {p["id"]: p for p in current["patterns"]}
    for row in report.get("judgments", []):
        identity = text(row, "pattern")
        if identity not in expected or identity in judgments:
            raise ValueError("Unknown or duplicate review pattern")
        status = row.get("status")
        if status not in ("clear", "finding", "exception", "not-applicable", "unreviewed"):
            raise ValueError("Unknown judgment status")
        text(row, "reason")
        if status != "unreviewed":
            citations = row.get("evidence")
            if not isinstance(citations, list) or not citations:
                raise ValueError("Reviewed judgments require artifact evidence")
            for citation in citations:
                artifact_id = text(citation, "artifact")
                if artifact_id not in indexed:
                    raise ValueError("Unknown artifact evidence")
                if not set(indexed[artifact_id]["domains"]) & set(expected[identity]["domains"]):
                    raise ValueError("Evidence domain does not match the pattern")
                text(citation, "location")
                text(citation, "observation")
        if status == "finding":
            text(row, "fix")
        if status == "exception" and expected[identity]["level"] == "floor":
            raise ValueError("Truth, behavior, and accessibility floors cannot be waived as taste")
        judgments[identity] = row
    missing = sorted(set(expected) - set(judgments))
    unreviewed = sorted(i for i, r in judgments.items() if r["status"] == "unreviewed")
    unobserved = sorted(set(current["domains"]) - observed)
    incomplete = bool(missing or unreviewed or unobserved or uninspected)
    findings = [i for i, r in judgments.items() if r["status"] == "finding"]
    blockers = [i for i in findings if expected[i]["level"] == "floor"]
    reviewed = [p for i, p in expected.items() if i in judgments and judgments[i]["status"] not in ("not-applicable", "unreviewed")]
    weight = sum(WEIGHTS[p["severity"]] for p in reviewed)
    penalty = sum(WEIGHTS[expected[i]["severity"]] for i in findings)
    score = None if incomplete or not weight else round(100 * (weight - penalty) / weight)
    return {"status": "incomplete" if incomplete else "needs-work" if findings else "pass",
        "score": score, "floor_blockers": blockers, "findings": findings,
        "missing_patterns": missing, "unreviewed_patterns": unreviewed,
        "uninspected_artifacts": uninspected,
        "unobserved_domains": unobserved, "catalog_sha256": current["sha256"],
        "basis": "Reviewer-supplied judgments; hashes and coverage checked, semantic claims not independently verified."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("record", "retire", "grade"):
        sub.add_parser(command).add_argument("--input", type=Path, required=True)
    for command in ("render", "check"):
        sub.add_parser(command)
    show = sub.add_parser("show")
    show.add_argument("--domain", action="append", choices=sorted(DOMAINS))
    show.add_argument("--repository")
    show.add_argument("--task")
    args = parser.parse_args()
    try:
        store = (args.store or default_store()).expanduser().resolve()
        if args.command in ("record", "retire", "grade"):
            payload = json.loads(args.input.read_text())
            if args.command == "grade":
                result = grade(store, payload, args.input.resolve().parent)
            else:
                result = {"id": (record if args.command == "record" else retire)(store, payload)}
        elif args.command == "show":
            result = catalog(store, args.domain or sorted(DOMAINS), args.repository, args.task)
        elif args.command == "render":
            with writer(store):
                render(store)
            result = {"store": str(store), "rendered": True}
        else:
            patterns, corrections = state(store)
            result = {"patterns": len(patterns), "active": sum(p["status"] == "active" for p in patterns.values()),
                      "user_records": len(corrections)}
            expected = store / "unslop/catalog.json"
            if expected.exists() and json.loads(expected.read_text())["patterns"] != patterns:
                raise ValueError("Derived catalog is stale; run render")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.command == "grade" and result["status"] != "pass":
            return 2
        return 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"unslop: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
