#!/usr/bin/env python3
"""Bundle pinned source inputs and the Qt file modified by the build script."""
import argparse
import ast
import json
import pathlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

from prepare_macos_release import deterministic_zip, require, sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release-dir", type=Path, required=True)
    p.add_argument("--qt-archive", type=Path)
    args = p.parse_args()
    source = Path(__file__).resolve().parents[2]
    provenance = json.loads((args.release_dir / "provenance.json").read_text())
    commit = provenance["build_commit"]
    version = provenance["distribution_version"]
    def show(path):
        return subprocess.check_output(["git", "-C", str(source), "show", commit + ":" + path], text=True)
    deps = ast.parse(show("src/build_tools/update_deps.py"))
    qt = next(n.value for n in deps.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "QT6" for t in n.targets))
    fields = {k.arg: ast.literal_eval(k.value) for k in qt.keywords}
    require(fields["url"].startswith("https://download.qt.io/archive/qt/"), "Unexpected Qt source host")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        stage = root / "stage"
        stage.mkdir()
        archive = stage / fields["url"].rsplit("/", 1)[1]
        if args.qt_archive:
            shutil.copy2(args.qt_archive, archive)
        else:
            with urllib.request.urlopen(fields["url"], timeout=120) as response, archive.open("wb") as output:
                shutil.copyfileobj(response, output)
        require(sha(archive) == fields["sha256"], "Qt source hash mismatch")
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                if member.name.endswith("/src/corelib/thread/qyieldcpu.h"):
                    target = root / "qt/src/corelib/thread/qyieldcpu.h"
                elif "/LICENSES/" in member.name:
                    suffix = pathlib.PurePosixPath(member.name.split("/LICENSES/", 1)[1])
                    require(not suffix.is_absolute() and ".." not in suffix.parts, "Unsafe license path")
                    target = stage / "Qt-LICENSES" / str(suffix)
                else:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
        # Reproduce the audited patch without executing the upstream Python file.
        header = root / "qt/src/corelib/thread/qyieldcpu.h"
        content = header.read_text()
        require(content.count("#if __has_builtin(__yield)\n") == 1, "Qt patch no longer applies")
        patch_source = show("src/build_tools/build_qt.py")
        require("__builtin_arm_yield();" in patch_source, "Review changed upstream Qt patch")
        header.write_text(content.replace("#if __has_builtin(__yield)\n", "#if __has_builtin(__builtin_arm_yield)\n    __builtin_arm_yield();\n#elif __has_builtin(__yield)\n"))
        shutil.copy2(header, stage / "qyieldcpu.h")
        subprocess.run(["git", "-C", str(source), "archive", "--format=tar.gz", "--output=" + str(stage / ("mozkey-source-" + commit[:7] + ".tar.gz")), commit], check=True)
        (stage / "README.txt").write_text(f"MozKey build source: {commit}\nQt source archive SHA256: {fields['sha256']}\nqyieldcpu.h is the modified Qt file after the patch in src/build_tools/build_qt.py.\nExtract the Qt archive and replace src/corelib/thread/qyieldcpu.h with this file.\nBuild configuration and patch implementation: src/build_tools/build_qt.py in the MozKey source archive.\nExact CI build: .github/workflows/macos_zenz_formal_package_dual_native.yml in the same archive.\nNo additional restrictions on modification or reverse engineering for debugging modified LGPL libraries are imposed by this distribution.\nDynamic generated dictionary inputs were not retained in the original build artifacts.\n")
        filename = f"MozKey-macOS-Corresponding-Source-{version}.zip"
        candidate = root / filename
        deterministic_zip(stage, candidate)
        destination = args.release_dir / filename
        require(not destination.exists() or sha(destination) == sha(candidate), "Source asset already exists with different content")
        if not destination.exists():
            shutil.copy2(candidate, destination)
    sums = "".join(sha(f) + "  " + f.name + "\n" for f in sorted(args.release_dir.glob("*.zip")))
    (args.release_dir / "SHA256SUMS.txt").write_text(sums)


if __name__ == "__main__":
    main()
