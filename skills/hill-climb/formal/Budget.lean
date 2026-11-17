import Std.Tactic

namespace ExperimentBudget

structure Budget where
  limit : Nat
  reserved : Nat
  settled : Nat
  overrun : Bool
  deriving Repr

def withinLimit (s : Budget) : Prop := s.reserved + s.settled ≤ s.limit

def reserve (s : Budget) (amount : Nat) : Option Budget :=
  if !s.overrun && decide (s.reserved + s.settled + amount ≤ s.limit) then
    some { s with reserved := s.reserved + amount }
  else none

def settle (s : Budget) (held actual : Nat) : Option Budget :=
  if held ≤ s.reserved then
    some { s with reserved := s.reserved - held,
                  settled := s.settled + actual,
                  overrun := s.overrun || decide (actual > held) }
  else none

-- A successful atomic reservation respects the ceiling, even if the caller
-- provides a bad initial state. SQLite must serialize the check and insertion.
theorem reservation_preserves (s next : Budget) (amount : Nat)
    (h : reserve s amount = some next) : withinLimit next := by
  unfold reserve at h
  split at h
  next hg =>
    simp only [Option.some.injEq] at h
    subst next
    simp only [Bool.and_eq_true, Bool.not_eq_true, decide_eq_true_eq] at hg
    dsimp [withinLimit]
    omega
  next => simp at h

theorem bounded_settlement_preserves (s next : Budget) (held actual : Nat)
    (hvalid : withinLimit s) (hbound : actual ≤ held)
    (h : settle s held actual = some next) : withinLimit next := by
  unfold settle at h
  split at h
  next hg =>
    simp only [Option.some.injEq] at h
    subst next
    dsimp [withinLimit] at *
    omega
  next => simp at h

theorem overrun_blocks_reservation (s next : Budget) (held actual extra : Nat)
    (hover : actual > held) (h : settle s held actual = some next) :
    reserve next extra = none := by
  unfold settle at h
  split at h
  next hg =>
    simp only [Option.some.injEq] at h
    subst next
    simp [reserve, hover]
  next => simp at h

-- Produce concrete oracle rows directly from the definitions proved above.
def boolBit (b : Bool) : Nat := if b then 1 else 0

def cases : Array String := Id.run do
  let mut out := #[]
  for limit in [0:5] do
    for held in [0:5] do
      for settled in [0:5] do
        if held + settled ≤ limit then
          for requested in [0:5] do
            let s := Budget.mk limit held settled false
            let allowed := (reserve s requested).isSome
            out := out.push s!"R {limit} {held} {settled} {requested} {boolBit allowed}"
          for actual in [0:5] do
            let s := Budget.mk limit held settled false
            let after := (settle s held actual).getD s
            out := out.push s!"S {limit} {held} {settled} {actual} {after.reserved} {after.settled} {boolBit after.overrun}"
  return out

end ExperimentBudget

def main : IO Unit := do
  for line in ExperimentBudget.cases do
    IO.println line
