"""Actual ledger / Lean-oracle correspondence and mutation detection."""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/hill-climb/formal"))
from lean_bridge import BridgeMismatch, Ledger, check_launch_policy, check_proposals, check_reservations, check_settlements, oracle


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

    def test_launch_policy_matches_checked_truth_table_and_detects_mutations(self):
        cases = [r for r in self.rows if r[0] == "L"]
        self.assertEqual(4, check_launch_policy(cases))
        with self.assertRaises(BridgeMismatch):
            check_launch_policy(cases, policy=lambda registered, cancelled: not cancelled)
        with self.assertRaises(BridgeMismatch):
            check_launch_policy(cases, policy=lambda registered, cancelled: registered)

    @unittest.skipUnless(os.name == "posix", "staged POSIX launch protocol")
    def test_real_staged_launch_consults_checked_gate(self):
        import tempfile
        from unittest.mock import patch
        import experiment_runner as runner
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "target-ran"
            argv = [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"]
            # The target may run only when the registered process is admitted.
            with runner.cancellation_scope(), patch.object(
                    runner, "launch_permitted", wraps=runner.launch_permitted) as policy:
                result = runner._execute(argv, root, root, 5, 4096, root)
            self.assertEqual(result["status"], "passed")
            self.assertTrue(marker.exists())
            policy.assert_called_once_with(True, False)
            marker.unlink()
            # Denying the pure gate on the actual execution path must withhold
            # the pipe permit even though the rest of the launch proceeds.
            with runner.cancellation_scope(), patch.object(
                    runner, "launch_permitted", return_value=False) as policy:
                runner._execute(argv, root, root, 5, 4096, root)
            policy.assert_called_once_with(True, False)
            self.assertFalse(marker.exists())
            # Pre-cancel exercises the actual registered/cancelled branch.
            with runner.cancellation_scope():
                runner.cancel_active_trials()
                with patch.object(runner, "launch_permitted", wraps=runner.launch_permitted) as policy:
                    runner._execute(argv, root, root, 5, 4096, root)
                policy.assert_called_once_with(True, True)
            self.assertFalse(marker.exists())

    def test_host_and_scripted_proposals_match_the_checked_count_model(self):
        self.assertEqual(14, check_proposals([r for r in self.rows if r[0] == "P"]))

    def test_proposal_limit_mutation_is_detected(self):
        import importlib.util
        import tempfile
        source_path = ROOT / "skills/hill-climb/scripts/experiment_ledger.py"
        source = source_path.read_text()
        guard = 'if count >= limit["max_proposals"]:'
        self.assertEqual(source.count(guard), 1)
        with tempfile.TemporaryDirectory() as temporary:
            mutant_path = Path(temporary) / "mutant_ledger.py"
            mutant_path.write_text(source.replace(guard, 'if count > limit["max_proposals"]:'))
            spec = importlib.util.spec_from_file_location("mutant_ledger", mutant_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            case = ("P", 1, 1, 0, 1)
            self.assertIn(case, self.rows)
            with self.assertRaises(BridgeMismatch):
                check_proposals([case], ledger_type=module.Ledger)

    def test_proposal_proof_axiom_is_rejected(self):
        import tempfile
        from unittest.mock import patch
        import lean_bridge
        with tempfile.TemporaryDirectory() as temporary:
            weakened = Path(temporary) / "Budget.lean"
            source = lean_bridge.PROOF.read_text()
            begin = source.index("theorem proposal_trace_preserves")
            end = source.index("-- The parent decides")
            replacement = (
                "axiom proposal_trace_preserves (limit count final : Nat) (actions : List Bool)\n"
                "    (initial : count ≤ limit) (result : proposalTrace limit count actions = some final) : final ≤ limit\n\n"
            )
            weakened.write_text(source[:begin] + replacement + source[end:])
            with patch.object(lean_bridge, "PROOF", weakened):
                with self.assertRaisesRegex(ValueError, "axiom"):
                    oracle(os.environ["LEAN_BIN"])

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
