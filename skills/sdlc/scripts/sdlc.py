#!/usr/bin/env python3
"""Coordinate atomic delivery graphs, sparse worktrees, and workload evidence gates."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tkstack_state import ensure_state, state_container


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def record(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def records(value, label):
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list of JSON objects")
    return [record(item, label) for item in value]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".sdlc-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, indent=2)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Git command failed")
    return result.stdout if "-z" in args else result.stdout.strip()


def full_sha(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value))


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    return value


def string_list(value, label, allow_empty=False):
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{label} must be a {'possibly empty ' if allow_empty else 'nonempty '}list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} entries must be nonempty text")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains duplicates")
    return value


def ownership_prefix(path):
    if path.startswith("/") or ".." in Path(path).parts:
        raise ValueError("Ownership paths must stay inside the repository")
    parts = []
    for part in Path(path).parts:
        if any(character in part for character in "*?["):
            break
        parts.append(part)
    return Path(*parts).as_posix() if parts else "."


def validate_graph(graph):
    record(graph, "graph")
    if graph.get("version") != 1:
        raise ValueError("Unsupported graph version")
    requirements = set(string_list(graph.get("requirements"), "requirements"))
    workload = record(graph.get("workload", {}), "graph.workload")
    text(workload.get("path"), "workload.path")
    if not re.fullmatch(r"[0-9a-f]{64}", workload.get("sha256", "")):
        raise ValueError("Freeze the workload and fill its real SHA-256 before dispatch")
    limit = graph.get("max_concurrency", 4)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("max_concurrency must be a positive integer")
    tasks = graph.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("A graph requires atomic tasks")
    nodes, branches = {}, set()
    for node in tasks:
        record(node, "task")
        identity = text(node.get("id"), "task.id")
        if identity in nodes:
            raise ValueError("Duplicate task ID: " + identity)
        nodes[identity] = node
        branch = text(node.get("branch"), "task.branch")
        if branch in branches:
            raise ValueError("Each task graph branch needs exclusive ownership: " + branch)
        branches.add(branch)
        if node.get("kind", "deliverable") not in ("deliverable", "review", "mitigation"):
            raise ValueError("Unknown task kind: " + identity)
        text(node.get("base_ref"), "task.base_ref")
        text(node.get("deliverable"), "task.deliverable")
        for name in ("paths", "acceptance", "evidence", "requirements"):
            string_list(node.get(name), f"{identity}.{name}")
        for path in node["paths"]:
            ownership_prefix(path)
        if not set(node["requirements"]) <= requirements:
            raise ValueError("Task references an unknown requirement: " + identity)
        string_list(node.get("depends_on"), f"{identity}.depends_on", allow_empty=True)
    ancestors = {}
    visiting = set()
    def visit(identity):
        if identity not in nodes:
            raise ValueError("Unknown dependency: " + identity)
        if identity in visiting:
            raise ValueError("Task graph contains a cycle")
        if identity in ancestors:
            return ancestors[identity]
        visiting.add(identity)
        inherited = set()
        for parent in nodes[identity]["depends_on"]:
            inherited.add(parent)
            inherited.update(visit(parent))
        visiting.remove(identity)
        ancestors[identity] = inherited
        return inherited
    for identity, node in nodes.items():
        visit(identity)
        parent = node.get("pr_parent")
        if parent is not None and parent not in ancestors[identity]:
            raise ValueError("PR parent must be a graph dependency: " + identity)
    for index, left in enumerate(tasks):
        if left.get("kind") == "review":
            continue
        for right in tasks[index + 1:]:
            if right.get("kind") == "review" or left["id"] in ancestors[right["id"]] or right["id"] in ancestors[left["id"]]:
                continue
            for a in map(ownership_prefix, left["paths"]):
                for b in map(ownership_prefix, right["paths"]):
                    if a == "." or b == "." or a == b or a.startswith(b + "/") or b.startswith(a + "/"):
                        raise ValueError(f"Concurrent writers overlap: {left['id']} / {right['id']}; assign one owner or a real sequencing edge")
    return nodes


def load_graph(path):
    path = Path(path).resolve()
    graph = read_json(path)
    validate_graph(graph)
    workload = Path(graph["workload"]["path"])
    if not workload.is_absolute():
        workload = path.parent / workload
    if digest(workload.read_bytes()) != graph["workload"]["sha256"]:
        raise ValueError("Graph workload differs from its frozen identity")
    return graph


def evidence_policy(requirements, check_kinds, artifact_kinds, plan=None):
    if plan is None:
        plan = {identity: {"check_kinds": list(check_kinds), "artifact_kinds": list(artifact_kinds)} for identity in requirements}
    record(plan, "evidence_plan")
    if set(plan) != set(requirements):
        raise ValueError("Evidence plan must cover every frozen requirement exactly once")
    for identity, policy in plan.items():
        record(policy, "evidence policy")
        kinds = string_list(policy.get("check_kinds"), identity + ".check_kinds")
        if not set(kinds) <= {"bdd", "contract", "other"}:
            raise ValueError("Unknown check kind in evidence policy")
        string_list(policy.get("artifact_kinds"), identity + ".artifact_kinds", allow_empty=True)
    return plan


def freeze(repo, workload, out, requirements, check_kinds, artifact_kinds, evidence_plan=None):
    out = Path(out).resolve()
    with state_lock(out.with_name(out.name + ".freeze")):
        return _freeze(repo, workload, out, requirements, check_kinds, artifact_kinds, evidence_plan)


def _freeze(repo, workload, out, requirements, check_kinds, artifact_kinds, plan):
    out = Path(out).resolve()
    content = Path(workload).read_bytes()
    string_list(requirements, "requirements")
    policy = evidence_policy(requirements, check_kinds, artifact_kinds, plan)
    identity = digest(content)
    if (out / "baseline.json").exists():
        existing = read_json(out / "baseline.json")
        if (existing["workload_sha256"] != identity or existing["requirements"] != requirements
                or existing["check_kinds"] != check_kinds or existing["artifact_kinds"] != artifact_kinds
                or existing.get("evidence_plan") != policy
                or digest((out / "initial-workload.md").read_bytes()) != identity):
            raise ValueError("The initial workload is frozen; record an authorized amendment instead of replacing it")
        return existing
    if out.exists() and any(out.iterdir()):
        raise ValueError("Baseline output must be empty")
    metadata = {"version": 1, "workload_sha256": identity, "requirements": requirements,
                "check_kinds": check_kinds, "artifact_kinds": artifact_kinds,
                "evidence_plan": policy,
                "git_base_sha": git(repo, "rev-parse", "HEAD"),
                "branch": git(repo, "branch", "--show-current"),
                "origin_path": str(Path(workload).resolve())}
    out.mkdir(parents=True, exist_ok=True)
    (out / "initial-workload.md").write_bytes(content)
    write_json(out / "baseline.json", metadata)
    return metadata


@contextmanager
def state_lock(path):
    path = Path(path)
    ensure_state(path.parent)
    lock = path.with_name(path.name + ".lock")
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError("Scheduler state is busy; retry after its owner finishes") from error
    try:
        yield
    finally:
        lock.rmdir()


def scheduler_transition(graph, state, worker, task=None, outcome=None, head=None, proof=None,
                         repo=None, nodes=None, branch_heads=None, excluded=(), inspect=False):
    """Validate one transition outside any storage writer transaction."""
    nodes = nodes if nodes is not None else validate_graph(graph)
    repo = Path(repo or Path.cwd())
    text(worker, "worker")
    def branch_head(identity):
        if branch_heads is not None:
            return branch_heads.get(nodes[identity]["branch"])
        return git(repo, "rev-parse", "--verify", "refs/heads/" + nodes[identity]["branch"] + "^{commit}")
    if state["workload_sha256"] != graph["workload"]["sha256"]:
        raise ValueError("Scheduler state belongs to another workload")
    for identity, record in state["tasks"].items():
        if outcome == "retry" and identity == task and record["owner"] == worker:
            continue
        if identity not in nodes or record["definition_sha256"] != digest(json.dumps(nodes[identity], sort_keys=True).encode()):
            raise ValueError("A leased or completed task definition changed: " + identity)
        if record["status"] == "done":
            retained = Path(record["proof_path"])
            if not retained.is_file() or file_digest(retained) != record["proof_sha256"]:
                raise ValueError("Completed task proof is missing or changed: " + identity)
    reusable_results = {}
    def reusable(identity):
        if identity in reusable_results:
            return reusable_results[identity]
        accepted = state["tasks"].get(identity)
        valid = bool(accepted and accepted["status"] == "done")
        if valid:
            valid = branch_head(identity) == accepted["head_sha"]
        if valid:
            for parent, pinned_head in accepted["dependency_heads"].items():
                current = state["tasks"].get(parent, {})
                if (not reusable(parent) or current.get("head_sha") != pinned_head
                        or current.get("proof_sha256") != accepted.get("dependency_proofs", {}).get(parent)):
                    valid = False
                    break
        reusable_results[identity] = valid
        return valid
    if inspect:
        done = sorted(identity for identity in state["tasks"] if reusable(identity))
        return {"done": done, "stale": sorted(identity for identity, value in state["tasks"].items()
                if value["status"] == "done" and identity not in done)}
    if outcome:
        record = state["tasks"].get(task)
        if not record or record["owner"] != worker or (record["status"] not in ("running", "blocked") and outcome != "retry"):
            raise ValueError("Only the current task owner may release its lease")
        if outcome == "done":
            if not full_sha(head) or not proof or not Path(proof).is_file():
                raise ValueError("Completion needs the exact head and a retained proof file")
            if branch_head(task) != head:
                raise ValueError("Completion head differs from the actual task branch")
            for parent, accepted in record["dependency_heads"].items():
                if branch_head(parent) != accepted:
                    raise ValueError("Task input moved after its lease: " + parent)
                if (not reusable(parent) or state["tasks"][parent]["head_sha"] != accepted
                        or state["tasks"][parent]["proof_sha256"] != record["dependency_proofs"][parent]):
                    raise ValueError("Task input proof was invalidated after its lease: " + parent)
            changed = git(repo, "diff", "--no-renames", "--name-only", "-z", record["base_sha"], head).split("\0")
            for path in changed:
                if not path:
                    continue
                allowed = any(Path(pattern).as_posix() == "." or
                              fnmatch.fnmatchcase(path, pattern.rstrip("/")) or
                              (not any(char in pattern for char in "*?[") and
                               (path == Path(pattern).as_posix().rstrip("/") or
                                path.startswith(Path(pattern).as_posix().rstrip("/") + "/")))
                              for pattern in nodes[task]["paths"])
                if not allowed:
                    raise ValueError("Task changed a path outside its declared ownership: " + path)
            result = read_json(proof)
            if (not isinstance(result, dict) or result.get("task_id") != task
                    or result.get("workload_sha256") != record.get("workload_sha256", graph["workload"]["sha256"])
                    or result.get("head_sha") != head or result.get("result") != "pass"
                    or set(result.get("requirements", [])) != set(nodes[task]["requirements"])
                    or result.get("dependency_heads") != record["dependency_heads"]):
                raise ValueError("Task proof must match task/workload/head/requirements/input heads")
            string_list(result.get("checks"), "task proof checks")
            record.update(head_sha=head, proof_path=str(Path(proof).resolve()), proof_sha256=file_digest(Path(proof)))
        if outcome == "retry":
            del state["tasks"][task]
        else:
            record["status"] = outcome
        result = {"task": task, "status": outcome}
    else:
        running = [item for item in state["tasks"].values() if item["status"] == "running"]
        if len(running) >= graph.get("max_concurrency", 4):
            return {"task": None, "reason": "capacity"}
        done = {identity for identity in state["tasks"] if reusable(identity)}
        available = [node for node in graph["tasks"] if node["id"] not in state["tasks"] and node["id"] not in excluded and set(node["depends_on"]) <= done]
        node = next((node for node in available if task is None or node["id"] == task), None)
        if node is None:
            stale = sorted(identity for identity, item in state["tasks"].items()
                           if item["status"] == "done" and identity not in done)
            return {"task": None, "reason": "no ready node", "stale_tasks": stale}
        dependency_heads = {}
        inputs = list(node["depends_on"])
        if node.get("pr_parent") and node["pr_parent"] not in inputs:
            inputs.append(node["pr_parent"])
        for parent in inputs:
            accepted = state["tasks"][parent]["head_sha"]
            current = branch_head(parent)
            if current != accepted:
                raise ValueError("Dependency branch moved after proof: " + parent)
            dependency_heads[parent] = accepted
        base_sha = git(repo, "rev-parse", "--verify", node["base_ref"] + "^{commit}")
        if node.get("pr_parent"):
            git(repo, "merge-base", "--is-ancestor", dependency_heads[node["pr_parent"]], base_sha)
        state["tasks"][node["id"]] = {"status": "running", "owner": worker,
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "workload_sha256": graph["workload"]["sha256"],
            "base_sha": base_sha, "dependency_heads": dependency_heads,
            "dependency_proofs": {parent: state["tasks"][parent]["proof_sha256"] for parent in dependency_heads},
            "definition_sha256": digest(json.dumps(node, sort_keys=True).encode())}
        result = {"task": node["id"], "owner": worker, "branch": node["branch"],
                  "base_sha": base_sha, "dependency_heads": dependency_heads}
    return result

def scheduler(graph, state_path, worker, task=None, outcome=None, head=None, proof=None, repo=None):
    """Compatibility adapter for existing JSON scheduler files."""
    with state_lock(state_path):
        state = read_json(state_path) if Path(state_path).exists() else {"workload_sha256": graph["workload"]["sha256"], "tasks": {}}
        result = scheduler_transition(graph, state, worker, task, outcome, head, proof, repo)
        write_json(state_path, state)
        return result


def cow_method(seed_file, root):
    cp = shutil.which("cp")
    if not cp:
        return None
    for flags in (["--reflink=always"], ["-c"] if sys.platform == "darwin" else []):
        if not flags:
            continue
        with tempfile.TemporaryDirectory(prefix=".sdlc-cow-", dir=root) as probe:
            result = subprocess.run([cp, *flags, str(seed_file), str(Path(probe) / "probe")], capture_output=True)
            if result.returncode == 0:
                return [cp, *flags]
    return None


def _reflink_copy(source, destination, method):
    with tempfile.TemporaryDirectory(prefix=".sdlc-reflink-", dir=destination.parent) as temporary:
        cloned = Path(temporary) / "clone"
        subprocess.run([*method, str(source), str(cloned)], check=True, capture_output=True)
        cloned.chmod(destination.stat().st_mode & 0o777)
        cloned.replace(destination)


def worktree(repo, root, branch, base, paths, seed=None, cache_root=None, require_cow=False):
    state_container(root)
    if cache_root is not None:
        state_container(cache_root)
    repo, root = Path(repo).resolve(), Path(root).resolve()
    base_sha = git(repo, "rev-parse", "--verify", base + "^{commit}")
    git(repo, "check-ref-format", "--branch", branch)
    registered = [Path(line[len("worktree "):]).resolve() for line in git(repo, "worktree", "list", "--porcelain").splitlines() if line.startswith("worktree ")]
    cache = (Path(cache_root) if cache_root else root / ".shared-cache").resolve()
    if any(root.is_relative_to(checkout) or cache.is_relative_to(checkout) for checkout in registered):
        raise ValueError("Worktree and shared-cache roots must be outside all registered checkouts")
    if cache == root:
        raise ValueError("Keep the cache in a dedicated directory")
    for path in paths:
        if not path or path.startswith("/") or ".." in Path(path).parts or any(char in path for char in "*?[\n\r"):
            raise ValueError("Sparse paths must be explicit repository-relative cone directories")
    if not paths:
        raise ValueError("Select the sparse directories needed by this task")
    ensure_state(root)
    method = None
    if seed:
        seed = Path(seed).resolve()
        if git(seed, "rev-parse", "HEAD") != base_sha or git(seed, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("COW seed must be pristine and pinned to the exact base commit")
        candidates = [seed / name for name in git(seed, "ls-files", "-z").split("\0") if name]
        seed_file = next((path for path in candidates if path.is_file() and not path.is_symlink() and path.stat().st_size), None)
        method = cow_method(seed_file, root) if seed_file else None
    if require_cow and method is None:
        raise ValueError("Verified filesystem COW is unavailable; no branch was dispatched")
    name = branch.replace("/", "--") + "-" + digest(branch.encode())[:8]
    directory = root / name
    if cache.is_relative_to(directory) or directory.is_relative_to(cache):
        raise ValueError("Shared cache and task checkout must be separate")
    if directory.exists():
        raise ValueError("Worktree path already exists: " + str(directory))
    git(repo, "worktree", "add", "--no-checkout", "-b", branch, str(directory), base_sha)
    try:
        result = subprocess.run(["git", "-C", str(directory), "sparse-checkout", "set", "--cone", "--stdin"],
                                input="\n".join(paths) + "\n", text=True, capture_output=True)
        if result.returncode:
            raise ValueError(result.stderr.strip())
        git(directory, "read-tree", "-mu", "HEAD")
        copied = 0
        if method:
            for filename in git(directory, "ls-files", "-z").split("\0"):
                source, destination = seed / filename, directory / filename
                if not filename or not destination.is_file() or destination.is_symlink():
                    continue
                if not source.is_file() or source.is_symlink() or file_digest(source) != file_digest(destination):
                    raise ValueError("The COW seed lacks an identical materialized tracked file: " + filename)
                _reflink_copy(source, destination, method)
                copied += 1
        if git(directory, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("Worktree is not pristine after sparse/COW materialization")
    except Exception as error:
        raise ValueError(f"Worktree setup failed; retained unready worktree {directory} for inspection: {error}") from error
    ensure_state(cache)
    build = state_container(root) / "build" / name / "cargo"
    ensure_state(build.parent)
    environment = {"npm_config_cache": str(cache / "npm"), "PIP_CACHE_DIR": str(cache / "pip"),
                   "UV_CACHE_DIR": str(cache / "uv"), "UV_LINK_MODE": "clone" if method else "copy",
                   "SCCACHE_DIR": str(cache / "sccache"), "CARGO_TARGET_DIR": str(build)}
    return {"path": str(directory), "branch": branch, "base_sha": base_sha,
            "cow": bool(method), "cow_files": copied,
            "storage_mode": "verified-reflink-sparse" if method else "sparse-shared-git-objects-only",
            "shared_git_objects": git(directory, "rev-parse", "--path-format=absolute", "--git-common-dir"),
            "cache_root": str(cache), "environment": environment}


def verified_file(root, record):
    path = Path(record["path"])
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Evidence paths must stay relative to the manifest")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("Evidence artifact is missing or outside its retained directory: " + str(path))
    if file_digest(resolved) != record["sha256"]:
        raise ValueError("Evidence artifact hash mismatch: " + str(path))
    return str(path)


def review_digest(manifest):
    return digest(json.dumps({key: value for key, value in manifest.items() if key not in ("review", "pr")},
                             sort_keys=True, separators=(",", ":")).encode())


def gate(repo, baseline, manifest_path, merge=False):
    baseline, manifest_path = Path(baseline).resolve(), Path(manifest_path).resolve()
    initial = record(read_json(baseline / "baseline.json"), "baseline")
    if initial.get("version") != 1:
        raise ValueError("Unsupported baseline version")
    if digest((baseline / "initial-workload.md").read_bytes()) != initial["workload_sha256"]:
        raise ValueError("Frozen initial workload was changed")
    manifest = record(read_json(manifest_path), "evidence manifest")
    head = git(repo, "rev-parse", "HEAD")
    if manifest.get("workload_sha256") != initial["workload_sha256"] or manifest.get("head_sha") != head:
        raise ValueError("Evidence is stale or bound to another workload/head")
    requirements = set(initial["requirements"])
    policies = evidence_policy(initial["requirements"], initial["check_kinds"], initial["artifact_kinds"], initial.get("evidence_plan"))
    superseded = {}
    amendment_ids = set()
    for amendment in records(manifest.get("amendments", []), "amendments"):
        record(amendment, "amendment")
        verified_file(manifest_path.parent, amendment)
        text(amendment.get("authorized_by"), "amendment.authorized_by")
        text(amendment.get("reason"), "amendment.reason")
        identity = text(amendment.get("id"), "amendment.id")
        if identity in amendment_ids:
            raise ValueError("Amendment IDs must be unique")
        amendment_ids.add(identity)
        additions = string_list(amendment.get("requirements_added", []), "amendment.requirements_added", allow_empty=True)
        withdrawals = string_list(amendment.get("requirements_superseded", []), "amendment.requirements_superseded", allow_empty=True)
        record(amendment.get("evidence_plan", {}), "amendment.evidence_plan")
        for requirement in additions:
            if requirement in requirements:
                raise ValueError("Amendment duplicates a requirement")
            requirements.add(requirement)
            policy = amendment.get("evidence_plan", {}).get(requirement)
            policies[requirement] = evidence_policy([requirement], initial["check_kinds"], initial["artifact_kinds"],
                                                   {requirement: policy} if policy else None)[requirement]
        for requirement in withdrawals:
            if requirement not in requirements:
                raise ValueError("Amendment supersedes an unknown requirement")
            superseded[requirement] = identity
    checks = {}
    for check in records(manifest.get("checks", []), "checks"):
        record(check, "check")
        identity = text(check.get("id"), "check.id")
        if identity in checks or check.get("result") != "pass" or check.get("head_sha") != head:
            raise ValueError("Checks must be unique, passing, and current-head: " + identity)
        text(check.get("command"), "check.command")
        if not set(string_list(check.get("requirements"), "check.requirements")) <= requirements:
            raise ValueError("Check references an unknown requirement")
        checks[identity] = check
    required_kinds = {kind for requirement, policy in policies.items() if requirement not in superseded for kind in policy["check_kinds"]}
    if not required_kinds <= {check.get("kind") for check in checks.values()}:
        raise ValueError("Required BDD/contract check kinds are missing")
    artifacts = {}
    for artifact in records(manifest.get("artifacts", []), "artifacts"):
        record(artifact, "artifact")
        path = verified_file(manifest_path.parent, artifact)
        if path in artifacts or not set(string_list(artifact.get("requirements"), "artifact.requirements")) <= requirements:
            raise ValueError("Artifact paths must be unique and map to known requirements")
        revision = initial["git_base_sha"] if artifact.get("side") == "before" else head
        if artifact.get("revision") != revision:
            raise ValueError("Artifact revision does not match its baseline/candidate side: " + path)
        text(artifact.get("capture_command"), "artifact.capture_command")
        if not isinstance(artifact.get("environment"), dict) or not artifact["environment"]:
            raise ValueError("Artifact environment/fixture metadata is required")
        artifacts[path] = artifact
    rows = records(manifest.get("compliance", []), "compliance")
    if {row.get("requirement") for row in rows} != requirements or len(rows) != len(requirements):
        raise ValueError("Compliance must account for every initial and amended requirement exactly once")
    for row in rows:
        record(row, "compliance row")
        requirement = row["requirement"]
        text(row.get("rationale"), "compliance.rationale")
        if requirement in superseded:
            if row.get("verdict") != "superseded" or row.get("amendment") != superseded[requirement]:
                raise ValueError("Retain superseded requirements with their authorizing amendment")
            continue
        if row.get("verdict") != "pass":
            raise ValueError("An applicable requirement has not passed: " + requirement)
        references = row.get("checks", [])
        if not references or any(identity not in checks or requirement not in checks[identity]["requirements"] for identity in references):
            raise ValueError("Compliance needs checks for the specific requirement: " + requirement)
        for path in row.get("evidence", []):
            if path not in artifacts or requirement not in artifacts[path]["requirements"]:
                raise ValueError("Compliance artifact does not prove the referenced requirement")
        for kind in policies[requirement]["check_kinds"]:
            if not any(checks[identity].get("kind") == kind for identity in references):
                raise ValueError("Required check kind does not cover requirement: " + requirement)
            if kind == "contract":
                contracts = [checks[identity] for identity in references if checks[identity].get("kind") == "contract"]
                digests = set()
                for check in contracts:
                    contract = artifacts.get(check.get("contract_artifact"))
                    if (not contract or contract.get("kind") != "contract"
                            or requirement not in contract["requirements"]
                            or contract["sha256"] != check.get("contract_sha256")):
                        raise ValueError("Contract checks need the same retained, hashed interaction artifact")
                    digests.add(check["contract_sha256"])
                for contract_digest in digests:
                    pair = [check for check in contracts if check["contract_sha256"] == contract_digest]
                    if not any(check.get("role") == "consumer" for check in pair) or not any(check.get("role") == "provider" and check.get("real_provider") is True for check in pair):
                        raise ValueError("Each requirement/contract needs consumer and real-provider verification")
        for kind in policies[requirement]["artifact_kinds"]:
            matching = [artifacts[path] for path in row.get("evidence", []) if artifacts[path].get("kind") == kind]
            if not matching:
                raise ValueError("Required artifact kind is missing for " + requirement + ": " + kind)
            if kind == "screenshot":
                paired = False
                for before in matching:
                    if before.get("side") != "before":
                        continue
                    identity = text(before.get("comparison_id"), "screenshot.comparison_id")
                    for after in matching:
                        if after.get("side") == "after" and after.get("comparison_id") == identity:
                            keys = ("viewport", "device_scale", "theme", "state", "fixture")
                            if all(key in before["environment"] and before["environment"][key] == after["environment"].get(key) for key in keys):
                                paired = True
                if not paired:
                    raise ValueError("Visual evidence requires matched before/after screenshots and capture conditions")
    for finding in records(manifest.get("findings", []), "findings"):
        record(finding, "finding")
        if finding.get("status") not in ("resolved", "rejected-with-evidence"):
            raise ValueError("Adversarial finding remains open")
        text(finding.get("resolution"), "finding.resolution")
        if finding.get("verification_head_sha") != head or not finding.get("evidence"):
            raise ValueError("Finding disposition needs current-head counterevidence or verification")
        if any(item not in checks and item not in artifacts for item in finding["evidence"]):
            raise ValueError("Finding references missing verification evidence")
    review = record(manifest.get("review", {}), "review")
    text(manifest.get("implementation_owner"), "implementation_owner")
    text(review.get("reviewer"), "review.reviewer")
    if (review["reviewer"].strip() == manifest["implementation_owner"].strip()
            or review.get("verdict") != "approve" or review.get("requirements_complete") is not True
            or review.get("head_sha") != head or review.get("workload_sha256") != initial["workload_sha256"]):
        raise ValueError("An independent current-head workload compliance approval is required")
    if review.get("evidence_sha256") != review_digest(manifest):
        raise ValueError("Independent approval does not cover this evidence/compliance/amendment payload")
    if manifest.get("amendments") and review.get("amendments_verified") is not True:
        raise ValueError("Independent review must verify workload amendments")
    if merge:
        pr = manifest.get("pr", {})
        if pr.get("head_sha") != head or not all(pr.get(field) is True for field in
                ("checks_green", "comments_complete", "approvals_current", "dependencies_merged", "mergeable")):
            raise ValueError("PR merge gate is not current and complete")
        for comment in records(pr.get("comments", []), "pr.comments"):
            if comment.get("status") not in ("fixed", "answered", "resolved", "rejected-with-evidence", "acknowledged", "scope-amendment"):
                raise ValueError("A PR comment is unaddressed")
            text(comment.get("resolution"), "comment.resolution")
    return {"structural_gate": "pass", "head_sha": head, "requirements": len(requirements),
            "note": "Artifact meaning and live PR state require the independent reviewer and native host checks"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze_parser = commands.add_parser("freeze")
    freeze_parser.add_argument("--repo", type=Path, default=Path.cwd())
    freeze_parser.add_argument("--workload", type=Path, required=True)
    freeze_parser.add_argument("--out", type=Path, required=True)
    freeze_parser.add_argument("--requirement", action="append", required=True)
    freeze_parser.add_argument("--check-kind", action="append", choices=("bdd", "contract", "other"))
    freeze_parser.add_argument("--artifact-kind", action="append", default=[])
    freeze_parser.add_argument("--evidence-plan", type=Path)
    validate = commands.add_parser("graph")
    validate.add_argument("path", type=Path)
    for command in ("claim", "finish"):
        sub = commands.add_parser(command)
        sub.add_argument("--graph", type=Path, required=True)
        sub.add_argument("--state", type=Path, required=True)
        sub.add_argument("--worker", required=True)
        sub.add_argument("--task", required=command == "finish")
        sub.add_argument("--repo", type=Path, default=Path.cwd())
        if command == "finish":
            sub.add_argument("--outcome", choices=("done", "blocked", "retry"), required=True)
            sub.add_argument("--head")
            sub.add_argument("--proof", type=Path)
    wt = commands.add_parser("worktree")
    for name in ("repo", "root"):
        wt.add_argument("--" + name, type=Path, required=True)
    wt.add_argument("--branch", required=True)
    wt.add_argument("--base", required=True)
    wt.add_argument("--path", action="append", required=True)
    wt.add_argument("--seed", type=Path)
    wt.add_argument("--cache-root", type=Path)
    wt.add_argument("--require-cow", action="store_true")
    evidence = commands.add_parser("gate")
    evidence.add_argument("--repo", type=Path, default=Path.cwd())
    evidence.add_argument("--baseline", type=Path, required=True)
    evidence.add_argument("--manifest", type=Path, required=True)
    evidence.add_argument("--merge", action="store_true")
    review_parser = commands.add_parser("review-digest")
    review_parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            result = freeze(args.repo, args.workload, args.out, args.requirement,
                            args.check_kind or ["bdd", "contract"], args.artifact_kind,
                            read_json(args.evidence_plan) if args.evidence_plan else None)
        elif args.command == "graph":
            graph = load_graph(args.path)
            result = {"valid": True, "tasks": len(graph["tasks"]), "requirements": graph["requirements"]}
        elif args.command in ("claim", "finish"):
            result = scheduler(load_graph(args.graph), args.state, args.worker, args.task,
                               getattr(args, "outcome", None), getattr(args, "head", None), getattr(args, "proof", None), args.repo)
        elif args.command == "worktree":
            result = worktree(args.repo, args.root, args.branch, args.base, args.path,
                              args.seed, args.cache_root, args.require_cow)
        elif args.command == "review-digest":
            result = {"evidence_sha256": review_digest(record(read_json(args.manifest), "evidence manifest"))}
        else:
            result = gate(args.repo, args.baseline, args.manifest, args.merge)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"sdlc: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
