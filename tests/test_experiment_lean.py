"""Actual ledger / Lean-oracle correspondence and mutation detection."""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/hill-climb/formal"))
from lean_bridge import BridgeMismatch, Ledger, check_reservations, check_settlements, oracle


class UnderaccountingMutant(Ledger):
    @staticmethod
    def _totals(rows):
        totals = Ledger._totals(rows)
        totals["reserved_tokens"] = 0
        return totals


class LeanLedgerBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lean = os.environ.get("LEAN_BIN")
        if not lean:
            raise unittest.SkipTest("set LEAN_BIN to run pinned Lean proof and ledger bridge")
        cls.rows = oracle(lean)

    def test_reservation_and_settlement_match_the_checked_definitions(self):
        self.assertEqual(175, check_reservations([r for r in self.rows if r[0] == "R"]))
        self.assertEqual(175, check_settlements([r for r in self.rows if r[0] == "S"]))

    def test_unproved_theorem_is_rejected(self):
        import tempfile
        from unittest.mock import patch
        import lean_bridge
        with tempfile.TemporaryDirectory() as temporary:
            weakened = Path(temporary) / "Budget.lean"
            source = lean_bridge.PROOF.read_text()
            self.assertIn("    omega", source)
            weakened.write_text(source.replace("    omega", "    sorry", 1))
            with patch.object(lean_bridge, "PROOF", weakened):
                with self.assertRaisesRegex(ValueError, "warning|axiom"):
                    oracle(os.environ["LEAN_BIN"])

    def test_axiom_in_place_of_proof_is_rejected(self):
        import tempfile
        from unittest.mock import patch
        import lean_bridge
        with tempfile.TemporaryDirectory() as temporary:
            weakened = Path(temporary) / "Budget.lean"
            source = lean_bridge.PROOF.read_text()
            begin = source.index("theorem reservation_preserves")
            end = source.index("theorem bounded_settlement_preserves")
            replacement = ("axiom reservation_preserves (s next : Budget) (amount : Nat)\n"
                           "    (h : reserve s amount = some next) : withinLimit next\n\n")
            weakened.write_text(source[:begin] + replacement + source[end:])
            with patch.object(lean_bridge, "PROOF", weakened):
                with self.assertRaisesRegex(ValueError, "axiom"):
                    oracle(os.environ["LEAN_BIN"])

    def test_underaccounting_mutant_is_detected(self):
        case = ("R", 1, 1, 0, 1, 0)
        self.assertIn(case, self.rows)
        with self.assertRaises(BridgeMismatch):
            check_reservations([case], ledger_type=UnderaccountingMutant)
