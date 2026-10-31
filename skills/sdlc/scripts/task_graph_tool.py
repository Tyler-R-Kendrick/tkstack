#!/usr/bin/env python3
"""JSON entrypoint for the compiled, inference-free SDLC coordinator."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.dont_write_bytecode = True

from task_store import OPERATIONS, database_path, execute
from tkstack_state import state_root


def dispatch(payload):
    if not isinstance(payload, dict):
        raise ValueError("Input must be a JSON object")
    operation = payload.get("operation")
    if operation == "help" and set(payload) == {"operation"}:
        return {"operations": list(OPERATIONS), "state": ".tkstack/sdlc/task-graph.sqlite3",
                "engine": "sqlite-wal", "inference": "none"}
    if operation not in OPERATIONS:
        raise ValueError("Unknown task operation")
    allowed = {"operation", "scope", "database", "repo", "run", "actor", "graph", "task", "token", "ttl",
               "outcome", "head", "proof", "reason", "evidence", "issue", "revision"}
    if set(payload) - allowed:
        raise ValueError("Unknown task parameters")
    # Codify executes in a private materialization directory. Resolve external
    # paths against the caller's selected workspace, never that scratch cwd.
    workspace = state_root().parent
    def path(value):
        return str((workspace / Path(value).expanduser()).absolute()) if value is not None else None
    scope = payload.get("scope", "workspace")
    database = database_path(path(payload.get("database")), scope)
    arguments = {key: value for key, value in payload.items()
                 if key not in ("operation", "scope", "database", "repo", "run", "actor") and value is not None}
    for key in ("graph", "proof"):
        if key in arguments:
            arguments[key] = path(arguments[key])
    if "evidence" in arguments:
        arguments["evidence"] = [path(item) for item in arguments["evidence"]]
    if "issue" in arguments:
        arguments["issue"] = {**arguments["issue"], "evidence": [path(item) for item in arguments["issue"]["evidence"]]}
    if "revision" in arguments:
        revision = arguments["revision"]
        arguments["revision"] = {**revision, "graph": path(revision["graph"]),
                                 "adrs": [{**adr, "path": path(adr["path"])} for adr in revision["adrs"]]}
    return execute(database, payload.get("run"), operation, payload.get("actor"),
                   path(payload.get("repo")) or workspace, **arguments)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON file or - for stdin")
    args = parser.parse_args()
    try:
        with (sys.stdin if args.input == "-" else Path(args.input).open(encoding="utf-8")) as source:
            raw = source.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Input exceeds 1 MiB")
        result = dispatch(json.loads(raw))
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as error:
        print(f"sdlc tasks: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
