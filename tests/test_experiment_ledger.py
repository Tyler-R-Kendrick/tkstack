"""Contract tests for the durable, bounded experiment ledger."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/hill-climb/scripts"))
from experiment_ledger import Ledger


class ExperimentLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ledger.sqlite3"
        self.ledger = Ledger(self.path)
        self.ledger.initialize("task", max_trials=1, max_tokens=100)

    def test_competing_reservations_obey_atomic_limits(self):
        def reserve(number):
            try:
                return Ledger(self.path).reserve("task", f"run-{number}", tokens=60)
            except ValueError:
                return None

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(reserve, range(8)))
        accepted = [result for result in results if result]
        self.assertEqual(len(accepted), 1)
        status = self.ledger.status("task")
        self.assertEqual(status["reserved_tokens"], 60)
        self.assertEqual(status["reserved_trials"], 1)

    def test_retry_with_same_key_deduplicates_and_rejects_different_parameters(self):
        first = self.ledger.reserve("task", "same", tokens=40)
        self.assertEqual(first, self.ledger.reserve("task", "same", tokens=40))
        with self.assertRaisesRegex(ValueError, "different"):
            self.ledger.reserve("task", "same", tokens=41)
        self.assertEqual(self.ledger.status("task")["reserved_trials"], 1)

    def test_dispatch_uncertainty_survives_restart_and_requires_evidence_to_cancel(self):
        self.ledger.reserve("task", "one", tokens=80)
        self.ledger.dispatch("task", "one")
        self.ledger.uncertain("task", "one", "transport timeout")
        restarted = Ledger(self.path)
        self.assertEqual(restarted.status("task")["runs"][0]["status"], "uncertain")
        with self.assertRaisesRegex(ValueError, "evidence"):
            restarted.cancel("task", "one", reason="unknown")
        with self.assertRaisesRegex(ValueError, "budget"):
            restarted.reserve("task", "two", tokens=1)
        restarted.cancel("task", "one", reason="worker never accepted", non_execution_evidence="receipt-42")
        self.assertEqual(restarted.reserve("task", "two", tokens=100)["status"], "reserved")
        self.assertEqual(restarted.status("task")["events"][-2]["details"]["non_execution_evidence"], "receipt-42")

    def test_competing_dispatch_claims_grant_only_one_external_start(self):
        self.ledger.reserve("task", "one", tokens=10)
        with ThreadPoolExecutor(max_workers=8) as pool:
            claims = list(pool.map(lambda _: Ledger(self.path).dispatch("task", "one"), range(8)))
        self.assertEqual(sum(claim["dispatch_granted"] for claim in claims), 1)

    def test_settlement_is_idempotent_conflict_checked_and_conserves_budget(self):
        self.ledger.reserve("task", "one", tokens=80)
        self.ledger.dispatch("task", "one")
        first = self.ledger.settle("task", "one", actual_tokens=55)
        self.assertEqual(first, self.ledger.settle("task", "one", actual_tokens=55))
        with self.assertRaisesRegex(ValueError, "conflict"):
            self.ledger.settle("task", "one", actual_tokens=54)
        status = self.ledger.status("task")
        self.assertEqual((status["settled_tokens"], status["reserved_tokens"]), (55, 0))
        self.assertEqual((status["settled_trials"], status["reserved_trials"]), (1, 0))
        with self.assertRaisesRegex(ValueError, "budget"):
            self.ledger.reserve("task", "another", tokens=0)

    def test_provider_overrun_is_durable_and_prevents_further_reservations(self):
        self.ledger.reserve("task", "one", tokens=60, trial_units=0)
        self.ledger.reserve("task", "already-reserved", tokens=20)
        self.ledger.dispatch("task", "one")
        overrun = self.ledger.settle("task", "one", actual_tokens=80)
        self.assertEqual(overrun["status"], "overrun")
        status = Ledger(self.path).status("task")
        self.assertTrue(status["overrun"])
        self.assertEqual(status["settled_tokens"], 80)
        with self.assertRaisesRegex(ValueError, "overrun"):
            self.ledger.reserve("task", "another", tokens=1)
        with self.assertRaisesRegex(ValueError, "overrun"):
            self.ledger.dispatch("task", "already-reserved")

    def test_cancel_before_dispatch_releases_budget_without_trial(self):
        self.ledger.reserve("task", "one", tokens=50)
        self.ledger.cancel("task", "one", reason="never started")
        self.assertEqual(self.ledger.status("task")["reserved_tokens"], 0)
        self.assertEqual(self.ledger.reserve("task", "two", tokens=100)["status"], "reserved")

    def test_invalid_inputs_and_illegal_transitions_do_not_mutate(self):
        for tokens in (True, -1, 1.5, "5"):
            with self.subTest(tokens=tokens), self.assertRaises(ValueError):
                self.ledger.reserve("task", "bad", tokens=tokens)
        with self.assertRaises(ValueError):
            self.ledger.reserve("task", "", tokens=0)
        with self.assertRaises(ValueError):
            self.ledger.reserve("task", "bad", tokens=0, trial_units=True)
        self.ledger.reserve("task", "one", tokens=10)
        with self.assertRaisesRegex(ValueError, "dispatch"):
            self.ledger.settle("task", "one", actual_tokens=0)
        self.assertEqual(self.ledger.status("task")["runs"][0]["status"], "reserved")
        with self.assertRaisesRegex(ValueError, "limits"):
            self.ledger.initialize("task", max_trials=2, max_tokens=100)

    def test_aborted_transaction_does_not_leave_lock(self):
        connection = sqlite3.connect(self.path)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE experiments SET max_tokens=1 WHERE experiment='task'")
        connection.rollback()
        connection.close()
        self.assertEqual(self.ledger.reserve("task", "one", tokens=100)["status"], "reserved")


if __name__ == "__main__":
    unittest.main()
