"""Local durable SDLC coordination. SQLite owns state; Git owns code and refs."""

import copy
import json
from pathlib import Path
import secrets
import sqlite3
import time

import sdlc
from tkstack_state import ensure_state, state_container, state_root


SCHEMA = 1
OPERATIONS = ("init", "status", "claim", "heartbeat", "finish", "quiesce", "recover",
              "issue", "revise", "history", "gate")


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def database_path(path=None, scope="workspace", project=None):
    path = Path(path).expanduser().absolute() if path else state_root(scope, project) / "sdlc/task-graph.sqlite3"
    if ".." in path.parts:
        raise ValueError("Task database paths must not contain parent traversal")
    container = state_container(path)
    if not path.is_relative_to(container / "sdlc") or "sessions" in path.relative_to(container).parts:
        raise ValueError("Durable task databases belong in .tkstack/sdlc/, outside sessions")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("Task database paths must not contain symlinks")
    return path


def connect(path, create=False, readonly=False):
    path = database_path(path)
    if create:
        ensure_state(path.parent)
    if not create and not path.is_file():
        raise ValueError("Task database does not exist; run tasks init first")
    connection = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw" if not create else "?mode=rwc"),
                                 uri=True, timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=ON")
    if not readonly:
        connection.execute("PRAGMA synchronous=FULL")
    if create:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (version INTEGER NOT NULL);
            INSERT INTO metadata SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM metadata);
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, repo TEXT NOT NULL, coordinator TEXT NOT NULL,
                version INTEGER NOT NULL, revision INTEGER NOT NULL, graph TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks (
                run TEXT NOT NULL REFERENCES runs(id), id TEXT NOT NULL, record TEXT NOT NULL,
                PRIMARY KEY(run,id));
            CREATE TABLE IF NOT EXISTS revisions (
                run TEXT NOT NULL REFERENCES runs(id), number INTEGER NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(run,number));
            CREATE TABLE IF NOT EXISTS issues (
                run TEXT NOT NULL REFERENCES runs(id), id TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(run,id));
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY, run TEXT NOT NULL REFERENCES runs(id),
                at REAL NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS run_events ON events(run,sequence);
        """)
    if [row[0] for row in connection.execute("SELECT version FROM metadata")] != [SCHEMA]:
        connection.close()
        raise ValueError("Unsupported task database schema")
    return connection


def repo_identity(repo):
    return str(Path(sdlc.git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve())


def registered_graph(path):
    path = Path(path).absolute()
    graph = sdlc.load_graph(path)
    graph["workload"]["path"] = str((path.parent / graph["workload"]["path"]).resolve())
    if set(graph["requirements"]) != {r for t in graph["tasks"] for r in t["requirements"]}:
        raise ValueError("Every graph requirement needs an assigned task")
    workload = Path(graph["workload"]["path"]).read_text()
    if sdlc.digest(workload.encode()) != graph["workload"]["sha256"]:
        raise ValueError("Workload must be unchanged UTF-8 text")
    return graph, workload


def snapshot(connection, run, repo):
    connection.execute("BEGIN")
    try:
        row = connection.execute("SELECT * FROM runs WHERE id=?", (run,)).fetchone()
        if row is None:
            raise ValueError("Unknown task run")
        if row["repo"] != repo:
            raise ValueError("Task run belongs to another repository")
        value = dict(row)
        value["graph"] = json.loads(row["graph"])
        value["tasks"] = {r["id"]: json.loads(r["record"]) for r in connection.execute("SELECT id,record FROM tasks WHERE run=?", (run,))}
        value["issues"] = {r["id"]: json.loads(r["payload"]) for r in connection.execute("SELECT id,payload FROM issues WHERE run=?", (run,))}
        return value
    finally:
        connection.execute("ROLLBACK")


def closure(nodes, seeds):
    result = set(seeds)
    children = {key: [] for key in nodes}
    for key, node in nodes.items():
        for parent in node["depends_on"]:
            children[parent].append(key)
    queue = list(seeds)
    while queue:
        for key in children.get(queue.pop(), ()):
            if key not in result:
                result.add(key)
                queue.append(key)
    return result


def paused(snapshot):
    nodes = {node["id"]: node for node in snapshot["graph"]["tasks"]}
    return closure(nodes, {task for issue in snapshot["issues"].values() if issue["status"] == "open" for task in issue["affected"]})


def coordinator(value, actor):
    if actor != value["coordinator"]:
        raise ValueError("Only the run coordinator may revise or recover task state")


def lease(record, actor, token):
    if (not record or record.get("owner") != actor or not token
            or record.get("token") != token or record.get("status") != "running"
            or record.get("expires_at", 0) <= time.time()):
        raise ValueError("A current unexpired owner/token lease is required")


def evidence(paths):
    sdlc.string_list(paths, "evidence paths")
    result = []
    for path in paths:
        path = Path(path).resolve(strict=True)
        if not path.is_file():
            raise ValueError("Evidence must be a retained file")
        result.append({"path": str(path), "sha256": sdlc.file_digest(path)})
    return result


def revise(value, request, actor):
    coordinator(value, actor)
    if request.get("expected_revision") != value["revision"]:
        raise ValueError("Revision changed; inspect the current graph before revising")
    for key in ("rationale", "authorization"):
        sdlc.text(request.get(key), key)
    graph, workload = registered_graph(request["graph"])
    old = value["graph"]
    entries = sdlc.records(request.get("requirements"), "requirement dispositions")
    dispositions = {}
    for entry in entries:
        identity = sdlc.text(entry.get("id"), "requirement ID")
        if identity in dispositions:
            raise ValueError("Duplicate requirement disposition")
        dispositions[identity] = entry
    if set(dispositions) != set(old["requirements"]):
        raise ValueError("Account for every previous requirement, including withdrawn ones")
    changed_requirements = set(graph["requirements"]) - set(old["requirements"])
    for identity, disposition in dispositions.items():
        sdlc.record(disposition, "requirement disposition")
        sdlc.text(disposition.get("reason"), "requirement disposition reason")
        status = disposition.get("status")
        if status not in ("unchanged", "changed", "withdrawn") or ((identity in graph["requirements"]) == (status == "withdrawn")):
            raise ValueError("Requirement disposition disagrees with the revised workload")
        if status != "unchanged":
            changed_requirements.add(identity)
    resolving = sdlc.string_list(request.get("resolves"), "resolved issue IDs", allow_empty=True)
    if any(key not in value["issues"] or value["issues"][key]["status"] != "open" for key in resolving):
        raise ValueError("Resolve only existing open issues")
    adrs = request.get("adrs", [])
    if any(value["issues"][key]["kind"] == "architecture" for key in resolving) and not adrs:
        raise ValueError("Architecture issue resolution requires a retained ADR decision")
    adr_records = []
    for adr in adrs:
        sdlc.record(adr, "ADR")
        sdlc.text(adr.get("decision"), "ADR decision")
        item = evidence([adr["path"]])[0]
        item.update(decision=adr["decision"], content=Path(item["path"]).read_text())
        adr_records.append(item)
    old_nodes = {n["id"]: n for n in old["tasks"]}
    nodes = {n["id"]: n for n in graph["tasks"]}
    changed = {key for key in old_nodes.keys() | nodes.keys() if old_nodes.get(key) != nodes.get(key)}
    changed |= {key for key, node in {**old_nodes, **nodes}.items() if set(node["requirements"]) & changed_requirements}
    changed |= {task for key in resolving for task in value["issues"][key]["affected"]}
    changed = closure(old_nodes, changed) | closure(nodes, changed)
    for key in changed:
        if value["tasks"].get(key, {}).get("status") == "running":
            raise ValueError("Affected workers must quiesce before revision: " + key)
    for key, issue in value["issues"].items():
        if key not in resolving and issue["status"] == "open" and not set(issue["affected"]) <= set(nodes):
            raise ValueError("Cannot remove tasks from an unresolved issue")
    invalidated = {key: value["tasks"].pop(key) for key in sorted(changed) if key in value["tasks"]}
    for key in resolving:
        value["issues"][key].update(status="resolved", resolved_revision=value["revision"] + 1)
    value["revision"] += 1
    value["graph"] = graph
    return {"revision": value["revision"], "graph": graph, "workload": workload,
            "rationale": request["rationale"], "authorization": request["authorization"],
            "requirements": dispositions, "adrs": adr_records, "resolved": resolving,
            "invalidated": invalidated, "carried": sorted(value["tasks"])}


def transition(value, operation, actor, arguments, repo):
    graph = value["graph"]
    nodes = {node["id"]: node for node in graph["tasks"]}
    task = arguments.get("task")
    task_record = value["tasks"].get(task)
    blocked = paused(value)
    revision = None
    ttl = arguments.get("ttl", 900)
    if type(ttl) is not int or not 10 <= ttl <= 86400:
        raise ValueError("Lease ttl must be 10..86400 seconds")
    if operation in ("claim", "finish", "gate"):
        heads = dict(line.split(" ", 1) for line in sdlc.git(repo, "for-each-ref", "--format=%(refname:strip=2) %(objectname)", "refs/heads/").splitlines())
        state = {"workload_sha256": graph["workload"]["sha256"], "tasks": value["tasks"]}
        if operation == "gate":
            checked = sdlc.scheduler_transition(graph, state, actor, repo=repo, nodes=nodes, branch_heads=heads, inspect=True)
            if blocked or set(checked["done"]) != set(nodes):
                raise ValueError("Task gate blocked by open issues, incomplete tasks, or stale proof")
            return {"task_gate": "pass", "revision": value["revision"], "tasks": len(nodes),
                    "note": "Also run the original-workload evidence gate and independent review; this does not authenticate PR state"}, None
        if operation == "finish":
            lease(task_record, actor, arguments.get("token"))
            if task in blocked:
                raise ValueError("Task is paused by an outer-loop issue; quiesce before revision")
            outcome = arguments.get("outcome")
            if outcome not in ("done", "blocked", "retry"):
                raise ValueError("Invalid completion outcome")
            result = sdlc.scheduler_transition(graph, state, actor, task, outcome,
                arguments.get("head"), arguments.get("proof"), repo, nodes, heads)
            # Evidence I/O can be long: expiry is checked again at publication below.
            result["released_lease"] = copy.deepcopy(task_record)
            return result, None
        result = sdlc.scheduler_transition(graph, state, actor, task, repo=repo, nodes=nodes,
                                           branch_heads=heads, excluded=blocked)
        if result["task"]:
            record = value["tasks"][result["task"]]
            record.update(token=secrets.token_hex(24), expires_at=time.time() + ttl,
                          revision=value["revision"])
            result.update(token=record["token"], expires_at=record["expires_at"],
                          revision=value["revision"], workload_sha256=record["workload_sha256"])
        else:
            result["paused"] = sorted(blocked)
        return result, None
    if operation in ("heartbeat", "quiesce"):
        lease(task_record, actor, arguments.get("token"))
        if operation == "heartbeat":
            if task in blocked:
                raise ValueError("Task is paused; stop writes and quiesce")
            task_record["expires_at"] = time.time() + ttl
        else:
            sdlc.text(arguments.get("reason"), "quiescence reason")
            task_record["status"] = "blocked"
            task_record["quiescence"] = arguments["reason"]
        return {"task": task, "status": task_record["status"], "expires_at": task_record["expires_at"]}, None
    if operation == "recover":
        coordinator(value, actor)
        sdlc.text(arguments.get("reason"), "recovery reason")
        recovery_evidence = evidence(arguments.get("evidence"))
        if not task_record:
            raise ValueError("No task record to recover")
        if task_record["status"] == "running" and task_record["expires_at"] > time.time():
            raise ValueError("Live owners must quiesce; recovery requires an expired lease")
        if any(value["tasks"].get(key, {}).get("status") == "running" for key in closure(nodes, {task}) - {task}):
            raise ValueError("Dependent workers must quiesce before recovering their input")
        previous = value["tasks"].pop(task)
        return {"task": task, "status": "released", "previous": previous,
                "reason": arguments["reason"], "quiescence_evidence": recovery_evidence}, None
    if operation == "issue":
        request = sdlc.record(arguments.get("issue"), "issue")
        identity = sdlc.text(request.get("id"), "issue.id")
        if identity in value["issues"]:
            raise ValueError("Issue ID already exists")
        kind = request.get("kind")
        if kind not in ("requirement", "architecture", "environment", "implementation"):
            raise ValueError("Unknown issue kind")
        sdlc.text(request.get("observation"), "issue.observation")
        tasks = sdlc.string_list(request.get("tasks"), "issue.tasks", allow_empty=True)
        requirements = sdlc.string_list(request.get("requirements"), "issue.requirements", allow_empty=True)
        if not set(tasks) <= set(nodes) or not set(requirements) <= set(graph["requirements"]):
            raise ValueError("Issue refers to unknown tasks or requirements")
        seeds = set(tasks) | {key for key, node in nodes.items() if set(node["requirements"]) & set(requirements)}
        if not seeds:
            raise ValueError("Issue must identify at least one affected task or requirement")
        issue = {**request, "actor": actor, "revision": value["revision"], "status": "open",
                 "evidence": evidence(request.get("evidence")), "affected": sorted(closure(nodes, seeds))}
        value["issues"][identity] = issue
        return issue, None
    if operation == "revise":
        revision = revise(value, sdlc.record(arguments.get("revision"), "revision"), actor)
        return {"revision": value["revision"], "invalidated": sorted(revision["invalidated"]),
                "carried": revision["carried"]}, revision
    raise ValueError("Unknown task operation")


def initialize(path, run, actor, repo, graph_path):
    graph, workload = registered_graph(graph_path)
    identity = repo_identity(repo)
    payload = {"revision": 1, "graph": graph, "workload": workload, "actor": actor}
    connection = connect(path, create=True)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("INSERT INTO runs VALUES(?,?,?,?,?,?)", (run, identity, actor, 1, 1, encoded(graph)))
        connection.execute("INSERT INTO revisions VALUES(?,?,?)", (run, 1, encoded(payload)))
        connection.execute("INSERT INTO events(run,at,kind,payload) VALUES(?,?,?,?)", (run, time.time(), "init", encoded(payload)))
        connection.execute("COMMIT")
    except sqlite3.IntegrityError as error:
        raise ValueError("Run already exists; inspect it instead of reinitializing") from error
    finally:
        connection.close()
    return {"run": run, "revision": 1, "database": str(path)}


def execute(path, run, operation, actor, repo, **arguments):
    sdlc.text(run, "run")
    sdlc.text(actor, "actor")
    repo = Path(repo).resolve(strict=True)
    path = database_path(path)
    if operation == "init":
        return initialize(path, run, actor, repo, arguments["graph"])
    identity = repo_identity(repo)
    readonly = operation in ("status", "history", "gate")
    connection = connect(path, readonly=readonly)
    try:
        for _ in range(16):
            before = snapshot(connection, run, identity)
            if operation == "status":
                now = time.time()
                tasks = {key: {k: v for k, v in record.items() if k != "token"} for key, record in before["tasks"].items()}
                return {"run": run, "revision": before["revision"], "version": before["version"],
                        "coordinator": before["coordinator"], "graph": before["graph"], "tasks": tasks,
                        "paused": sorted(paused(before)), "issues": before["issues"],
                        "expired": sorted(key for key, record in tasks.items() if record["status"] == "running" and record["expires_at"] <= now)}
            if operation == "history":
                connection.execute("BEGIN")
                try:
                    return {"revisions": [json.loads(row[0]) for row in connection.execute("SELECT payload FROM revisions WHERE run=? ORDER BY number", (run,))],
                            "events": [{**dict(row), "payload": json.loads(row["payload"])} for row in connection.execute("SELECT sequence,at,kind,payload FROM events WHERE run=? ORDER BY sequence", (run,))]}
                finally:
                    connection.execute("ROLLBACK")
            after = copy.deepcopy(before)
            result, revision = transition(after, operation, actor, arguments, repo)
            if readonly:
                current = connection.execute("SELECT version FROM runs WHERE id=?", (run,)).fetchone()[0]
                if current == before["version"]:
                    return result
                continue
            connection.execute("BEGIN IMMEDIATE")
            try:
                current = connection.execute("SELECT version FROM runs WHERE id=?", (run,)).fetchone()[0]
                if current != before["version"]:
                    connection.execute("ROLLBACK")
                    continue
                if operation in ("finish", "heartbeat", "quiesce"):
                    lease(before["tasks"].get(arguments.get("task")), actor, arguments.get("token"))
                if revision:
                    connection.execute("UPDATE runs SET version=version+1,revision=?,graph=? WHERE id=?",
                                       (after["revision"], encoded(after["graph"]), run))
                else:
                    connection.execute("UPDATE runs SET version=version+1 WHERE id=?", (run,))
                for key in before["tasks"].keys() | after["tasks"].keys():
                    if before["tasks"].get(key) == after["tasks"].get(key):
                        continue
                    if key not in after["tasks"]:
                        connection.execute("DELETE FROM tasks WHERE run=? AND id=?", (run, key))
                    else:
                        connection.execute("INSERT INTO tasks VALUES(?,?,?) ON CONFLICT(run,id) DO UPDATE SET record=excluded.record", (run, key, encoded(after["tasks"][key])))
                for key, issue in after["issues"].items():
                    if before["issues"].get(key) != issue:
                        connection.execute("INSERT INTO issues VALUES(?,?,?) ON CONFLICT(run,id) DO UPDATE SET payload=excluded.payload", (run, key, encoded(issue)))
                if revision:
                    connection.execute("INSERT INTO revisions VALUES(?,?,?)", (run, after["revision"], encoded(revision)))
                connection.execute("INSERT INTO events(run,at,kind,payload) VALUES(?,?,?,?)", (run, time.time(), operation,
                    encoded({"actor": actor, "revision": after["revision"], "result": result})))
                connection.execute("COMMIT")
                return result
            except BaseException:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        raise ValueError("Task state changed repeatedly; retry after contention subsides")
    finally:
        connection.close()
