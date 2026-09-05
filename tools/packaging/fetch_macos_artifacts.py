#!/usr/bin/env python3
"""Fetch a fresh successful run from the configured fork using authenticated gh."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile
import zipfile

from prepare_macos_release import REPOSITORY, require, sha, validate_metadata


def api(endpoint):
    return json.loads(subprocess.check_output(["gh", "api", f"repos/{REPOSITORY}/{endpoint}"], text=True))


def extract_safe(archive, destination):
    with zipfile.ZipFile(archive) as z:
        names = set()
        require(len(z.infolist()) <= 100 and sum(i.file_size for i in z.infolist()) <= 1024**3, "Oversized artifact")
        for info in z.infolist():
            path = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            require(not path.is_absolute() and ".." not in path.parts and "\\" not in info.filename, "Unsafe ZIP path")
            require(info.filename and path.parts and ":" not in path.parts[0], "Unsafe ZIP path")
            normalized = str(path).casefold()
            require(normalized not in names, "Duplicate ZIP entry")
            names.add(normalized)
            require(not stat.S_ISLNK(mode) and (stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR)), "Unsafe ZIP entry type")
        z.extractall(destination)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    require(args.run_id > 0 and not args.output.exists(), "Use a positive run ID and a new output directory")
    run = api(f"actions/runs/{args.run_id}")
    jobs = api(f"actions/runs/{args.run_id}/attempts/{run['run_attempt']}/jobs?per_page=100")
    artifacts = api(f"actions/runs/{args.run_id}/artifacts?per_page=100")
    selected = validate_metadata(run, jobs, artifacts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        root = Path(tmp)
        data = root / "data"
        (data / "metadata").mkdir(parents=True)
        for name, obj in (("run", run), ("jobs", jobs), ("artifacts", artifacts)):
            (data / "metadata" / (name + ".json")).write_text(json.dumps(obj, sort_keys=True) + "\n")
        for artifact in selected:
            archive = root / (str(artifact["id"]) + ".zip")
            with archive.open("wb") as out:
                subprocess.run(["gh", "api", f"repos/{REPOSITORY}/actions/artifacts/{artifact['id']}/zip"], stdout=out, check=True)
            expected = next(a["digest"] for a in artifacts["artifacts"] if a["id"] == artifact["id"])
            require(expected == "sha256:" + sha(archive), "Artifact archive digest mismatch")
            extract_safe(archive, data / artifact["name"])
        shutil.move(str(data), str(args.output))
    print(f"Saved run {args.run_id} / {run['head_sha']} to {args.output}")


if __name__ == "__main__":
    main()
