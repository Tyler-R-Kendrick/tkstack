#!/usr/bin/env python3
"""Execute a scoped experiment-action sequence with the native MAF runtime."""
import argparse
import asyncio
from contextlib import redirect_stdout
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys

from bindings import execute_requests, _json


async def execute(request_dir, root, target, inputs, timeout):
    from agent_framework_declarative import WorkflowFactory

    observed = []
    failures = []
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    controller = scripts / "experiment.py"
    controller_files = ("experiment.py", "experiment_git.py", "experiment_ledger.py",
                        "experiment_runner.py", "experiment_evaluate.py", "hill_climb.py",
                        "json_contract.py")
    controller_hashes = {
        name: hashlib.sha256((scripts / name).read_bytes()).hexdigest()
        for name in controller_files
    }

    async def bound_execute_requests(request_paths: list[str]) -> str:
        try:
            value = await execute_requests(request_dir, root, target, request_paths, controller, timeout)
        except (OSError, ValueError) as error:
            failures.append(str(error))
            raise
        receipt = json.dumps(value, sort_keys=True, allow_nan=False)
        observed.append(receipt)
        return receipt

    path = Path(__file__).with_name("workflow.yaml")
    source = path.read_bytes()
    input_bytes = json.dumps(inputs, sort_keys=True, allow_nan=False).encode()
    factory = WorkflowFactory().register_tool("execute_requests", bound_execute_requests)
    workflow = factory.create_workflow_from_yaml(source.decode("utf-8"), base_path=path.parent)
    result = await workflow.run(inputs)
    outputs = result.get_outputs()
    if failures:
        raise ValueError("binding failed: " + "; ".join(failures))
    if len(observed) != 1 or outputs != observed:
        raise ValueError("workflow did not emit the actual successful binding receipt")
    if path.read_bytes() != source:
        raise ValueError("workflow source changed during execution")
    if any(hashlib.sha256((scripts / name).read_bytes()).hexdigest() != value
           for name, value in controller_hashes.items()):
        raise ValueError("controller source changed during execution; inspect completed effects")
    return {
        "status": "succeeded",
        "workflow_sha256": hashlib.sha256(source).hexdigest(),
        "runtime_version": importlib.metadata.version("agent-framework-declarative"),
        "inputs_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "experiment_root": str(Path(root).resolve()),
        "target": target,
        "controller_sha256": controller_hashes,
        "results": json.loads(observed[0]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-dir", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    if importlib.util.find_spec("agent_framework_declarative") is None:
        print("MAF runtime unavailable; install requirements.lock in a project environment.", file=sys.stderr)
        return 3
    try:
        with redirect_stdout(sys.stderr):
            raw_inputs = args.input.read_bytes()
            if len(raw_inputs) > 256 * 1024:
                raise ValueError("input exceeds 256 KiB")
            inputs = _json(raw_inputs)
            if not isinstance(inputs, dict) or set(inputs) != {"request_paths"}:
                raise ValueError("input must contain only request_paths")
            result = asyncio.run(execute(args.request_dir, args.root, args.target, inputs, args.timeout))
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    except Exception as error:
        print(f"workflow failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
