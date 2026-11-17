"""Run pinned TLC checks in a temporary directory and report their results."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

# Hash locally computed for the official v1.8.0 release asset. Its SHA-1 also
# matches the upstream release page, which publishes SHA-1 for this asset.
JAR_SHA256 = "7e53aa636dac8a3cb0533f343115c0548e03fc0ce5edc7739becf58d3d0fb84f"
CASES = (
    ("Budget.tla", "BudgetSafe.cfg", None),
    ("Budget.tla", "BudgetBroken.cfg", "BudgetSafe"),
    ("Promotion.tla", "PromotionSafe.cfg", None),
    ("Promotion.tla", "PromotionBrokenGuard.cfg", "OriginSafe"),
    ("Promotion.tla", "PromotionBrokenWriter.cfg", "OriginSafe"),
)


def run(jar):
    jar = Path(jar).resolve(strict=True)
    if hashlib.sha256(jar.read_bytes()).hexdigest() != JAR_SHA256:
        raise ValueError("TLC jar does not match the pinned SHA-256")
    if not shutil.which("java"):
        raise RuntimeError("Java is required to run TLC")
    source = Path(__file__).resolve().parent
    results = []
    # TLC writes trace files beside the spec on failures. Never write to the checkout.
    with tempfile.TemporaryDirectory(prefix="tkstack-tlc-") as temporary:
        staging = Path(temporary)
        for path in source.iterdir():
            if path.suffix in {".tla", ".cfg"}:
                shutil.copyfile(path, staging / path.name)
        for spec, config, expected_violation in CASES:
            command = ["java", "-XX:+UseParallelGC", "-cp", str(jar), "tlc2.TLC",
                       "-workers", "1", "-config", config, spec]
            completed = subprocess.run(command, cwd=staging, capture_output=True,
                                       text=True, timeout=60, check=False)
            output = completed.stdout + completed.stderr
            if expected_violation is None:
                passed = (completed.returncode == 0 and
                          "Model checking completed. No error has been found." in output)
            else:
                passed = (completed.returncode == 12 and
                          f"Invariant {expected_violation} is violated." in output)
            if not passed:
                raise RuntimeError(f"TLC {config} did not produce the expected result:\n{output}")
            count = re.search(r"(\d+) distinct states found", output)
            results.append({"config": config, "states": int(count.group(1)) if count else None,
                            "result": "safe_within_bounds" if expected_violation is None
                                      else "expected_counterexample",
                            "invariant": expected_violation})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", required=True, help="Path to the pinned official tla2tools.jar")
    args = parser.parse_args()
    print(json.dumps(run(args.jar), indent=2))


if __name__ == "__main__":
    main()
