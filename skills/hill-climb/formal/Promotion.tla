------------------------- MODULE Promotion -------------------------
EXTENDS Naturals
CONSTANTS MaxEpoch, BrokenGuard, ExternalUpdatesGeneration
VARIABLES ref, generation, epoch, phase, expectedRef, expectedGeneration,
          expectedEpoch, marker, originRef, originGeneration, originEpoch,
          writeEpoch, commitEpoch, up
vars == <<ref, generation, epoch, phase, expectedRef, expectedGeneration,
          expectedEpoch, marker, originRef, originGeneration, originEpoch,
          writeEpoch, commitEpoch, up>>
Refs == {"base", "other", "winner"}
Init == /\ ref = "base" /\ generation = 0 /\ epoch = 0 /\ phase = "none"
        /\ expectedRef = "none" /\ expectedGeneration = 0 /\ expectedEpoch = 0
        /\ marker = FALSE /\ originRef = "none" /\ originGeneration = 0
        /\ originEpoch = 0 /\ writeEpoch = 0 /\ commitEpoch = 0 /\ up = TRUE
ExternalMove(r) ==
    /\ r \in Refs \ {ref} /\ epoch < MaxEpoch
    /\ ref' = r /\ epoch' = epoch + 1
    /\ generation' = IF ExternalUpdatesGeneration THEN generation + 1 ELSE generation
    /\ UNCHANGED <<phase, expectedRef, expectedGeneration, expectedEpoch, marker,
                   originRef, originGeneration, originEpoch, writeEpoch, commitEpoch, up>>
RecordIntent ==
    /\ up /\ phase = "none" /\ ref = "base"
    /\ phase' = "pending" /\ expectedRef' = ref
    /\ expectedGeneration' = generation /\ expectedEpoch' = epoch
    /\ UNCHANGED <<ref, generation, epoch, marker, originRef, originGeneration,
                   originEpoch, writeEpoch, commitEpoch, up>>
WriteRef ==
    /\ up /\ phase = "pending" /\ ~marker /\ epoch < MaxEpoch
    /\ (BrokenGuard \/ (ref = expectedRef /\ generation = expectedGeneration))
    /\ ref' = "winner" /\ generation' = generation + 1 /\ epoch' = epoch + 1
    /\ marker' = TRUE /\ originRef' = ref /\ originGeneration' = generation
    /\ originEpoch' = epoch /\ writeEpoch' = epoch + 1
    /\ UNCHANGED <<phase, expectedRef, expectedGeneration, expectedEpoch, commitEpoch, up>>
Ack ==
    /\ up /\ phase = "pending" /\ marker
    /\ ref = "winner" /\ generation = expectedGeneration + 1
    /\ phase' = "committed" /\ commitEpoch' = epoch
    /\ UNCHANGED <<ref, generation, epoch, expectedRef, expectedGeneration, expectedEpoch,
                   marker, originRef, originGeneration, originEpoch, writeEpoch, up>>
Crash ==
    /\ up /\ phase = "pending" /\ up' = FALSE
    /\ UNCHANGED <<ref, generation, epoch, phase, expectedRef, expectedGeneration,
                   expectedEpoch, marker, originRef, originGeneration, originEpoch,
                   writeEpoch, commitEpoch>>
Recover ==
    /\ ~up /\ up' = TRUE
    /\ IF ~marker /\ ref = expectedRef /\ generation = expectedGeneration
          THEN /\ phase' = "pending" /\ commitEpoch' = commitEpoch
          ELSE IF marker /\ ref = "winner" /\ generation = expectedGeneration + 1
               THEN /\ phase' = "committed" /\ commitEpoch' = epoch
               ELSE /\ phase' = "quarantined" /\ commitEpoch' = commitEpoch
    /\ UNCHANGED <<ref, generation, epoch, expectedRef, expectedGeneration, expectedEpoch,
                   marker, originRef, originGeneration, originEpoch, writeEpoch>>
Next == (\E r \in Refs : ExternalMove(r)) \/ RecordIntent \/ WriteRef \/ Ack \/ Crash \/ Recover
Spec == Init /\ [][Next]_vars
TypeOK == /\ ref \in Refs /\ generation \in 0..MaxEpoch /\ epoch \in 0..MaxEpoch
          /\ phase \in {"none", "pending", "committed", "quarantined"}
          /\ expectedRef \in Refs \cup {"none"} /\ expectedGeneration \in 0..MaxEpoch
          /\ expectedEpoch \in 0..MaxEpoch /\ marker \in BOOLEAN
          /\ originRef \in Refs \cup {"none"} /\ originGeneration \in 0..MaxEpoch
          /\ originEpoch \in 0..MaxEpoch /\ writeEpoch \in 0..MaxEpoch
          /\ commitEpoch \in 0..MaxEpoch /\ up \in BOOLEAN
OriginSafe == ~marker \/ (originRef = expectedRef /\ originGeneration = expectedGeneration
                           /\ originEpoch = expectedEpoch)
CommitSafe == phase # "committed" \/ (marker /\ commitEpoch = writeEpoch)
=============================================================================
