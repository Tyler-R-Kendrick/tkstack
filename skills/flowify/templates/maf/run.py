#!/usr/bin/env python3
"""Run this model-free example with the real Microsoft Agent Framework runtime."""

import argparse
import asyncio
from contextlib import redirect_stdout
import hashlib
import importlib.util
import importlib.metadata
import json
from pathlib import Path
import sys

from bindings import hash_files


async def execute(project, inputs, jobs):
    from agent_framework_declarative import WorkflowFactory
    observed = []
    failures = []
    async def bound_hash_files(paths: list[str]) -> str:
        try:
            value = await hash_files(project, paths, jobs)
        except (OSError, ValueError) as error:
            failures.append(str(error))
            raise
        receipt = json.dumps(value, sort_keys=True)
        observed.append(receipt)
        return receipt
    workflow_path = Path(__file__).with_name("workflow.yaml")
    source = workflow_path.read_bytes()
    inputs_hash = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    factory = WorkflowFactory().register_tool("hash_files", bound_hash_files)
    workflow = factory.create_workflow_from_yaml(source.decode("utf-8"), base_path=workflow_path.parent)
    result = await workflow.run(inputs)
    outputs = result.get_outputs()
    if failures:
        raise ValueError("Binding failed: " + "; ".join(failures))
    if len(observed) != 1 or outputs != observed:
        raise ValueError("Workflow did not emit the actual successful binding receipt")
    if workflow_path.read_bytes() != source:
        raise ValueError("Workflow source changed during execution")
    return {"status": "succeeded", "workflow_sha256": hashlib.sha256(source).hexdigest(),
            "runtime_version": importlib.metadata.version("agent-framework-declarative"),
            "inputs_sha256": inputs_hash,
            "result": json.loads(observed[0])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if importlib.util.find_spec("agent_framework_declarative") is None:
        print("MAF runtime unavailable; install and lock requirements.txt in a project environment.", file=sys.stderr)
        return 3
    try:
        # This CLI owns stdout; vendor initialization diagnostics belong on stderr.
        with redirect_stdout(sys.stderr):
            result = asyncio.run(execute(args.project, json.loads(args.input.read_text()), args.jobs))
        print(json.dumps(result, indent=2))
        return 0
    except Exception as error:
        print(f"workflow failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
