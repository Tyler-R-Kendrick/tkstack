import sys
import unittest
from pathlib import Path

FORMAL = Path(__file__).resolve().parents[1] / "skills" / "hill-climb" / "formal"
sys.path.insert(0, str(FORMAL))

from model_check import (
    BudgetState, PromotionState, budget_steps, check_budget, check_promotion,
    promotion_steps,
)


class ExperimentModelTests(unittest.TestCase):
    def test_atomic_budget_transition_preserves_budget_in_all_reachable_states(self):
        result = check_budget(atomic=True)
        self.assertGreater(result.states_explored, 1)
        self.assertIsNone(result.counterexample)

    def test_stale_budget_check_yields_counterexample(self):
        result = check_budget(atomic=False)
        self.assertIsNotNone(result.counterexample)
        self.assertEqual(
            ["worker 0 checks", "worker 1 checks", "worker 0 reserves", "worker 1 reserves"],
            result.counterexample,
        )

    def test_promotions_remain_evidence_bound_during_crash_and_external_moves(self):
        result = check_promotion()
        self.assertGreater(result.states_explored, 1)
        self.assertIsNone(result.counterexample)

    def test_unknown_dispatch_remains_charged_until_verified(self):
        state = BudgetState(("unknown", "idle"))
        self.assertEqual(state.charged, 1)
        self.assertNotIn("worker 1 checks", dict(budget_steps(state, atomic=True)))
        transitions = dict(budget_steps(state, atomic=True))
        self.assertEqual(transitions["worker 0 confirms no execution"].charged, 0)
        self.assertEqual(transitions["worker 0 reconciles usage"].charged, 1)

    def test_removing_promotion_guard_finds_aba_counterexample(self):
        result = check_promotion(guarded=False)
        self.assertEqual(
            ["record eligible intent", "external writes base", "write candidate ref"],
            result.counterexample,
        )

    def test_recovery_quarantines_an_intervening_ref_write(self):
        state = PromotionState(intent="pending", expected_ref="base",
                               expected_generation=0, up=False,
                               ref="base", generation=2, writer="external")
        actions = dict(promotion_steps(state, guarded=True))
        self.assertEqual(actions["quarantine ambiguous recovery"].intent, "quarantined")
        self.assertNotIn("recover and retry", actions)
        self.assertNotIn("recover committed write", actions)
