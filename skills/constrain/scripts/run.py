#!/usr/bin/env python3
"""Skillify-generated contract tool; native skill procedures retain their scope."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from package_runtime import execute, NativeFailure, read_json, loads

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    try:
        if args.input == '-':
            raw = sys.stdin.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError('Input exceeds 1 MiB')
            payload = loads(raw)
        else:
            payload = read_json(args.input)
        print(json.dumps(execute(payload, Path(__file__).resolve().parent.parent), sort_keys=True, allow_nan=False))
        return 0
    except NativeFailure as error:
        sys.stdout.write(error.stdout)
        sys.stderr.write(error.stderr)
        return error.code if 0 < error.code <= 125 else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
