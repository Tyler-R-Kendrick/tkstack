"""Behavioral checks for retained workload proof and isolated delivery leases.

The evidence fixtures are synthetic structural reports. They do not stand in for
an independent review, a real provider verification, or native hosting checks.
"""

import copy
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/sdlc/scripts/sdlc.py"
SPEC = importlib.util.spec_from_file_location("sdlc_helper", SCRIPT)
sdlc = importlib.util.module_from_spec(SPEC)
_bytecode_setting = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    SPEC.loader.exec_module(sdlc)
finally:
    sys.dont_write_bytecode = _bytecode_setting


class SdlcTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tkstack-sdlc-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / ".tkstack/tests"
        self.root.mkdir(parents=True)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "SDLC Test")
        self.git("config", "user.email", "sdlc-test@example.invalid")
        for name in ("src/a/app.py", "src/b/app.py", "root.txt"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("original " + name + "\n")
        self.git("add", ".")
        self.git("commit", "-qm", "initial")
        self.head = self.git("rev-parse", "HEAD")
        self.workload = self.root / "workload.md"
        self.workload.write_text("R1: first behavior\nR2: second behavior\n")
        self.workload_sha = sdlc.digest(self.workload.read_bytes())
        self.state = self.root / "state.json"
        self.baseline = self.root / "baseline"
        self.reports = self.root / "reports"
        self.reports.mkdir()
        self.manifest_path = self.reports / "manifest.json"

    def git(self, *args, repo=None):
        result = subprocess.run(
            ["git", "-C", str(repo or self.repo), *args],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()

    def branch_exists(self, branch):
        result = subprocess.run(
            ["git", "-C", str(self.repo), "show-ref", "--verify", "--quiet", "refs/heads/" + branch],
            capture_output=True,
        )
        return result.returncode == 0

    def node(self, identity, paths=None, depends_on=None):
        return {
            "id": identity, "kind": "deliverable", "branch": "task/" + identity,
            "base_ref": self.head, "deliverable": "Observable behavior " + identity,
            "requirements": ["R1"], "paths": paths or ["src/" + identity],
            "acceptance": ["Given input, when called, then an observable result is returned"],
            "evidence": ["BDD and contract report"], "depends_on": depends_on or [],
        }

    def graph(self, *nodes, max_concurrency=2):
        return {
            "version": 1, "workload": {"path": str(self.workload), "sha256": self.workload_sha},
            "requirements": ["R1"], "max_concurrency": max_concurrency,
            "tasks": list(nodes or [self.node("a")]),
        }

    def claim(self, graph, worker, task):
        return sdlc.scheduler(graph, self.state, worker, task=task, repo=self.repo)

    def result_proof(self, task, **changes):
        state = json.loads(self.state.read_text())
        proof = {
            "task_id": task, "workload_sha256": self.workload_sha,
            "head_sha": self.head, "result": "pass", "requirements": ["R1"],
            "checks": ["synthetic-structural-check"],
            "dependency_heads": state["tasks"][task].get("dependency_heads", {}),
            **changes,
        }
        path = self.reports / (task + "-result.json")
        path.write_text(json.dumps(proof))
        return path

    def finish(self, graph, worker, task, proof=None, head=None, outcome="done"):
        return sdlc.scheduler(
            graph, self.state, worker, task=task, outcome=outcome,
            head=head or self.head, proof=proof, repo=self.repo,
        )

    def freeze(self, requirements=None, check_kinds=None, artifact_kinds=None, evidence_plan=None):
        return sdlc.freeze(
            self.repo, self.workload, self.baseline, requirements or ["R1"],
            check_kinds if check_kinds is not None else ["bdd", "contract"],
            artifact_kinds if artifact_kinds is not None else [], evidence_plan=evidence_plan,
        )

    def artifact(self, path, requirements, kind="contract", side="after", **changes):
        artifact = self.reports / path
        artifact.write_text("synthetic retained " + path + "\n")
        return {
            "path": path, "sha256": sdlc.digest(artifact.read_bytes()),
            "kind": kind, "requirements": requirements, "side": side,
            "revision": self.frozen["git_base_sha"] if side == "before" else self.head,
            "capture_command": "synthetic structural fixture",
            "environment": {"fixture": "stable"}, **changes,
        }

    def manifest(self, requirements=None, evidence_plan=None):
        requirements = requirements or ["R1"]
        self.frozen = self.freeze(requirements=requirements, evidence_plan=evidence_plan)
        (self.repo / "src/a/app.py").write_text("candidate behavior\n")
        self.git("add", ".")
        self.git("commit", "-qm", "candidate")
        self.head = self.git("rev-parse", "HEAD")
        contract = self.artifact("contract.json", requirements)
        checks = [
            {"id": "bdd", "kind": "bdd"},
            {"id": "consumer", "kind": "contract", "role": "consumer",
             "contract_sha256": contract["sha256"], "contract_artifact": contract["path"]},
            {"id": "provider", "kind": "contract", "role": "provider", "real_provider": True,
             "contract_sha256": contract["sha256"], "contract_artifact": contract["path"]},
        ]
        for check in checks:
            check.update(head_sha=self.head, result="pass", command="synthetic check " + check["id"],
                         requirements=requirements.copy())
        return {
            "workload_sha256": self.workload_sha, "head_sha": self.head,
            "implementation_owner": "implementer", "checks": checks, "artifacts": [contract],
            "compliance": [
                {"requirement": requirement, "verdict": "pass", "rationale": "Synthetic structural proof",
                 "checks": ["bdd", "consumer", "provider"], "evidence": ["contract.json"]}
                for requirement in requirements
            ],
            "review": {"reviewer": "independent-reviewer", "verdict": "approve",
                       "requirements_complete": True, "head_sha": self.head,
                       "workload_sha256": self.workload_sha},
        }

    def save_manifest(self, manifest, seal=True):
        if seal:
            manifest["review"]["evidence_sha256"] = sdlc.review_digest(manifest)
        self.manifest_path.write_text(json.dumps(manifest))

    def gate(self, manifest, seal=True, merge=False):
        self.save_manifest(manifest, seal=seal)
        return sdlc.gate(self.repo, self.baseline, self.manifest_path, merge=merge)

    def screenshot_pair(self, manifest, requirement, comparison_id):
        environment = {
            "viewport": {"width": 800, "height": 600}, "device_scale": 1,
            "theme": "light", "state": "loaded", "fixture": "stable",
        }
        pair = [
            self.artifact(
                f"{requirement}-{side}.png", [requirement], kind="screenshot", side=side,
                comparison_id=comparison_id, environment=copy.deepcopy(environment),
            )
            for side in ("before", "after")
        ]
        manifest["artifacts"].extend(pair)
        row = next(row for row in manifest["compliance"] if row["requirement"] == requirement)
        row["evidence"].extend(artifact["path"] for artifact in pair)
        return pair

    def test_freeze_preserves_initial_bytes_and_rejects_policy_changes(self):
        plan = {"R1": {"check_kinds": ["bdd"], "artifact_kinds": ["har"]}}
        original = self.freeze(evidence_plan=plan)
        retained = (self.baseline / "initial-workload.md").read_bytes()
        self.assertEqual(self.freeze(evidence_plan=plan), original)
        self.assertEqual(original["evidence_plan"], plan)
        changed = {"R1": {"check_kinds": ["bdd"], "artifact_kinds": []}}
        with self.assertRaises(ValueError):
            self.freeze(evidence_plan=changed)
        self.workload.write_text("A replacement workload\n")
        with self.assertRaises(ValueError):
            self.freeze(evidence_plan=plan)
        self.assertEqual((self.baseline / "initial-workload.md").read_bytes(), retained)

    def test_graph_rejects_path_aliases_and_partially_matching_globs(self):
        for left, right in (
            ("src/x", "./src/x"), ("src/x", "src//x"),
            ("src/foo*.py", "src/foobar.py"), ("src/a/", "src/a/module.py"),
        ):
            with self.subTest(left=left, right=right), self.assertRaises(ValueError):
                sdlc.validate_graph(self.graph(self.node("a", [left]), self.node("b", [right])))

    def test_graph_allows_overlapping_writers_only_after_a_dependency(self):
        graph = self.graph(self.node("a", ["src/shared"]), self.node("b", ["src/shared"], ["a"]))
        self.assertEqual(set(sdlc.validate_graph(graph)), {"a", "b"})
        graph["tasks"][0]["depends_on"] = ["b"]
        with self.assertRaises(ValueError):
            sdlc.validate_graph(graph)

    def test_graph_rejects_invalid_dependency_branch_and_capacity(self):
        base = self.graph(self.node("a"), self.node("b"))
        variants = []
        duplicate = copy.deepcopy(base)
        duplicate["tasks"][1]["branch"] = duplicate["tasks"][0]["branch"]
        variants.append(duplicate)
        missing = copy.deepcopy(base)
        missing["tasks"][1]["depends_on"] = ["missing"]
        variants.append(missing)
        for limit in (0, True, "2"):
            invalid = copy.deepcopy(base)
            invalid["max_concurrency"] = limit
            variants.append(invalid)
        for invalid in variants:
            with self.subTest(graph=invalid), self.assertRaises(ValueError):
                sdlc.validate_graph(invalid)

    def test_malformed_graph_records_are_rejected_cleanly(self):
        invalid_node = self.graph()
        invalid_node["tasks"] = [True]
        invalid_workload = self.graph()
        invalid_workload["workload"] = []
        for invalid in (None, [], invalid_node, invalid_workload):
            with self.subTest(graph=invalid), self.assertRaises(ValueError):
                sdlc.validate_graph(invalid)

    def test_concurrent_claims_grant_one_exclusive_task_lease(self):
        graph = self.graph()
        barrier = threading.Barrier(6)

        def compete(index):
            barrier.wait()
            try:
                return self.claim(graph, "worker-" + str(index), "a")
            except ValueError as error:
                self.assertIn("busy", str(error).lower())
                return {"task": None}

        with ThreadPoolExecutor(max_workers=6) as workers:
            results = list(workers.map(compete, range(6)))
        self.assertEqual(sum(result["task"] == "a" for result in results), 1)
        self.assertEqual(set(json.loads(self.state.read_text())["tasks"]), {"a"})

    def test_scheduler_limits_frontier_and_preserves_owner_exclusivity(self):
        graph = self.graph(self.node("a"), self.node("b"), self.node("c"))
        self.assertEqual(self.claim(graph, "worker-a", "a")["task"], "a")
        self.assertEqual(self.claim(graph, "worker-b", "b")["task"], "b")
        self.assertIsNone(self.claim(graph, "worker-c", "c")["task"])
        with self.assertRaises(ValueError):
            self.finish(graph, "different-worker", "a", outcome="retry")
        self.finish(graph, "worker-a", "a", outcome="blocked")
        self.assertEqual(self.claim(graph, "worker-c", "c")["task"], "c")

    def test_dependency_dispatch_records_accepted_input_heads(self):
        graph = self.graph(self.node("a"), self.node("b", depends_on=["a"]))
        self.assertIsNone(self.claim(graph, "worker-b", "b")["task"])
        self.claim(graph, "worker-a", "a")
        self.git("branch", "task/a", self.head)
        self.finish(graph, "worker-a", "a", proof=self.result_proof("a"))
        self.assertEqual(self.claim(graph, "worker-b", "b")["task"], "b")
        record = json.loads(self.state.read_text())["tasks"]["b"]
        self.assertEqual(record["dependency_heads"], {"a": self.head})

    def test_completion_rejects_unrelated_reports_and_nonexistent_heads(self):
        graph = self.graph()
        self.claim(graph, "worker", "a")
        self.git("branch", "task/a", self.head)
        text_proof = self.reports / "unrelated.txt"
        text_proof.write_text("An old report from a different task")
        with self.assertRaises(ValueError):
            self.finish(graph, "worker", "a", proof=text_proof)
        for changes in (
            {"task_id": "different"}, {"workload_sha256": "0" * 64},
            {"head_sha": "0" * 40}, {"result": "fail"}, {"requirements": []},
            {"checks": []}, {"dependency_heads": {"unexpected": self.head}},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.finish(graph, "worker", "a", proof=self.result_proof("a", **changes))
        with self.assertRaises(ValueError):
            self.finish(graph, "worker", "a", proof=self.result_proof("a"), head="0" * 40)

    def test_completion_rejects_commits_outside_task_ownership(self):
        graph = self.graph()
        self.claim(graph, "worker", "a")
        self.git("checkout", "-qb", "task/a")
        (self.repo / "src/b/app.py").write_text("outside the assigned atom\n")
        self.git("add", ".")
        self.git("commit", "-qm", "unowned change")
        self.head = self.git("rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "outside its declared ownership"):
            self.finish(graph, "worker", "a", proof=self.result_proof("a"))
        self.assertEqual(json.loads(self.state.read_text())["tasks"]["a"]["status"], "running")

    def test_completion_rejects_inputs_that_move_during_work(self):
        graph = self.graph(self.node("a"), self.node("b", depends_on=["a"]))
        self.claim(graph, "worker-a", "a")
        self.git("branch", "task/a", self.head)
        self.finish(graph, "worker-a", "a", proof=self.result_proof("a"))
        self.claim(graph, "worker-b", "b")
        self.git("branch", "task/b", self.head)
        proof = self.result_proof("b")
        (self.repo / "src/a/app.py").write_text("new dependency behavior\n")
        self.git("add", ".")
        self.git("commit", "-qm", "input changed")
        self.git("branch", "-f", "task/a", "HEAD")
        with self.assertRaisesRegex(ValueError, "input moved after its lease"):
            self.finish(graph, "worker-b", "b", proof=proof)

    def test_completion_checks_both_sides_of_a_rename(self):
        graph = self.graph()
        self.claim(graph, "worker", "a")
        self.git("checkout", "-qb", "task/a")
        self.git("mv", "src/b/app.py", "src/a/stolen.py")
        self.git("commit", "-qm", "rename from unowned path")
        self.head = self.git("rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "outside its declared ownership"):
            self.finish(graph, "worker", "a", proof=self.result_proof("a"))

    def test_ownership_preserves_literal_filename_whitespace(self):
        graph = self.graph()
        self.claim(graph, "worker", "a")
        self.git("checkout", "-qb", "task/a")
        outside = self.repo / " src/a/stolen.py"
        outside.parent.mkdir(parents=True)
        outside.write_text("a different top-level directory\n")
        self.git("add", ".")
        self.git("commit", "-qm", "unowned whitespace path")
        self.head = self.git("rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "outside its declared ownership"):
            self.finish(graph, "worker", "a", proof=self.result_proof("a"))

    def test_exclusive_repository_ownership_allows_root_level_changes(self):
        graph = self.graph(self.node("a", paths=["."]))
        self.claim(graph, "worker", "a")
        self.git("checkout", "-qb", "task/a")
        (self.repo / "root.txt").write_text("accepted repository-owned change\n")
        self.git("add", ".")
        self.git("commit", "-qm", "root change")
        self.head = self.git("rev-parse", "HEAD")
        result = self.finish(graph, "worker", "a", proof=self.result_proof("a"))
        self.assertEqual(result["status"], "done")

    def test_recompleted_ancestor_invalidates_done_descendants_until_reverified(self):
        graph = self.graph(self.node("a"), self.node("b", depends_on=["a"]),
                           self.node("c", depends_on=["b"]))
        graph["tasks"][1]["base_ref"] = "task/a"
        for identity in ("a", "b"):
            self.claim(graph, "worker-" + identity, identity)
            self.git("branch", "task/" + identity, self.head)
            self.finish(graph, "worker-" + identity, identity, proof=self.result_proof(identity))
        old_head = self.head
        self.finish(graph, "worker-a", "a", outcome="retry")
        self.claim(graph, "worker-a", "a")
        (self.repo / "src/a/app.py").write_text("updated upstream behavior\n")
        self.git("add", ".")
        self.git("commit", "-qm", "changed ancestor")
        self.head = self.git("rev-parse", "HEAD")
        self.git("branch", "-f", "task/a", self.head)
        self.finish(graph, "worker-a", "a", proof=self.result_proof("a"))
        stale = self.claim(graph, "worker-c", "c")
        self.assertIsNone(stale["task"])
        self.assertIn("b", stale["stale_tasks"])
        self.assertNotEqual(old_head, self.head)
        self.finish(graph, "worker-b", "b", outcome="retry")
        self.claim(graph, "worker-b", "b")
        self.git("branch", "-f", "task/b", self.head)
        self.finish(graph, "worker-b", "b", proof=self.result_proof("b"))
        self.assertEqual(self.claim(graph, "worker-c", "c")["task"], "c")

    def test_reaccepted_same_head_proof_invalidates_running_and_done_descendants(self):
        graph = self.graph(self.node("a"), self.node("b", depends_on=["a"]),
                           self.node("c", depends_on=["a"]), self.node("d", depends_on=["b"]))
        for identity in ("a", "b"):
            self.claim(graph, "worker-" + identity, identity)
            self.git("branch", "task/" + identity, self.head)
            self.finish(graph, "worker-" + identity, identity, proof=self.result_proof(identity))
        self.claim(graph, "worker-c", "c")
        self.git("branch", "task/c", self.head)
        c_proof = self.result_proof("c")
        self.finish(graph, "worker-a", "a", outcome="retry")
        self.claim(graph, "worker-a", "a")
        self.finish(graph, "worker-a", "a", proof=self.result_proof("a", checks=["replacement-proof"]))
        self.assertIsNone(self.claim(graph, "worker-d", "d")["task"])
        with self.assertRaisesRegex(ValueError, "input proof was invalidated"):
            self.finish(graph, "worker-c", "c", proof=c_proof)

    def test_transitive_pr_parent_is_pinned_separately_from_direct_inputs(self):
        nodes = [self.node("a"), self.node("b", depends_on=["a"]),
                 self.node("c", depends_on=["b"])]
        nodes[2]["pr_parent"] = "a"
        graph = self.graph(*nodes)
        for identity in ("a", "b"):
            self.claim(graph, "worker-" + identity, identity)
            self.git("branch", "task/" + identity, self.head)
            self.finish(graph, "worker-" + identity, identity, proof=self.result_proof(identity))
        claimed = self.claim(graph, "worker-c", "c")
        self.assertEqual(claimed["dependency_heads"], {"a": self.head, "b": self.head})
        self.git("branch", "task/c", self.head)
        self.finish(graph, "worker-c", "c", proof=self.result_proof("c"))

    def test_changed_completion_proof_blocks_downstream_dispatch(self):
        graph = self.graph(self.node("a"), self.node("b", depends_on=["a"]))
        self.claim(graph, "worker-a", "a")
        self.git("branch", "task/a", self.head)
        proof = self.result_proof("a")
        self.finish(graph, "worker-a", "a", proof=proof)
        proof.write_text("A replacement report")
        with self.assertRaises(ValueError):
            self.claim(graph, "worker-b", "b")

    def test_leased_task_definitions_cannot_change_silently(self):
        graph = self.graph()
        self.claim(graph, "worker", "a")
        graph["tasks"][0]["acceptance"] = ["A weakened acceptance condition"]
        with self.assertRaises(ValueError):
            self.finish(graph, "worker", "a", outcome="blocked")
        self.finish(graph, "worker", "a", outcome="retry")
        self.assertNotIn("a", json.loads(self.state.read_text())["tasks"])

    def test_sparse_worktrees_have_separate_indexes_patterns_and_mutable_files(self):
        external = self.root / "worktrees"
        with patch.object(sdlc, "cow_method", return_value=None):
            first = sdlc.worktree(self.repo, external, "isolated/a", self.head, ["src/a"], seed=self.repo)
            second = sdlc.worktree(self.repo, external, "isolated/b", self.head, ["src/b"], seed=self.repo)
        first_path, second_path = Path(first["path"]), Path(second["path"])
        self.assertFalse(first["cow"])
        self.assertTrue((first_path / "src/a/app.py").is_file())
        self.assertFalse((first_path / "src/b/app.py").exists())
        self.assertTrue((second_path / "src/b/app.py").is_file())
        self.assertFalse((second_path / "src/a/app.py").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")
        indexes = {self.git("rev-parse", "--path-format=absolute", "--git-path", "index", repo=repo)
                   for repo in (self.repo, first_path, second_path)}
        self.assertEqual(len(indexes), 3)
        sparse_files = [Path(self.git("rev-parse", "--path-format=absolute", "--git-path", "info/sparse-checkout", repo=repo))
                        for repo in (first_path, second_path)]
        self.assertNotEqual(sparse_files[0], sparse_files[1])
        self.assertIn("src/a", sparse_files[0].read_text())
        self.assertIn("src/b", sparse_files[1].read_text())
        original = (second_path / "root.txt").read_text()
        (first_path / "root.txt").write_text("worker edit\n")
        (self.repo / "root.txt").write_text("source edit\n")
        self.assertEqual((first_path / "root.txt").read_text(), "worker edit\n")
        self.assertEqual((self.repo / "root.txt").read_text(), "source edit\n")
        self.assertEqual((second_path / "root.txt").read_text(), original)
        self.assertEqual(first["environment"]["npm_config_cache"], second["environment"]["npm_config_cache"])
        self.assertNotEqual(first["environment"]["CARGO_TARGET_DIR"], second["environment"]["CARGO_TARGET_DIR"])

    def test_required_cow_failure_does_not_create_a_branch(self):
        with patch.object(sdlc, "cow_method", return_value=None), self.assertRaises(ValueError):
            sdlc.worktree(self.repo, self.root / "worktrees", "strict-cow", self.head,
                          ["src/a"], seed=self.repo, require_cow=True)
        self.assertFalse(self.branch_exists("strict-cow"))
        self.assertEqual(len(self.git("worktree", "list", "--porcelain").split("worktree ")) - 1, 1)

    def test_worktree_and_cache_paths_cannot_be_inside_existing_checkouts(self):
        for index, (repo, root, cache) in enumerate((
            (self.repo, self.repo / "nested", None),
            (self.repo / "src/a", self.repo / "nested-subdir", None),
            (self.repo, self.root / "external", self.repo / "cache"),
        )):
            branch = "unsafe-" + str(index)
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                sdlc.worktree(repo, root, branch, self.head, ["src/a"], cache_root=cache)
            self.assertFalse(self.branch_exists(branch))
        safe = sdlc.worktree(self.repo, self.root / "safe", "safe", self.head, ["src/a"])
        with self.assertRaises(ValueError):
            sdlc.worktree(self.repo, Path(safe["path"]) / "nested", "nested-worker", self.head, ["src/a"])
        self.assertFalse(self.branch_exists("nested-worker"))

    def test_default_cache_symlink_cannot_redirect_into_source(self):
        external = self.root / "worktrees"
        external.mkdir()
        (external / ".shared-cache").symlink_to(self.repo / "src/a", target_is_directory=True)
        with self.assertRaises(ValueError):
            sdlc.worktree(self.repo, external, "cache-link", self.head, ["src/a"])
        self.assertFalse(self.branch_exists("cache-link"))
        self.assertEqual(self.git("status", "--porcelain"), "")

    @unittest.skipUnless(shutil.which("cp"), "copy command unavailable")
    def test_copy_staging_never_follows_a_tracked_temporary_name_symlink(self):
        checkout = self.root / "checkout"
        checkout.mkdir()
        source = self.root / "seed-file"
        source.write_text("seed contents\n")
        destination = checkout / "a"
        destination.write_text("original checkout\n")
        destination.chmod(0o755)
        victim = self.root / "unrelated-source-file"
        victim.write_text("must survive\n")
        collision = checkout / "a.sdlc-reflink"
        collision.symlink_to(victim)
        sdlc._reflink_copy(source, destination, [shutil.which("cp")])
        self.assertEqual(destination.read_text(), source.read_text())
        self.assertEqual(destination.stat().st_mode & 0o777, 0o755)
        self.assertEqual(victim.read_text(), "must survive\n")
        self.assertTrue(collision.is_symlink())
        self.assertEqual(set(checkout.iterdir()), {destination, collision})

    def test_gate_accepts_complete_current_head_structural_evidence(self):
        result = self.gate(self.manifest())
        self.assertEqual(result["structural_gate"], "pass")
        self.assertEqual(result["head_sha"], self.head)

    def test_gate_rejects_consumer_only_proof_for_one_requirement(self):
        manifest = self.manifest(requirements=["R1", "R2"])
        manifest["checks"][2]["requirements"] = ["R1"]
        manifest["compliance"][1]["checks"] = ["bdd", "consumer"]
        with self.assertRaises(ValueError):
            self.gate(manifest)

    def test_gate_rejects_contract_versions_that_have_no_matching_counterpart(self):
        manifest = self.manifest()
        other = self.artifact("different-contract.json", ["R1"])
        manifest["artifacts"].append(other)
        manifest["checks"][2].update(contract_sha256=other["sha256"], contract_artifact=other["path"])
        with self.assertRaises(ValueError):
            self.gate(manifest)

    def test_gate_rejects_stub_provider_and_unretained_contract(self):
        manifest = self.manifest()
        for changes in ({"real_provider": False}, {"contract_artifact": "missing.json"}):
            invalid = copy.deepcopy(manifest)
            invalid["checks"][2].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.gate(invalid)

    def test_visual_evidence_is_required_for_each_applicable_requirement(self):
        policy = {requirement: {"check_kinds": ["bdd", "contract"], "artifact_kinds": ["screenshot"]}
                  for requirement in ("R1", "R2")}
        manifest = self.manifest(requirements=["R1", "R2"], evidence_plan=policy)
        self.screenshot_pair(manifest, "R1", "first-page")
        with self.assertRaises(ValueError):
            self.gate(manifest)
        self.screenshot_pair(manifest, "R2", "second-page")
        self.assertEqual(self.gate(manifest)["structural_gate"], "pass")

    def test_visual_pair_must_match_viewport_comparison_and_required_references(self):
        policy = {"R1": {"check_kinds": ["bdd", "contract"], "artifact_kinds": ["screenshot"]}}
        manifest = self.manifest(evidence_plan=policy)
        self.screenshot_pair(manifest, "R1", "page")
        self.assertEqual(self.gate(manifest)["structural_gate"], "pass")
        variants = []
        viewport = copy.deepcopy(manifest)
        viewport["artifacts"][-1]["environment"]["viewport"]["width"] = 1200
        variants.append(viewport)
        comparison = copy.deepcopy(manifest)
        comparison["artifacts"][-1]["comparison_id"] = "different-page"
        variants.append(comparison)
        unreferenced = copy.deepcopy(manifest)
        unreferenced["compliance"][0]["evidence"].remove("R1-after.png")
        variants.append(unreferenced)
        for invalid in variants:
            with self.subTest(artifacts=invalid["artifacts"]), self.assertRaises(ValueError):
                self.gate(invalid)

    def test_gate_rejects_changed_artifact_bytes_and_stale_candidate_heads(self):
        manifest = self.manifest()
        self.assertEqual(self.gate(manifest)["structural_gate"], "pass")
        stale = copy.deepcopy(manifest)
        stale["checks"][0]["head_sha"] = self.frozen["git_base_sha"]
        with self.assertRaises(ValueError):
            self.gate(stale)
        (self.reports / "contract.json").write_text("different report\n")
        with self.assertRaises(ValueError):
            self.gate(manifest)

    def test_gate_rejects_mutation_of_the_frozen_workload(self):
        manifest = self.manifest()
        (self.baseline / "initial-workload.md").write_text("A reduced workload")
        with self.assertRaises(ValueError):
            self.gate(manifest)

    def test_review_must_have_a_distinct_text_identity(self):
        manifest = self.manifest()
        for reviewer in (True, ["reviewer"], {"name": "reviewer"}, "", "implementer"):
            invalid = copy.deepcopy(manifest)
            invalid["review"]["reviewer"] = reviewer
            with self.subTest(reviewer=reviewer), self.assertRaises(ValueError):
                self.gate(invalid)

    def test_review_approval_expires_when_same_head_evidence_changes(self):
        manifest = self.manifest()
        self.assertEqual(self.gate(manifest)["structural_gate"], "pass")
        manifest["checks"][0]["command"] = "a different behavior check"
        with self.assertRaises(ValueError):
            self.gate(manifest, seal=False)

    def test_merge_gate_requires_current_ci_comments_and_dependencies(self):
        manifest = self.manifest()
        manifest["pr"] = {
            "head_sha": self.head, "checks_green": True, "comments_complete": True,
            "approvals_current": True, "dependencies_merged": True, "mergeable": True,
            "comments": [{"status": "answered", "resolution": "Question answered with retained evidence"}],
        }
        self.assertEqual(self.gate(manifest, merge=True)["structural_gate"], "pass")
        for field in ("checks_green", "comments_complete", "approvals_current", "dependencies_merged", "mergeable"):
            invalid = copy.deepcopy(manifest)
            invalid["pr"][field] = False
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.gate(invalid, merge=True)
        manifest["pr"]["comments"][0]["status"] = "open"
        with self.assertRaises(ValueError):
            self.gate(manifest, merge=True)


if __name__ == "__main__":
    unittest.main()
