# Reliable reusable execution

Before generating a workflow, separate an algorithm from an agent judgment,
and an on-demand invocation from a scheduled automation. Scheduling, external
messages, paid calls, and merge/release effects need the task's actual scope;
authoring a reusable script does not silently enable them.

Define parameters, observable outcome, guards, budget, timeouts, and a bounded
no-op exit. Use immutable inputs and per-task output ownership. Prefer events
to redundant pollers; otherwise share a budget, back off, and retain the last
observation so a resume neither misses work nor repeats effects.

State how each action fails, retries, cancels, and resumes. A stable operation ID
and durable host result can prevent duplicate paid submissions; retrying an
unknown outcome blindly cannot. Treat failure to launch the workflow separately
from failure of a completed action or the quality of its output.

Identify stall types before changing a prompt: no ready work, lost writer lease,
blocked dependency, missing credential/runtime, exhausted quota, or a valid quiet
exit. Record acted, no-op, or blocked with evidence. Zero output is not success
unless it is the explicit no-op contract.

A reusable package includes its native definition, code bindings, lockfiles,
input/output contract, real invocation, and public behavior evidence. A handoff
records exact version, completed nodes, retained results, owned workers, and next
ready action. Preserve the selected DSL's actual runtime semantics; do not infer
concurrency or durability from YAML indentation or a successful source parse.
