"""Check Lean theorems and compare their executable oracle to the real ledger."""

import argparse
import collections
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

FORMAL = Path(__file__).resolve().parent
sys.path.insert(0, str(FORMAL.parent / "scripts"))
from experiment_ledger import Ledger

PROOF = FORMAL / "Budget.lean"
THEOREMS = (
    "ExperimentBudget.reservation_preserves",
    "ExperimentBudget.bounded_settlement_preserves",
    "ExperimentBudget.overrun_blocks_reservation",
)
ALLOWED_KERNEL_AXIOMS = {"propext", "Quot.sound", "Classical.choice"}


class BridgeMismatch(AssertionError):
    pass


def oracle(lean):
    lean = str(Path(lean).resolve(strict=True))
    version = subprocess.run([lean, "--version"], check=True, capture_output=True, text=True).stdout
    if "version 4.19.0" not in version or "commit 6caaee842e94" not in version:
        raise ValueError("Lean must be the pinned 4.19.0 release")
    with tempfile.TemporaryDirectory(prefix="lean-budget-") as temporary:
        root = Path(temporary)
        compiled = subprocess.run([lean, "-o", str(root / "Budget.olean"), str(PROOF)],
                                  text=True, capture_output=True, check=True, cwd=PROOF.parent)
        if compiled.stdout.strip() or compiled.stderr.strip():
            raise ValueError("Lean reported a warning or unexpected compiler output")
        audit = root / "Audit.lean"
        audit.write_text("import Budget\n" + "".join(f"#print axioms {name}\n" for name in THEOREMS))
        env = {**os.environ, "LEAN_PATH": str(root)}
        checked = subprocess.run([lean, str(audit)], text=True, capture_output=True,
                                 check=True, env=env)
        if checked.stderr.strip():
            raise ValueError("Lean axiom audit reported an error")
        lines = checked.stdout.strip().splitlines()
        if len(lines) != len(THEOREMS):
            raise ValueError("Lean axiom audit did not report all theorems")
        for name, line in zip(THEOREMS, lines):
            match = re.fullmatch(r"'([^']+)' depends on axioms: \[(.*)\]", line)
            if not match or match.group(1) != name:
                raise ValueError(f"Unexpected Lean axiom audit: {line}")
            axioms = {part.strip() for part in match.group(2).split(",") if part.strip()}
            if not axioms <= ALLOWED_KERNEL_AXIOMS:
                raise ValueError(f"Unexpected axiom in {name}: {sorted(axioms)}")
        evaluated = subprocess.run([lean, "--run", str(PROOF)], text=True,
                                   capture_output=True, check=True, cwd=PROOF.parent)
        if evaluated.stderr.strip():
            raise ValueError("Lean oracle emitted a warning")
        rows = []
        for line in evaluated.stdout.splitlines():
            parts = line.split()
            if not parts or parts[0] not in {"R", "S"}:
                raise ValueError(f"Unexpected Lean oracle row: {line!r}")
            values = [int(part) for part in parts[1:]]
            if len(values) != (5 if parts[0] == "R" else 7):
                raise ValueError(f"Malformed Lean oracle row: {line!r}")
            rows.append((parts[0], *values))
        if not rows:
            raise ValueError("Lean oracle produced no rows")
        return rows


def baseline(ledger, limit, held, settled):
    ledger.initialize("test", max_trials=0, max_tokens=limit)
    if settled:
        ledger.reserve("test", "settled", tokens=settled, trial_units=0)
        ledger.dispatch("test", "settled")
        ledger.settle("test", "settled", actual_tokens=settled)
    ledger.reserve("test", "held", tokens=held, trial_units=0)


def check_reservations(rows, ledger_type=Ledger):
    grouped = collections.defaultdict(list)
    for kind, limit, held, settled, requested, expected in rows:
        if kind != "R":
            raise ValueError("Expected reservation oracle rows")
        grouped[(limit, held, settled)].append((requested, expected))
    checked = 0
    with tempfile.TemporaryDirectory(prefix="lean-ledger-reserve-") as temporary:
        for number, ((limit, held, settled), cases) in enumerate(sorted(grouped.items())):
            ledger = ledger_type(Path(temporary) / f"{number}.sqlite")
            baseline(ledger, limit, held, settled)
            for requested, expected in cases:
                key = f"candidate-{requested}"
                try:
                    ledger.reserve("test", key, tokens=requested, trial_units=0)
                    accepted = 1
                except ValueError as exc:
                    if "budget exhausted" not in str(exc):
                        raise
                    accepted = 0
                if accepted != expected:
                    raise BridgeMismatch(f"reservation {(limit, held, settled, requested)}: "
                                         f"Lean={expected}, ledger={accepted}")
                if accepted:
                    ledger.cancel("test", key, reason="bridge test")
                checked += 1
    return checked


def check_settlements(rows):
    checked = 0
    with tempfile.TemporaryDirectory(prefix="lean-ledger-settle-") as temporary:
        for number, row in enumerate(rows):
            kind, limit, held, settled, actual, expected_held, expected_settled, expected_overrun = row
            if kind != "S":
                raise ValueError("Expected settlement oracle rows")
            ledger = Ledger(Path(temporary) / f"{number}.sqlite")
            baseline(ledger, limit, held, settled)
            ledger.dispatch("test", "held")
            ledger.settle("test", "held", actual_tokens=actual)
            status = ledger.status("test")
            observed = (status["reserved_tokens"], status["settled_tokens"], int(status["overrun"]))
            expected = (expected_held, expected_settled, expected_overrun)
            if observed != expected:
                raise BridgeMismatch(f"settlement {row[1:5]}: Lean={expected}, ledger={observed}")
            if expected_overrun:
                try:
                    ledger.reserve("test", "after-overrun", tokens=0, trial_units=0)
                except ValueError as exc:
                    if "overrun" not in str(exc):
                        raise
                else:
                    raise BridgeMismatch("Provider overrun permitted a later reservation")
            checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", required=True)
    args = parser.parse_args()
    rows = oracle(args.lean)
    reservations = check_reservations([row for row in rows if row[0] == "R"])
    settlements = check_settlements([row for row in rows if row[0] == "S"])
    print(f"Lean theorems checked; {reservations} reservation and {settlements} settlement cases match SQLite")


if __name__ == "__main__":
    main()
