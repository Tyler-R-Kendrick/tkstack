#!/usr/bin/env python3
"""Exercise the actual Copier template and generated Python in isolated output directories."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile


TEMPLATE = Path(__file__).resolve().parent


def verify(executable, jobs=3):
    if type(jobs) is not int or not 1 <= jobs <= 8:
        raise ValueError("Jobs must be between 1 and 8")
    version = subprocess.run([str(executable), "--version"], capture_output=True, text=True,
                             check=True, timeout=10).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="reusify-copier-") as temporary:
        root = Path(temporary)
        environment = {**os.environ, "XDG_CACHE_HOME": str(root / "cache")}

        def render(case):
            name, label, workers, expected = case
            output = root / name
            result = subprocess.run([str(executable), "copy", "--defaults", "--data", "display_name=" + label,
                                     "--data", "worker_limit=" + str(workers), str(TEMPLATE), str(output)],
                                    env=environment, capture_output=True, text=True, timeout=45)
            module = output / "project_info.py"
            if not expected:
                if result.returncode == 0 or module.exists():
                    raise ValueError("Invalid input was accepted or published: " + name)
                return {"case": name, "status": "rejected"}, None
            if result.returncode != 0:
                raise ValueError("Native rendering failed: " + name)
            py_compile.compile(str(module), doraise=True)
            spec = importlib.util.spec_from_file_location("generated_" + name.replace("-", "_"), module)
            consumer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(consumer)
            if consumer.DISPLAY_NAME != label or consumer.WORKER_LIMIT != workers:
                raise ValueError("Generated consumer values differ from explicit inputs: " + name)
            data = module.read_bytes()
            return {"case": name, "status": "passed", "source_sha256": hashlib.sha256(data).hexdigest()}, data

        cases = [("basic", "Example", 1, True), ("quotes", 'A "quoted" label', 8, True),
                 ("unicode", "Build 🚀\nsecond\tline", 32, True),
                 ("literal-code", '\"; raise RuntimeError("injected")\n#', 4, True),
                 ("zero", "Example", 0, False), ("above-limit", "Example", 33, False),
                 ("invalid-type", "Example", "invalid", False), ("blank", "   ", 4, False)]
        with ThreadPoolExecutor(max_workers=min(jobs, len(cases))) as pool:
            results = list(pool.map(render, cases))
        repeat_receipt, repeat = render(("repeat", "Example", 1, True))
        if repeat != results[0][1]:
            raise ValueError("Unchanged inputs produced different module bytes")
        receipts = [receipt for receipt, _ in results] + [repeat_receipt]
    return {"status": "passed", "engine": version, "cases": receipts,
            "unchanged_module_bytes": True, "model_calls": 0,
            "scope": "Actual rendering, generated Python compilation/consumption, validation, and isolated outputs; no T4/Roslyn/editor execution."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copier", type=Path)
    parser.add_argument("--jobs", type=int, default=3)
    args = parser.parse_args()
    executable = args.copier or shutil.which("copier")
    if executable is None:
        print(json.dumps({"status": "runtime-unavailable", "native_verified": False}))
        return 3
    try:
        print(json.dumps(verify(executable, args.jobs), indent=2))
    except (OSError, ValueError, subprocess.SubprocessError, py_compile.PyCompileError) as error:
        print("reusify example: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
