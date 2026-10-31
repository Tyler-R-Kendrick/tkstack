#!/usr/bin/env python3
"""Invoke the skill's executable workflow with one JSON object."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from workflow import execute
from json_contract import loads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON file, or - for stdin")
    args = parser.parse_args()
    try:
        if args.input == "-":
            raw = sys.stdin.read(1024 * 1024 + 1)
        else:
            with Path(args.input).open(encoding="utf-8") as source:
                raw = source.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Input exceeds the 1 MiB text limit")
        payload = loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Input must be a JSON object")
        output = execute(payload)
        print(json.dumps(output, allow_nan=False, sort_keys=True))
        return 0
    except NotImplementedError:
        print("WORKFLOW_NOT_IMPLEMENTED", file=sys.stderr)
        return 3
    except (OSError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
