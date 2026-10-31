#!/usr/bin/env python3
"""Read a reuse catalog and count source observations without executing or changing code."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True


KINDS = ("template", "snippet", "macro", "generator", "module", "library", "component")
MAX_JSON = 1024 * 1024
MAX_SOURCE = 4 * 1024 * 1024


class CatalogUnavailable(FileNotFoundError):
    pass


def text(value, label, maximum=2048):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be nonblank text of at most {maximum} characters")
    return value


def fields(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"{label} requires exactly: {', '.join(expected)}")


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result

    def constant(value):
        raise ValueError("Non-finite JSON value: " + value)

    with Path(path).open("rb") as source:
        data = source.read(MAX_JSON + 1)
    if len(data) > MAX_JSON:
        raise ValueError("JSON exceeds the 1 MiB profile limit")
    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def contained(project, value, file_only=False):
    path = Path(text(value, "Path", 1024))
    if path.is_absolute():
        raise ValueError("Use a repository-relative path: " + str(path))
    resolved = (project / path).resolve(strict=True)
    if not resolved.is_relative_to(project) or (file_only and not resolved.is_file()):
        raise ValueError("Path escapes the project or has the wrong type: " + str(path))
    if not (resolved.is_file() or resolved.is_dir()):
        raise ValueError("Expected a regular source or directory: " + str(path))
    return resolved


def catalog(project, filename=".tkstack/reuse/catalog.json"):
    project = Path(project).resolve(strict=True)
    relative = Path(text(filename, "Catalog path", 1024))
    if relative.is_absolute():
        raise ValueError("Catalog path must be repository-relative")
    candidate = project / relative
    if not candidate.resolve().is_relative_to(project):
        raise ValueError("Catalog path escapes the project")
    if not candidate.exists() and not candidate.is_symlink():
        raise CatalogUnavailable("No reuse catalog; search actual modules and manifests")
    path = contained(project, filename, file_only=True)
    data = read_json(path)
    fields(data, ("version", "entries"), "Catalog")
    if type(data["version"]) is not int or data["version"] != 1 or not isinstance(data["entries"], list):
        raise ValueError("Catalog requires version 1 and an entries array")
    entries = []
    ids = set()
    for entry in data["entries"]:
        fields(entry, ("id", "kind", "summary", "artifact", "guide", "tags", "usage"), "Entry")
        identifier = text(entry["id"], "ID", 64)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier) or identifier in ids:
            raise ValueError("Duplicate or invalid reuse ID: " + identifier)
        ids.add(identifier)
        if entry["kind"] not in KINDS:
            raise ValueError("Unknown reuse kind")
        text(entry["summary"], "Summary")
        text(entry["usage"], "Usage", 4096)
        tags = entry["tags"]
        if not isinstance(tags, list) or len(tags) > 32:
            raise ValueError("Tags must be an array of at most 32 strings")
        for tag in tags:
            text(tag, "Tag", 128)
        contained(project, entry["artifact"])
        contained(project, entry["guide"], file_only=True)
        entries.append(entry)
    return sorted(entries, key=lambda entry: entry["id"])


def find(project, query, filename=".tkstack/reuse/catalog.json", kind=None, limit=10):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    if kind is not None and kind not in KINDS:
        raise ValueError("Unknown reuse kind")
    terms = text(query, "Query", 256).casefold().split()
    matches = []
    for entry in catalog(project, filename):
        haystack = " ".join([entry["id"], entry["kind"], entry["summary"], *entry["tags"]]).casefold()
        if (kind is None or entry["kind"] == kind) and all(term in haystack for term in terms):
            matches.append(entry)
    return {"status": "matched" if matches else "no-match", "total": len(matches),
            "results": matches[:limit], "executed": False}


def read_source(path):
    with path.open("rb") as source:
        before = os.fstat(source.fileno())
        data = source.read(MAX_SOURCE + 1)
        after = os.fstat(source.fileno())
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Source changed during observation: " + str(path))
    if len(data) > MAX_SOURCE:
        raise ValueError("Source exceeds the 4 MiB profile limit: " + str(path))
    return {"identity": (after.st_dev, after.st_ino), "sha256": hashlib.sha256(data).hexdigest(),
            "lines": data.decode("utf-8").splitlines(keepends=True)}


def assess(project, document, jobs=4):
    if type(jobs) is not int or not 1 <= jobs <= 16:
        raise ValueError("Jobs must be between 1 and 16")
    project = Path(project).resolve(strict=True)
    fields(document, ("version", "pattern", "occurrences"), "Evidence")
    if type(document["version"]) is not int or document["version"] != 1:
        raise ValueError("Evidence version must be 1")
    text(document["pattern"], "Pattern")
    observations = document["occurrences"]
    if not isinstance(observations, list) or not 1 <= len(observations) <= 64:
        raise ValueError("Provide 1 to 64 observations")
    requests = []
    for item in observations:
        fields(item, ("path", "start_line", "end_line"), "Occurrence")
        start, end = item["start_line"], item["end_line"]
        if type(start) is not int or type(end) is not int or not 1 <= start <= end:
            raise ValueError("Line ranges require positive integer start <= end")
        requests.append((contained(project, item["path"], file_only=True), start, end))
    paths = list(dict.fromkeys(path for path, _, _ in requests))
    with ThreadPoolExecutor(max_workers=min(jobs, len(paths))) as pool:
        sources = dict(zip(paths, pool.map(read_source, paths)))
    seen = set()
    ranges = {}
    snapshots = {}
    result = []
    for path, start, end in requests:
        source = sources[path]
        identity = source["identity"]
        if end > len(source["lines"]):
            raise ValueError("Line range exceeds source: " + str(path))
        if identity in snapshots and snapshots[identity] != source["sha256"]:
            raise ValueError("Physical source changed across aliases")
        snapshots[identity] = source["sha256"]
        key = (identity, start, end)
        if key in seen:
            continue
        seen.add(key)
        if any(start <= previous_end and previous_start <= end
               for previous_start, previous_end in ranges.get(identity, [])):
            raise ValueError("Overlapping source ranges are not independent evidence")
        ranges.setdefault(identity, []).append((start, end))
        excerpt = "".join(source["lines"][start - 1:end]).encode("utf-8")
        result.append({"path": str(path.relative_to(project)), "start_line": start, "end_line": end,
                       "source_sha256": source["sha256"], "excerpt_sha256": hashlib.sha256(excerpt).hexdigest()})
    return {"pattern": document["pattern"], "distinct_occurrences": len(result), "threshold": 3,
            "threshold_met": len(result) >= 3, "semantic_equivalence": "unverified",
            "automatic_extraction": False, "occurrences": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "find", "assess"):
        operation = sub.add_parser(name)
        operation.add_argument("--project", type=Path, default=Path.cwd())
        if name == "assess":
            operation.add_argument("--input", type=Path, required=True)
            operation.add_argument("--jobs", type=int, default=4)
        else:
            operation.add_argument("--catalog", default=".tkstack/reuse/catalog.json")
            if name == "find":
                operation.add_argument("--query", required=True)
                operation.add_argument("--kind", choices=KINDS)
                operation.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    try:
        if args.command == "find":
            result = find(args.project, args.query, args.catalog, args.kind, args.limit)
        elif args.command == "assess":
            result = assess(args.project, read_json(args.input), args.jobs)
        else:
            result = {"status": "valid", "entries": len(catalog(args.project, args.catalog)), "executed": False}
        print(json.dumps(result, indent=2))
    except CatalogUnavailable as error:
        print(json.dumps({"status": "catalog-unavailable", "message": str(error), "executed": False}))
        return 3
    except (OSError, ValueError) as error:
        print("reusify: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
