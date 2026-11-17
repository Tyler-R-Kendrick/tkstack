"""Capture a four-cell regrade from controller-owned, settled trial evidence."""

import hashlib
import json
import os
from pathlib import Path
import tarfile
import tempfile

import experiment
from experiment_evaluate import regrade_matrix
from experiment_runner import _materialize


def _historical_config(root, revision):
    candidates = [root / "experiment.json", root / "revisions" / (revision + ".json")]
    for path in candidates:
        if path.is_file() and not path.is_symlink() and experiment.digest(path) == revision:
            config = experiment.read(path)
            if config.get("version") == 1:
                return config
    raise ValueError("historical experiment configuration is missing or changed")


def _decision(root, decision_id):
    saved = experiment.read(root / "decisions" / (experiment.name(decision_id) + ".json"))
    keys = saved["baseline_keys"] + saved["candidate_keys"]
    if not keys:
        raise ValueError("decision has no run receipts")
    revisions = {experiment.read(root / "runs" / (experiment.name(key) + ".json"))["config_digest"]
                 for key in keys}
    if len(revisions) != 1:
        raise ValueError("decision mixes experiment revisions")
    revision = revisions.pop()
    config = _historical_config(root, revision)
    identity_before, identity_after = saved["spec"]["baseline"], saved["spec"]["candidate"]
    spec = experiment.evaluation_spec(config, identity_before, identity_after)
    if spec != saved["spec"]:
        raise ValueError("decision spec differs from frozen configuration")
    before = experiment.rows_for(root, config, saved["baseline_keys"], "baseline", identity_before, revision=revision, generation=saved["generation"])
    after = experiment.rows_for(root, config, saved["candidate_keys"], "candidate", identity_after, revision=revision, generation=saved["generation"])
    return config, spec, before, after


def _tar_source(git, identity, destination):
    if experiment.commit_identity(git, identity["commit"]) != identity:
        raise ValueError("submission commit or tree is no longer available")
    with tempfile.TemporaryDirectory(prefix="snapshot-", dir=destination.parent) as temp:
        source = Path(temp) / "source"
        source.mkdir()
        _materialize(git.repo, identity["commit"], source)
        with destination.open("xb") as output:
            with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for path in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
                    info = archive.gettarinfo(str(path), arcname=path.relative_to(source).as_posix())
                    info.uid, info.gid, info.uname, info.gname, info.mtime = 0, 0, "", "", 0
                    if info.isfile():
                        with path.open("rb") as content:
                            archive.addfile(info, content)
                    else:
                        archive.addfile(info)
            output.flush()
            os.fsync(output.fileno())
    return experiment.digest(destination)


def capture(root, git, capture_id, old_decision, new_decision):
    """Reconstruct Git submissions and build a reviewable four-cell matrix.

    Source snapshots are reconstructed from the exact Git trees. Runtime
    outputs not retained by the trial cannot be reconstructed from those trees.
    """
    root = Path(root).resolve(strict=True)
    output = root / "regrades" / experiment.name(capture_id)
    if output.exists() or output.is_symlink():
        raise ValueError("regrade capture already exists")
    old_config, old_spec, old_before, old_after = _decision(root, old_decision)
    new_config, new_spec, new_before, new_after = _decision(root, new_decision)
    output.mkdir(parents=True, mode=0o700)
    source_dir, case_dir = output / "submissions", output / "cases"
    source_dir.mkdir()
    case_dir.mkdir()
    sources, cases = {}, {}
    for config, rows in ((old_config, old_before), (old_config, old_after),
                         (new_config, new_before), (new_config, new_after)):
        for row in rows:
            commit = row["commit"]
            if commit not in sources:
                path = source_dir / (commit + ".tar")
                sha = _tar_source(git, {"commit": commit, "tree": row["tree"]}, path)
                sources[commit] = {"path": str(path.relative_to(root)), "sha256": sha}
            case_sha = config["case_files"][row["case"]]["sha256"]
            if case_sha not in cases:
                retained = root / "case-evidence" / case_sha
                if retained.is_symlink() or not retained.is_file() or experiment.digest(retained) != case_sha:
                    raise ValueError("retained case evidence is missing or changed")
                destination = case_dir / case_sha
                with destination.open("xb") as stream:
                    stream.write(retained.read_bytes())
                    stream.flush()
                    os.fsync(stream.fileno())
                cases[case_sha] = {"path": str(destination.relative_to(root)), "sha256": case_sha}
            row["submission_artifacts"] = [sources[commit]]
            row["case_sha256"] = case_sha
            row["case_artifact"] = cases[case_sha]
            for artifact in row["artifacts"]:
                artifact["path"] = "evidence/" + artifact["path"]
            for judgment in row.get("qualitative", {}).values():
                if isinstance(judgment, dict) and isinstance(judgment.get("evidence"), list):
                    judgment["evidence"] = ["evidence/" + path for path in judgment["evidence"]]
    matrix_request = {"old_spec": old_spec, "new_spec": new_spec,
                      "old_baseline": old_before, "old_candidate": old_after,
                      "new_baseline": new_before, "new_candidate": new_after,
                      "evidence_root": str(root)}
    result = regrade_matrix(**matrix_request)
    experiment.write_new(output / "matrix.json", matrix_request)
    experiment.write_new(output / "result.json", result)
    old_path = root / "decisions" / (experiment.name(old_decision) + ".json")
    new_path = root / "decisions" / (experiment.name(new_decision) + ".json")
    experiment.write_new(output / "manifest.json", {
        "old_decision": old_decision, "old_decision_sha256": experiment.digest(old_path),
        "new_decision": new_decision, "new_decision_sha256": experiment.digest(new_path),
        "matrix_sha256": experiment.digest(output / "matrix.json"),
        "result_sha256": experiment.digest(output / "result.json"),
    })
    return {"capture": str(output), "matrix": str(output / "matrix.json"),
            "result": result,
            "limitations": "Source archives reconstruct frozen Git trees; generated runtime outputs are not retained unless captured separately."}
