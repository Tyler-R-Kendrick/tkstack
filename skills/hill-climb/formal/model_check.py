"""Exhaust finite abstract state spaces for experiment controller invariants.

This is an independent specification model, not the controller implementation.
See README.md for bounds and the assumptions behind the promotion model.
"""

from collections import deque
from dataclasses import dataclass, replace
import json


@dataclass(frozen=True)
class Result:
    states_explored: int
    counterexample: list[str] | None


def explore(initial, transitions, invariant):
    """Breadth-first exploration returns a shortest invariant violation."""
    queue = deque([(initial, [])])
    seen = {initial}
    while queue:
        state, trace = queue.popleft()
        if not invariant(state):
            return Result(len(seen), trace)
        for action, successor in transitions(state):
            if successor not in seen:
                seen.add(successor)
                queue.append((successor, trace + [action]))
    return Result(len(seen), None)


@dataclass(frozen=True)
class BudgetState:
    # Two one-unit reservations compete for a single unit of capacity.
    workers: tuple[str, str] = ("idle", "idle")

    @property
    def charged(self):
        # A dispatched attempt with an unknown outcome is still charged.
        return sum(status in {"reserved", "dispatched", "unknown", "settled"}
                   for status in self.workers)


def with_worker(state, worker, status):
    workers = list(state.workers)
    workers[worker] = status
    return replace(state, workers=tuple(workers))


def budget_steps(state, atomic):
    for worker, status in enumerate(state.workers):
        if status == "idle" and state.charged < 1:
            yield f"worker {worker} checks", with_worker(state, worker, "checked")
        if status == "checked" and (not atomic or state.charged < 1):
            yield f"worker {worker} reserves", with_worker(state, worker, "reserved")
        if status == "reserved":
            yield f"worker {worker} dispatches", with_worker(state, worker, "dispatched")
            yield f"worker {worker} cancels before dispatch", with_worker(state, worker, "cancelled")
        if status == "dispatched":
            yield f"worker {worker} loses response", with_worker(state, worker, "unknown")
            yield f"worker {worker} settles", with_worker(state, worker, "settled")
        if status == "unknown":
            yield f"worker {worker} reconciles usage", with_worker(state, worker, "settled")
            yield f"worker {worker} confirms no execution", with_worker(state, worker, "cancelled")


def check_budget(atomic=True):
    return explore(BudgetState(), lambda state: budget_steps(state, atomic),
                   lambda state: state.charged <= 1)


@dataclass(frozen=True)
class PromotionState:
    ref: str = "base"
    generation: int = 0
    writer: str = "external"
    intent: str = "none"  # none, pending, committed or quarantined
    expected_ref: str | None = None
    expected_generation: int = -1
    # Records the pre-state of the one controller write, if it occurred.
    write_origin: tuple[str, int] | None = None
    up: bool = True


def promotion_steps(state, guarded):
    # Bound externally visible writes to three; allow ABA and same-value writes.
    if state.generation < 3:
        for ref in ("base", "other", "winner"):
            yield f"external writes {ref}", replace(
                state, ref=ref, generation=state.generation + 1, writer="external")
    if state.up and state.intent == "none" and state.ref == "base":
        yield "record eligible intent", replace(
            state, intent="pending", expected_ref=state.ref,
            expected_generation=state.generation)
    if state.up and state.intent == "pending" and state.write_origin is None:
        expected_matches = (state.ref == state.expected_ref
                            and state.generation == state.expected_generation)
        if state.generation < 3 and (not guarded or expected_matches):
            yield "write candidate ref", replace(
                state, ref="winner", generation=state.generation + 1,
                writer="controller", write_origin=(state.ref, state.generation))
    if state.up and state.intent == "pending" and state.write_origin is not None:
        if (state.writer == "controller" and state.ref == "winner"
                and state.generation == state.expected_generation + 1):
            yield "commit intent", replace(state, intent="committed")
    if state.up and state.intent == "pending":
        yield "crash", replace(state, up=False)
    if not state.up:
        unchanged = (state.write_origin is None
                     and state.ref == state.expected_ref
                     and state.generation == state.expected_generation)
        written = (state.write_origin is not None and state.writer == "controller"
                   and state.ref == "winner"
                   and state.generation == state.expected_generation + 1)
        if unchanged:
            yield "recover and retry", replace(state, up=True)
        elif written:
            yield "recover committed write", replace(state, up=True, intent="committed")
        else:
            yield "quarantine ambiguous recovery", replace(state, up=True, intent="quarantined")


def promotion_invariant(state):
    if state.write_origin is not None:
        return state.write_origin == (state.expected_ref, state.expected_generation)
    return state.intent != "committed"


def check_promotion(guarded=True):
    return explore(PromotionState(), lambda state: promotion_steps(state, guarded),
                   promotion_invariant)


def main():
    checks = {
        "atomic_budget": check_budget(),
        "stale_budget_counterexample": check_budget(atomic=False),
        "guarded_promotion": check_promotion(),
        "stale_promotion_counterexample": check_promotion(guarded=False),
    }
    print(json.dumps({name: {"states_explored": result.states_explored,
                            "counterexample": result.counterexample}
                      for name, result in checks.items()}, indent=2))
    return int(checks["atomic_budget"].counterexample is not None
               or checks["stale_budget_counterexample"].counterexample is None
               or checks["guarded_promotion"].counterexample is not None
               or checks["stale_promotion_counterexample"].counterexample is None)


if __name__ == "__main__":
    raise SystemExit(main())
