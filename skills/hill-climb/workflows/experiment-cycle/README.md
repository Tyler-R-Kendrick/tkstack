# Experiment cycle workflow

This optional Microsoft Agent Framework (MAF) workflow runs an ordered,
bounded list of existing hill-climb controller requests. It invokes the
controller for the selected experiment root and target, retains the source
request hashes and controller responses, and stops when a stage fails or
returns an ineligible comparison, unqualified calibration, or unresolved
recovery. Its single MAF tool action owns an ordered sequence. It does not
start agents or choose model providers.

## Prerequisites

Python 3.12 on Linux can use the supplied transitive hash lock:

```sh
python3 -m venv /path/to/isolated-venv
/path/to/isolated-venv/bin/pip install --require-hashes -r requirements.lock
```

The Power Fx dependency also needs a compatible .NET runtime. The native
checks for this implementation used .NET 8.0.33 and MAF declarative 1.4.0.
Install .NET independently and set `DOTNET_ROOT` and
`PYTHONNET_RUNTIME=coreclr` as needed. A Python dependency installation
does not provision .NET. Regenerate and verify the lock on other Python
versions or platforms.

## Invocation

Create explicit request JSON files as described in the
[Git experiment guide](../../references/git-experiments.md). Each request's
`root` must be the selected root. An `init` request must select the given
target, and the active configuration must match the target on existing roots.
Files must live inside the supplied request directory. Before the first stage,
the workflow checks the JSON, action, root and selected target and snapshots
each request's bytes. The controller validates action-specific fields when that
stage runs, so a later malformed request can still stop a partially completed
sequence.
`inputs.json` is illustrative. Replace the filenames with actual requests.

```sh
/path/to/isolated-venv/bin/python run.py \
  --request-dir /path/to/requests \
  --root /path/to/private-experiment \
  --target selected-target \
  --input /path/to/inputs.json
```

An input file has one field:

```json
{"request_paths": ["01-init.json", "02-allocate.json", "03-status.json"]}
```

Actions run in the declared order, with at most 16 requests per invocation.
A failure stops subsequent stages. Earlier successful side effects remain and
must be inspected through controller status/recovery. The host accepts
success only when the actual MAF output equals the successful binding receipt.
The source YAML, input and controller source hashes, selected root and target,
MAF runtime version, request hashes, and ordered responses are in the output.
The host checks controller source hashes again after the graph finishes. This
detects drift after effects may already have occurred; use a fixed, access
controlled package when stronger isolation is needed.

The default wrapper timeout is 120 seconds per stage. Run stages require at
least 120 seconds. The controller's own local trial timeout also applies.
If the wrapper times out, the controller may have started descendants in
separate process sessions. Their termination is not guaranteed. Inspect and
reconcile both the process tree and experiment ledger before retrying. Cancellation of the async binding
also does not guarantee that its worker thread or descendants have stopped.

## Scope and verification

The local runner executes trusted target commands with host privileges. The
workflow itself does not call a model, though a user-supplied target might.
It cannot enforce a model spend cap or hide confirmation data from a process
with host access. Use a real external sandbox and provider-aware accounting
for untrusted trials or model-spending workflows.

Unit tests exercise order, prevalidation, stopping and timeout reporting
without MAF. To run the native tests with the real runtime, set:

```sh
TKSTACK_MAF_PYTHON=/path/to/isolated-venv/bin/python \
DOTNET_ROOT=/path/to/dotnet PYTHONNET_RUNTIME=coreclr \
python3 -m unittest discover -s tests -p test_experiment_maf.py -v
```

The native tests create temporary Git repositories and run actual controller
requests through the MAF graph. They do not run a model or publish a branch.
