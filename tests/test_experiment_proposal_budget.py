"""Atomic limits on proposal requests, independent of trial start budgets."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/hill-climb/scripts"))
from experiment_ledger import Ledger


class ProposalBudgetTests(unittest.TestCase):
    def test_concurrent_proposals_claim_last_slot_once_and_trial_budget_is_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ledger.sqlite3"
            ledger = Ledger(db)
            ledger.initialize("e", max_trials=1, max_tokens=100)
            ledger.configure_proposals("e", max_proposals=1)
            def claim(index):
                try:
                    return Ledger(db).reserve("e", f"proposal-{index}", tokens=10,
                                              trial_units=0, proposal=True)
                except ValueError:
                    return None
            with ThreadPoolExecutor(max_workers=8) as pool:
                claimed = [x for x in pool.map(claim, range(8)) if x]
            self.assertEqual(len(claimed), 1)
            state = Ledger(db).status("e")
            self.assertEqual((state["max_proposals"], state["proposal_count"]), (1, 1))
            self.assertEqual(state["reserved_trials"], 0)
            self.assertEqual(ledger.reserve("e", "trial", tokens=0)["status"], "reserved")
            duplicate = ledger.reserve("e", claimed[0]["run_key"], tokens=10,
                                       trial_units=0, proposal=True)
            self.assertEqual(duplicate, claimed[0])
            with self.assertRaisesRegex(ValueError, "limits"):
                ledger.configure_proposals("e", max_proposals=2)
            with self.assertRaisesRegex(ValueError, "different"):
                ledger.reserve("e", claimed[0]["run_key"], tokens=10, trial_units=0)

    def test_cancelled_proposal_still_counts_toward_attempt_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger(Path(tmp) / "ledger.sqlite3")
            ledger.initialize("e", max_trials=1, max_tokens=0)
            ledger.configure_proposals("e", max_proposals=1)
            ledger.reserve("e", "first", tokens=0, trial_units=0, proposal=True)
            ledger.cancel("e", "first", reason="aborted before launch")
            with self.assertRaisesRegex(ValueError, "proposal budget"):
                ledger.reserve("e", "next", tokens=0, trial_units=0, proposal=True)
