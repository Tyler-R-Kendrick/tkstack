---------------------------- MODULE Budget ----------------------------
EXTENDS Naturals, FiniteSets
CONSTANTS Workers, Limit, Broken
VARIABLE phase
vars == <<phase>>
Statuses == {"idle", "checked", "reserved", "dispatched", "unknown", "settled", "cancelled"}
Charged == Cardinality({w \in Workers : phase[w] \in {"reserved", "dispatched", "unknown", "settled"}})
Init == phase = [w \in Workers |-> "idle"]
Check(w) == /\ phase[w] = "idle" /\ Charged < Limit
            /\ phase' = [phase EXCEPT ![w] = "checked"]
Reserve(w) == /\ phase[w] = "checked"
              /\ (Broken \/ Charged < Limit)
              /\ phase' = [phase EXCEPT ![w] = "reserved"]
Dispatch(w) == /\ phase[w] = "reserved"
               /\ phase' = [phase EXCEPT ![w] = "dispatched"]
CancelReserved(w) == /\ phase[w] = "reserved"
                     /\ phase' = [phase EXCEPT ![w] = "cancelled"]
LoseResponse(w) == /\ phase[w] = "dispatched"
                   /\ phase' = [phase EXCEPT ![w] = "unknown"]
Settle(w) == /\ phase[w] \in {"dispatched", "unknown"}
             /\ phase' = [phase EXCEPT ![w] = "settled"]
ConfirmNoExecution(w) == /\ phase[w] = "unknown"
                         /\ phase' = [phase EXCEPT ![w] = "cancelled"]
Next == \E w \in Workers : Check(w) \/ Reserve(w) \/ Dispatch(w) \/ CancelReserved(w)
                              \/ LoseResponse(w) \/ Settle(w) \/ ConfirmNoExecution(w)
Spec == Init /\ [][Next]_vars
TypeOK == phase \in [Workers -> Statuses]
BudgetSafe == Charged <= Limit
=============================================================================
