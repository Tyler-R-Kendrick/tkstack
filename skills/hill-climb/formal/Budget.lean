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

-- A proposal is charged once when authorized, and completion never refunds it.
def proposalStart (limit count : Nat) : Option Nat :=
  if count < limit then some (count + 1) else none

def proposalFinish (count : Nat) : Nat := count

theorem proposal_start_preserves (limit count next : Nat)
    (h : proposalStart limit count = some next) : next ≤ limit := by
  unfold proposalStart at h
  split at h
  next hg =>
    simp only [Option.some.injEq] at h
    subst next
    omega
  next => simp at h

theorem proposal_finish_keeps_count (count : Nat) : proposalFinish count = count := by
  rfl

theorem proposal_finish_does_not_restore_capacity (limit count : Nat)
    (h : limit ≤ count) : proposalStart limit (proposalFinish count) = none := by
  simp [proposalStart, proposalFinish, Nat.not_lt.mpr h]

-- Boolean true models a fresh admission; false models completion. Failed starts
-- are left out of an accepted trace. Duplicate keys and concurrency are external
-- assumptions checked by the executable ledger bridge and concurrency tests.
def proposalTrace (limit : Nat) : Nat → List Bool → Option Nat
  | count, [] => some count
  | count, true :: rest => (proposalStart limit count).bind (fun next => proposalTrace limit next rest)
  | count, false :: rest => proposalTrace limit (proposalFinish count) rest

theorem proposal_trace_preserves (limit count final : Nat) (actions : List Bool)
    (initial : count ≤ limit) (result : proposalTrace limit count actions = some final) : final ≤ limit := by
  induction actions generalizing count with
  | nil =>
    simp [proposalTrace] at result
    omega
  | cons action rest ih =>
    cases action with
    | false =>
      simp only [proposalTrace, proposalFinish] at result
      exact ih count initial result
    | true =>
      simp only [proposalTrace] at result
      cases h : proposalStart limit count with
      | none => simp [h] at result
      | some next =>
        simp [h] at result
        exact ih next (proposal_start_preserves limit count next h) result

-- The parent decides the child permit while holding the cancellation scope
-- lock. Registered is an identity check against that scope's active mapping.
def launchPermit (registered cancelled : Bool) : Bool := registered && !cancelled

theorem launch_requires_registration (registered cancelled : Bool)
    (h : launchPermit registered cancelled = true) : registered = true := by
  cases registered <;> cases cancelled <;> simp_all [launchPermit]

theorem launch_respects_cancellation (registered cancelled : Bool)
    (h : launchPermit registered cancelled = true) : cancelled = false := by
  cases registered <;> cases cancelled <;> simp_all [launchPermit]

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
  for limit in [1:5] do
    for count in [0:5] do
      if count ≤ limit then
        let started := (proposalStart limit count).isSome
        out := out.push s!"P {limit} {count} {boolBit started} {proposalFinish count}"
  for registered in #[false, true] do
    for cancelled in #[false, true] do
      out := out.push s!"L {boolBit registered} {boolBit cancelled} {boolBit (launchPermit registered cancelled)}"
  return out

end ExperimentBudget

def main : IO Unit := do
  for line in ExperimentBudget.cases do
    IO.println line
