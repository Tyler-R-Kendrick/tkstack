"""Real Git/SQLite contract tests for durable coordination and loop backedges."""

from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_sdlc as legacy

ROOT, sdlc = legacy.ROOT, legacy.sdlc

sys.path.insert(0, str(ROOT / "skills/sdlc/scripts"))
import task_store as store
import task_graph_tool as tool


class DurableSdlcTests(unittest.TestCase):
    setUp = legacy.SdlcTests.setUp
    git = legacy.SdlcTests.git
    node = legacy.SdlcTests.node
    graph = legacy.SdlcTests.graph

    def initialize(self, nodes=None):
        self.db = self.root.parent / "sdlc/task-graph.sqlite3"
        self.graph_file = self.root / "graph.json"
        self.definition = self.graph(*(nodes or [self.node("a"), self.node("b")]))
        self.definition["requirements"] = sorted({r for n in self.definition["tasks"] for r in n["requirements"]})
        self.graph_file.write_text(json.dumps(self.definition))
        return self.call("init", graph=str(self.graph_file))

    def call(self, operation, actor="coordinator", **args):
        return store.execute(self.db, "run", operation, actor, self.repo, **args)

    def proof(self, claim):
        task = claim["task"]
        node = next(node for node in self.definition["tasks"] if node["id"] == task)
        self.git("branch", node["branch"], self.head)
        path = self.reports / (task + ".json")
        path.write_text(json.dumps({"task_id": task, "workload_sha256": claim["workload_sha256"],
            "head_sha": self.head, "result": "pass", "requirements": node["requirements"],
            "checks": ["public behavior contract"], "dependency_heads": claim["dependency_heads"]}))
        return str(path)

    def finish(self, claim, actor="worker"):
        return self.call("finish", actor, task=claim["task"], token=claim["token"],
                         outcome="done", head=self.head, proof=self.proof(claim))

    def issue(self, kind="architecture", tasks=None):
        observation = self.reports / "discovery.txt"
        observation.write_text("The assumed storage interface cannot preserve the required ordering.")
        return self.call("issue", "worker", issue={"id": "I1", "kind": kind,
            "observation": observation.read_text(), "tasks": tasks or ["a"],
            "requirements": [], "evidence": [str(observation)]})

    def amendment(self, **changes):
        self.workload.write_text("R1: revised behavior\n")
        graph = copy.deepcopy(self.definition)
        graph["workload"]["sha256"] = sdlc.file_digest(self.workload)
        self.graph_file.write_text(json.dumps(graph))
        value = {"expected_revision": 1, "graph": str(self.graph_file),
            "authorization": "Current user's requested feature scope", "rationale": "Storage discovery requires a new contract",
            "requirements": [{"id": "R1", "status": "changed", "reason": "Ordering revised within the authorized scope"}],
            "resolves": ["I1"], "adrs": []}
        value.update(changes)
        return value

    def test_restart_and_ignore_policy_outside_sessions(self):
        with patch.dict(os.environ, {"TKSTACK_SESSION_ID": "temporary"}):
            self.initialize()
            lease = self.call("claim", "worker", task="a")
            self.assertEqual(self.call("status")["tasks"]["a"]["owner"], "worker")
            self.assertNotIn("token", self.call("status")["tasks"]["a"])
            self.assertEqual(store.database_path(project=self.repo), self.repo / ".tkstack/sdlc/task-graph.sqlite3")
        connection = sqlite3.connect(self.db)
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertIn("/sdlc/", (self.root.parent / ".gitignore").read_text())
        self.assertEqual(lease["revision"], 1)
        self.assertEqual(self.call("history")["revisions"][0]["workload"], self.workload.read_text())
        # Check SQLite, WAL, and SHM paths against Git's actual ignore semantics.
        self.git("init", "-q", str(self.root.parent.parent))
        for suffix in ("", "-wal", "-shm"):
            name = str(self.db) + suffix
            result = subprocess.run(["git", "-C", str(self.root.parent.parent), "check-ignore", name], capture_output=True)
            self.assertEqual(result.returncode, 0, name)

    def test_concurrent_process_claims_exactly_once_with_capacity(self):
        self.initialize([self.node(str(number), paths=["src/" + str(number)]) for number in range(8)])
        def claim(number):
            payload = {"operation": "claim", "database": str(self.db), "repo": str(self.repo),
                       "run": "run", "actor": "worker-" + str(number)}
            process = subprocess.run([sys.executable, str(ROOT / "skills/sdlc/scripts/task_graph_tool.py"), "--input", "-"],
                                     input=json.dumps(payload), text=True, capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            return json.loads(process.stdout)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(claim, range(8)))
        claimed = [item["task"] for item in results if item["task"]]
        self.assertEqual(len(claimed), 2)
        self.assertEqual(len(set(claimed)), 2)
        self.assertEqual(len(self.call("status")["tasks"]), 2)

    def test_crashed_transaction_rolls_back_without_stale_lock(self):
        self.initialize()
        script = "import os,sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('BEGIN IMMEDIATE'); c.execute('UPDATE runs SET revision=999'); os._exit(3)"
        result = subprocess.run([sys.executable, "-c", script, str(self.db)])
        self.assertEqual(result.returncode, 3)
        self.assertEqual(self.call("status")["revision"], 1)
        self.assertEqual(self.call("claim", "worker")["task"], "a")
        self.assertFalse(Path(str(self.db) + ".lock").exists())

    def test_expired_lease_requires_confirmed_recovery_and_new_token(self):
        self.initialize()
        first = self.call("claim", "worker", task="a")
        with patch.object(store.time, "time", return_value=first["expires_at"] + 1):
            with self.assertRaisesRegex(ValueError, "unexpired"):
                self.call("heartbeat", "worker", task="a", token=first["token"])
            self.assertIsNone(self.call("claim", "new", task="a")["task"])
            with self.assertRaisesRegex(ValueError, "evidence"):
                self.call("recover", task="a", reason="worker stopped")
            retained = self.reports / "quiesced.txt"
            retained.write_text("Worker process exited; writable worktree ownership released.")
            self.call("recover", task="a", reason="Observed process exit", evidence=[str(retained)])
            second = self.call("claim", "worker", task="a")
            self.assertNotEqual(first["token"], second["token"])
            with self.assertRaisesRegex(ValueError, "unexpired"):
                self.call("finish", "worker", task="a", token=first["token"], outcome="retry")

    def test_live_lease_cannot_be_recovered(self):
        self.initialize()
        self.call("claim", "worker", task="a")
        file = self.reports / "reason.txt"
        file.write_text("No proof of worker exit")
        with self.assertRaisesRegex(ValueError, "Live owners"):
            self.call("recover", task="a", reason="try again", evidence=[str(file)])

    def test_backedge_pauses_descendants_and_allows_independent_work(self):
        self.initialize([self.node("a"), self.node("b"), self.node("c", depends_on=["a"])])
        claim = self.call("claim", "worker", task="a")
        self.assertEqual(self.issue()["affected"], ["a", "c"])
        self.assertEqual(self.call("claim", "other")["task"], "b")
        with self.assertRaisesRegex(ValueError, "paused"):
            self.call("finish", "worker", task="a", token=claim["token"], outcome="retry")
        self.call("quiesce", "worker", task="a", token=claim["token"], reason="Stopped writes; needs outer loop decision")
        self.assertEqual(self.call("status")["tasks"]["a"]["status"], "blocked")
        with self.assertRaisesRegex(ValueError, "gate blocked"):
            self.call("gate")

    def test_revision_requires_quiescence_authority_dispositions_and_adr(self):
        self.initialize()
        claim = self.call("claim", "worker", task="a")
        self.issue()
        request = self.amendment()
        with self.assertRaisesRegex(ValueError, "coordinator"):
            self.call("revise", "worker", revision=request)
        for changes, expected in (({"authorization": ""}, "authorization"),
                                  ({"requirements": []}, "every previous"),
                                  ({"expected_revision": 0}, "Revision changed"),
                                  ({}, "ADR")):
            with self.assertRaisesRegex(ValueError, expected):
                self.call("revise", revision={**request, **changes})
        adr = self.reports / "ADR-001.md"
        adr.write_text("# ADR-001\nUse a transactional ordering boundary.\n")
        request["adrs"] = [{"path": str(adr), "decision": "accepted: transactional ordering"}]
        with self.assertRaisesRegex(ValueError, "quiesce"):
            self.call("revise", revision=request)
        self.call("quiesce", "worker", task="a", token=claim["token"], reason="stopped")
        self.call("revise", revision=request)
        history = self.call("history")
        self.assertEqual(len(history["revisions"]), 2)
        self.assertNotEqual(history["revisions"][0]["workload"], history["revisions"][1]["workload"])
        self.assertEqual(history["revisions"][1]["adrs"][0]["content"], adr.read_text())
        self.assertEqual(self.call("status")["issues"]["I1"]["status"], "resolved")
        self.assertEqual(self.call("claim", "worker", task="a")["revision"], 2)

    def test_unchanged_work_retains_its_claimed_workload_across_amendment(self):
        a, b = self.node("a"), self.node("b")
        b["requirements"] = ["R2"]
        self.initialize([a, b])
        unchanged = self.call("claim", "worker", task="b")
        self.issue(kind="requirement")
        request = self.amendment(requirements=[
            {"id": "R1", "status": "changed", "reason": "Requirement discovery"},
            {"id": "R2", "status": "unchanged", "reason": "Unrelated behavior retained exactly"}])
        result = self.call("revise", revision=request)
        self.assertEqual(result["carried"], ["b"])
        self.finish(unchanged)
        history = self.call("history")
        self.assertEqual(history["revisions"][1]["carried"], ["b"])
        self.assertEqual(self.call("status")["tasks"]["b"]["workload_sha256"], unchanged["workload_sha256"])

    def test_accepted_proofs_invalidate_on_revision_and_stay_in_history(self):
        self.initialize([self.node("a"), self.node("c", depends_on=["a"])])
        first = self.call("claim", "worker", task="a")
        self.finish(first)
        child = self.call("claim", "worker", task="c")
        self.finish(child)
        self.assertEqual(self.call("gate")["task_gate"], "pass")
        self.issue(kind="requirement")
        result = self.call("revise", revision=self.amendment())
        self.assertEqual(result["invalidated"], ["a", "c"])
        self.assertEqual(self.call("status")["tasks"], {})
        invalidated = self.call("history")["revisions"][1]["invalidated"]
        self.assertEqual(invalidated["a"]["head_sha"], self.head)
        self.assertTrue(Path(invalidated["a"]["proof_path"]).is_file())
        with self.assertRaisesRegex(ValueError, "gate blocked"):
            self.call("gate")

    def test_proof_tampering_and_other_repository_are_rejected(self):
        self.initialize()
        first = self.call("claim", "worker", task="a")
        self.finish(first)
        (self.reports / "a.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "proof is missing or changed"):
            self.call("claim", "other", task="b")
        other = self.root / "other"
        other.mkdir()
        self.git("init", "-q", str(other))
        with self.assertRaisesRegex(ValueError, "another repository"):
            store.execute(self.db, "run", "status", "coordinator", other)

    def test_readonly_missing_store_and_unsafe_paths_do_not_initialize(self):
        path = self.repo / ".tkstack/sdlc/missing.sqlite3"
        with self.assertRaisesRegex(ValueError, "does not exist"):
            store.execute(path, "run", "status", "worker", self.repo)
        self.assertFalse(path.parent.exists())
        for path in (self.repo / "bad.db", self.repo / ".tkstack/sessions/temp/sdlc/x.db"):
            with self.assertRaises(ValueError):
                store.database_path(path)
        outside = self.root / "outside"
        outside.mkdir()
        link = self.root.parent / "sdlc"
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            store.database_path(link / "x.db")

    def test_short_write_transaction_and_batched_git_reference_lookup(self):
        self.initialize()
        commands = []
        original = store.sdlc.git
        def observed(repo, *args):
            # An unrelated writer can acquire the lock during every Git lookup.
            connection = sqlite3.connect(self.db, timeout=0)
            connection.execute("BEGIN IMMEDIATE")
            connection.rollback()
            connection.close()
            commands.append(args[0])
            return original(repo, *args)
        with patch.object(store.sdlc, "git", side_effect=observed):
            self.call("claim", "worker", task="a")
        self.assertEqual(commands.count("for-each-ref"), 1)
        self.assertEqual(commands.count("rev-parse"), 2)  # repository identity and base only

    def test_compiled_cli_and_openai_call_share_real_durable_state(self):
        self.initialize()
        environment = {**os.environ, "TKSTACK_WORKSPACE_DIR": str(self.repo / ".tkstack")}
        command = [sys.executable, str(ROOT / "skills/codify/scripts/codify.py"),
                   "invoke", str(ROOT / "skills/sdlc")]
        result = subprocess.run([*command, "--", "claim", "--run", "run", "--actor", "worker",
                                 "--database", str(self.db), "--repo", str(self.repo), "--task", "a"],
                                env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        claimed = json.loads(result.stdout)
        self.assertEqual(claimed["task"], "a")
        arguments = {"operation": "status", "run": "run", "actor": "observer", "database": str(self.db),
                     "repo": str(self.repo), "scope": "workspace"}
        call = self.root / "call.json"
        for shape in ({"name": "sdlc_tasks_status", "arguments": json.dumps(arguments)},
                      {"type": "function", "function": {"name": "sdlc_tasks_status", "arguments": json.dumps(arguments)}}):
            call.write_text(json.dumps(shape))
            response = subprocess.run([*command, "--call", str(call)], env=environment, text=True, capture_output=True)
            self.assertEqual(response.returncode, 0, response.stderr)
            self.assertEqual(json.loads(response.stdout)["tasks"]["a"]["owner"], "worker")
        before = self.call("status")["version"]
        response = subprocess.run([*command, "--", "tasks", "claim", "--run", "run", "--actor", "other", "--ttl", "0"],
                                  env=environment, text=True, capture_output=True)
        self.assertNotEqual(response.returncode, 0)
        self.assertEqual(self.call("status")["version"], before)

    def test_default_help_does_not_create_selected_workspace_state(self):
        target = self.root / "empty-project"
        target.mkdir()
        result = subprocess.run([sys.executable, str(ROOT / "skills/codify/scripts/codify.py"),
                                 "invoke", str(ROOT / "skills/sdlc")], capture_output=True, text=True,
                                env={**os.environ, "TKSTACK_WORKSPACE_DIR": str(target / ".tkstack")})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tasks revise", result.stdout)
        self.assertFalse((target / ".tkstack").exists())


if __name__ == "__main__":
    unittest.main()
