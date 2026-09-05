#!/usr/bin/env python3
"""Prepare a deterministic release from a verified fork run; never install a PKG."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

REPOSITORY = "miz77/mozkey"
WORKFLOW = ".github/workflows/macos_zenz_formal_package_dual_native.yml"
PACKAGE = "Mozc_Zenz_Universal_formal_dev.pkg"
ARM = "mozkey-zenz-formal-universal-package"
INTEL = "mozkey-zenz-formal-native-intel-audit"
JOBS = {"Build formal PKG and verify on Apple Silicon", "Verify same formal PKG on native Intel"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def contract(path):
    result = {}
    for line in path.read_text().splitlines():
        key, sep, value = line.partition("=")
        require(sep and key not in result, "Malformed or duplicate contract field")
        result[key] = value
    return result


def validate_metadata(run, jobs, artifacts):
    require(run["repository"]["full_name"] == REPOSITORY, "Wrong repository")
    require(run["path"] == WORKFLOW, "Wrong workflow")
    require(run["status"] == "completed" and run["conclusion"] == "success", "Unsuccessful run")
    require(run["event"] in ("push", "workflow_dispatch") and run["head_branch"] == "main", "Untrusted event/branch")
    require(not run.get("pull_requests"), "PR-derived run")
    require(run["run_attempt"] == 1, "Initial implementation requires a fresh run, not a rerun")
    require(re.fullmatch(r"[0-9a-f]{40}", run["head_sha"]), "Invalid source SHA")
    require(jobs["total_count"] == len(jobs["jobs"]), "Incomplete job listing")
    for name in JOBS:
        matches = [j for j in jobs["jobs"] if j["name"] == name]
        require(len(matches) == 1, "Missing or duplicate job: " + name)
        job = matches[0]
        require(job["run_id"] == run["id"] and job["run_attempt"] == 1, "Job/run mismatch")
        require(job["status"] == "completed" and job["conclusion"] == "success", "Failed job")
    require(artifacts["total_count"] == len(artifacts["artifacts"]), "Incomplete artifact listing")
    selected = []
    for name in (ARM, INTEL):
        matches = [a for a in artifacts["artifacts"] if a["name"] == name]
        require(len(matches) == 1 and not matches[0]["expired"], "Missing, duplicate or expired artifact")
        a = matches[0]
        require(a["workflow_run"]["id"] == run["id"] and a["workflow_run"]["head_sha"] == run["head_sha"], "Artifact/run mismatch")
        selected.append({"id": a["id"], "name": name})
    return selected


def command(*args, check=True):
    r = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check:
        require(r.returncode == 0, "Command failed: " + " ".join(args) + "\n" + r.stdout)
    return r.stdout


def inspect_package(pkg, expanded):
    command("pkgutil", "--expand-full", str(pkg), str(expanded))
    infos = list(expanded.glob("*.pkg/PackageInfo"))
    require(len(infos) == 1, "Unexpected component package count")
    info = ET.parse(infos[0]).getroot()
    require(info.get("identifier") == "org.mozc.pkg.JapaneseInput", "Unexpected receipt")
    payload = infos[0].parent / "Payload"
    app = payload / "Library/Input Methods/Mozc.app"
    plist = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    require(plist["CFBundleIdentifier"] == "org.mozc.inputmethod.Japanese", "Unexpected bundle ID")
    binaries = []
    for p in sorted(payload.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        with p.open("rb") as f:
            magic = f.read(4)
        if magic not in (b"\xca\xfe\xba\xbe", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbf"):
            continue
        arch = command("lipo", "-archs", str(p)).strip()
        require(set(arch.split()) == {"arm64", "x86_64"}, "Non-universal binary: " + str(p))
        commands = command("otool", "-l", str(p))
        # Only deployment target commands, not dylib versions.
        targets = re.findall(r"cmd LC_(?:BUILD_VERSION|VERSION_MIN_MACOSX)\b(.*?)(?=Load command|\Z)", commands, re.S)
        minimums = [re.search(r"\b(?:minos|version)\s+(\S+)", t).group(1) for t in targets]
        require(minimums and all(tuple(map(int, v.split("."))) <= (12, 0, 0) for v in minimums), "Unexpected deployment target")
        signature = command("codesign", "-d", "--verbose=2", str(p)).replace(str(expanded), "<expanded-pkg>")
        command("codesign", "--verify", "--strict", str(p))
        binaries.append({"path": str(p.relative_to(payload)), "architectures": arch.split(), "minimum_macos": minimums, "signature": signature})
    require(binaries, "No Mach-O binaries")
    scripts = {p.name: p.read_text() for p in sorted((infos[0].parent / "Scripts").iterdir()) if p.is_file()}
    audit = {"receipt": info.get("identifier"), "install_path": "/Library/Input Methods/Mozc.app", "bundle_id": plist["CFBundleIdentifier"], "app_version": plist["CFBundleVersion"], "installer_signature": command("pkgutil", "--check-signature", str(pkg), check=False), "notarization": "Not performed by this distribution", "binaries": binaries, "installer_scripts": scripts, "gui_test": "Not performed"}
    return audit, app, infos[0].parent


def deterministic_zip(root, destination):
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(root.rglob("*")):
            require(not p.is_symlink(), "Unexpected symlink in release")
            if p.is_file():
                info = zipfile.ZipInfo(str(p.relative_to(root)), (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                with p.open("rb") as src, z.open(info, "w") as dst:
                    shutil.copyfileobj(src, dst)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(re.fullmatch(r"20\d{2}\.\d{2}\.\d{2}\.[1-9]\d*", args.version), "Invalid distribution version")
    source = Path(__file__).resolve().parents[2]
    metadata = args.artifacts / "metadata"
    run, jobs, artifacts = [json.loads((metadata / (n + ".json")).read_text()) for n in ("run", "jobs", "artifacts")]
    selected = validate_metadata(run, jobs, artifacts)
    arm, intel = args.artifacts / ARM, args.artifacts / INTEL
    c = contract(arm / "ARTIFACT-CONTRACT.txt")
    require(c == contract(intel / "ARTIFACT-CONTRACT.txt"), "ARM/Intel contract mismatch")
    require(c["source_commit"] == run["head_sha"], "Source SHA mismatch")
    require(sha(arm / PACKAGE) == c["package_sha256"], "PKG hash mismatch")
    require(sha(arm / "BUILD-CONTRACT.txt") == c["build_contract_sha256"], "BUILD-CONTRACT hash mismatch")
    # Permit only distribution tooling/docs to differ from the adopted source.
    changed = command("git", "-C", str(source), "diff", "--name-only", run["head_sha"]).splitlines()
    allowed = ("tools/packaging/", "docs/macos-distribution.md", "docs/macos-third-party-notices.md", ".github/workflows/publish-macos.yml")
    require(all(name.startswith(allowed) for name in changed), "Non-distribution changes from build source")
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        audit, app, component = inspect_package(arm / PACKAGE, root / "expanded")
        require((component / "Scripts/preinstall").read_bytes() == (source / "src/mac/installer/preflight_template.sh").read_bytes(), "Unexpected preinstall script")
        require((component / "Scripts/postinstall").read_bytes() == (source / "src/mac/installer/postflight_template.sh").read_bytes(), "Unexpected postinstall script")
        build = contract(arm / "BUILD-CONTRACT.txt")
        runtime = app / "Contents/Resources/ZenzRuntime"
        require(sha(runtime / "BUILD-CONTRACT.txt") == c["build_contract_sha256"], "Embedded contract mismatch")
        require(sha(runtime / "models" / build["model_output_file"]) == build["model_sha256"], "Model hash mismatch")
        stage = root / "stage"
        (stage / "audit").mkdir(parents=True)
        (stage / "LICENSES").mkdir()
        shutil.copy2(arm / PACKAGE, stage / PACKAGE)
        for name in ("ARTIFACT-CONTRACT.txt", "BUILD-CONTRACT.txt", "arm64-audit.txt"):
            shutil.copy2(arm / name, stage / "audit" / name)
        shutil.copy2(intel / "intel-audit.txt", stage / "audit/intel-audit.txt")
        shutil.copytree(metadata, stage / "audit/github")
        shutil.copytree(runtime / "licenses", stage / "LICENSES/ZenzRuntime")
        shutil.copy2(source / "LICENSE", stage / "LICENSES/MozKey-Mozc.txt")
        shutil.copy2(source / "THIRD_PARTY_NOTICES.md", stage / "LICENSES/UPSTREAM_THIRD_PARTY_NOTICES.md")
        shutil.copy2(app / "Contents/Resources/credits_en.html", stage / "LICENSES/credits_en.html")
        shutil.copy2(source / "docs/macos-distribution.md", stage / "README-macos.txt")
        shutil.copy2(source / "docs/macos-third-party-notices.md", stage / "THIRD_PARTY_NOTICES.md")
        (stage / "audit/package-inspection.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
        provenance = {"upstream_repository": "koyasi777/mozkey", "upstream_commit": run["head_sha"], "build_repository": REPOSITORY, "build_commit": run["head_sha"], "build_workflow": WORKFLOW, "build_run_id": run["id"], "build_run_attempt": run["run_attempt"], "artifacts": selected, "distribution_version": args.version, "package_filename": PACKAGE, "package_sha256": c["package_sha256"], "build_contract_sha256": c["build_contract_sha256"], "dictionary_profile": "daily", "dictionary_input_revisions": None, "dictionary_note": "Dynamic input revisions/hashes were not retained by this upstream workflow; do not infer them from current upstream HEAD.", "runtime_contract": build, "package_inspection": "audit/package-inspection.json", "gui_test": "Not performed", "licenses_review": "See THIRD_PARTY_NOTICES.md; dictionary redistribution review remains open."}
        encoded = json.dumps(provenance, indent=2, ensure_ascii=False) + "\n"
        (stage / "provenance.json").write_text(encoded)
        filename = "MozKey-macOS-Universal-" + args.version + ".zip"
        candidate = root / filename
        deterministic_zip(stage, candidate)
        target = args.output / filename
        require(not target.exists() or sha(target) == sha(candidate), "Existing version differs; use a new version")
        if not target.exists():
            shutil.copy2(candidate, target)
        (args.output / "provenance.json").write_text(encoded)
        (args.output / "SHA256SUMS.txt").write_text(sha(target) + "  " + filename + "\n")
        print(json.dumps({"zip": str(target), "sha256": sha(target), "package_sha256": c["package_sha256"], "audited_binaries": len(audit["binaries"])}, indent=2))


if __name__ == "__main__":
    main()
