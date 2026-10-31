# Requirements and atomic planning

Preserve the user's outcome and source wording before decomposing it. Establish
current behavior, owner, exclusions, acceptance conditions, evidence, budget,
and the actual publication/merge boundary. Resolve observable facts from the
repository; do not add a default interview or approval gate.

Give requirements stable IDs and express behavior as Given/When/Then examples.
Identify real consumer/provider contracts and supported versions. Record what
each check can and cannot prove. A schema is not proof of producer behavior.

Decompose into the smallest independently verifiable and deliverable outcomes.
A narrow complete behavior is useful; an isolated unfinished layer is not.
Contract-publication atoms may deliver a versioned artifact before providers
and consumers implement it, provided their acceptance claim is only that artifact.
Model true prerequisites and exclusive write scopes, then run the ready frontier
with bounded capacity and isolated state. Do not confuse DAG edges with PR bases.

Separate unresolved decisions from implementation tasks. Put a risky empirical
question first when a cheap bounded prototype can settle it. A prototype records
the hypothesis, distinguishing observation, result, and retained decision; it
does not become production code automatically. Keep product preferences separate
from facts that can be observed.

For a wide migration, first test whether a single coherent caller migration
can stay green. When external compatibility or reviewable delivery requires
expand/migrate/contract, state that reason, assign ownership and removal criteria,
and verify every increment. Do not preserve an unnecessary parallel API or accept
broken deliverables merely because a staging branch exists.

A plan-only request stops at the plan. In a full lifecycle, freeze the original
workload and branch obligations before dispatch, as the operating guide requires.
Read the existing workload, graph, and evidence templates instead of inventing
another task or tracking format.
