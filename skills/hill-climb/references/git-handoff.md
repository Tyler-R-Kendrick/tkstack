# Hand off a private champion to an SDLC worktree

The `native experiment` command can stage a promoted private champion in an
existing, exclusively owned SDLC worktree. Stop all writers first and use a
clean worktree at the exact recorded baseline, including no ignored files.
Review the decision, semantic evidence, independent confirmation and applicable
authorization before delivery.

```json
{
  "action": "handoff",
  "root": "/private/experiment",
  "decision": "accepted-decision-id",
  "delivery": "/path/to/sdlc-delivery-worktree",
  "writers_stopped": true
}
```

Invoke this request through `native experiment --request PATH`. The controller
loads the ledger-bound promotion intent and validates its decision and frozen
configuration. It rechecks settled selection and configured confirmation
receipts, the private champion ref, marker and generation, candidate ancestry,
edit scope, and the delivery baseline. It fetches the exact candidate object
locally, previews its patch in a temporary index, and stages it only when the
preview tree matches the evaluated tree. A final tree check follows staging.
The return value records the baseline, champion, tree, paths and staged state.
If promotion was interrupted, use the controller `recover` action first.

The action runs no commit, merge, push or publication. Continue with the
repository's normal SDLC review and delivery. Confirm the committed tree after
hooks and re-run applicable checks. If the base moved, a rebase or conflict
resolution changes the tree, or dependencies, evaluation inputs or context
changed, prepare a new integration candidate and re-evaluate it before
claiming the earlier result applies. If a failure occurs after staging, inspect
the owned worktree before taking further action. Retain private objects and
records for the required audit and replay period. The local fetch may also
retain candidate ancestry as unreachable objects until normal Git maintenance.

This operation assumes the caller holds an exclusive SDLC worktree lease and
has actually stopped external writers. The Git and controller checks are not
an OS sandbox, and semantic review and delivery authorization remain separate.
