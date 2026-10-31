"""Deterministic local-file binding; independent reads with bounded concurrency."""

import asyncio
import hashlib
from pathlib import Path


def fingerprint(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(64 * 1024):
            result.update(chunk)
    return result.hexdigest()


async def hash_files(project, paths, jobs=4):
    project = Path(project).resolve()
    if type(jobs) is not int or not 1 <= jobs <= 32:
        raise ValueError("jobs must be between 1 and 32")
    if not isinstance(paths, list) or not 1 <= len(paths) <= 64:
        raise ValueError("Supply 1 to 64 explicit project-relative files")
    resolved = []
    for name in paths:
        if not isinstance(name, str) or not name or Path(name).is_absolute():
            raise ValueError("Input files must be project-relative paths")
        path = (project / name).resolve()
        if not path.is_relative_to(project) or not path.is_file():
            raise ValueError("Input must be an existing file inside the explicit project")
        resolved.append(path)
    if len(set(resolved)) != len(resolved):
        raise ValueError("Do not request the same canonical file twice")
    limit = asyncio.Semaphore(jobs)
    async def one(path):
        async with limit:
            checksum = await asyncio.to_thread(fingerprint, path)
            return {"path": path.relative_to(project).as_posix(), "sha256": checksum}
    tasks = [asyncio.create_task(one(path)) for path in resolved]
    joined = asyncio.gather(*tasks, return_exceptions=True)
    try:
        results = await asyncio.shield(joined)
    except asyncio.CancelledError:
        # Thread-backed reads cannot be forcibly cancelled; join them before returning failure.
        await joined
        raise
    for result in results:
        if isinstance(result, BaseException):
            raise result
    return {"files": results, "count": len(results)}
