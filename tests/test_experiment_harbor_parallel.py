"""Parallel Harbor controller tests using executable, non-network fake trials."""
import json
from pathlib import Path
import unittest

import test_experiment_harbor_integration as fixtures


class HarborParallelTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.HarborControllerIntegrationTests(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.call = self.fixture.call
        self.root = self.fixture.root

    def test_parallel_harbor_trials_overlap_and_compare_frozen_evidence(self):
        # A process-level rendezvous fails if the two Harbor subprocesses are
        # accidentally run in sequence. Version probes are deliberately skipped.
        barrier = self.fixture.dir / "barrier"
        barrier.mkdir()
        marker = "config=json.loads(pathlib.Path(sys.argv[-1]).read_text())"
        rendezvous = f'''import time
barrier=pathlib.Path({str(barrier)!r})
key=pathlib.Path(sys.argv[-1]).parent.name
(barrier/key).write_text('ready')
deadline=time.monotonic()+8
while len(list(barrier.iterdir())) < 2:
    if time.monotonic() > deadline: raise RuntimeError('trials did not overlap')
    time.sleep(0.01)
'''
        self.fixture.bin.write_text(fixtures.FAKE.replace(marker, rendezvous + marker))
        self.fixture.bin.chmod(0o755)
        self.fixture.backend["harbor_bin_sha256"] = self.fixture.sha(self.fixture.bin)
        self.fixture.init()
        self.fixture.freeze()
        batch = self.call("parallel", batch="search", max_workers=2, trials=[
            {"side":"baseline", "case":"sel", "rep":0, "run_key":"old"},
            {"side":"candidate", "arm":"fix", "case":"sel", "rep":0, "run_key":"new"},
        ])
        self.assertEqual(batch["status"], "complete", batch)
        self.assertEqual([item["run_key"] for item in batch["trials"]], ["old", "new"])
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 2)
        self.assertEqual(self.call("compare", arm="fix", baseline=["old"], candidate=["new"],
                                   decision="pick")["decision"], "eligible")
        # A retained Harbor receipt is rechecked, including in batch-created runs.
        record = json.loads((self.root / "runs/old.json").read_text())
        Path(record["result"]["harbor"]["artifact_manifest"]).write_text("[]")
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            self.call("compare", arm="fix", baseline=["old"], candidate=["new"], decision="tampered")

    def test_unknown_harbor_batch_remains_charged_without_fallback(self):
        self.fixture.bin.write_text("#!/bin/sh\nif [ \\\"$1\\\" = --version ]; then echo 0.26.0; exit 0; fi\nexit 9\n".replace('\\\"', '"'))
        self.fixture.bin.chmod(0o755)
        self.fixture.backend["harbor_bin_sha256"] = self.fixture.sha(self.fixture.bin)
        self.fixture.init()
        self.fixture.freeze()
        batch = self.call("parallel", batch="failed", max_workers=2, trials=[
            {"side":"baseline", "case":"sel", "rep":0, "run_key":"old"},
            {"side":"candidate", "arm":"fix", "case":"sel", "rep":0, "run_key":"new"},
        ])
        self.assertEqual(batch["status"], "partial")
        self.assertTrue(all(item["result"]["status"] == "unknown" for item in batch["trials"]))
        ledger = self.call("status")["ledger"]
        self.assertEqual(ledger["reserved_trials"], 2)
        self.assertEqual({row["status"] for row in ledger["runs"]}, {"uncertain"})
        self.assertEqual(self.call("parallel-recover", batch="failed")["released"], [])


if __name__ == "__main__":
    unittest.main()
