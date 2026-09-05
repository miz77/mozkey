import copy
import tempfile
import unittest
from pathlib import Path
import zipfile

import prepare_macos_release as release
from fetch_macos_artifacts import extract_safe


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.run = {"repository": {"full_name": release.REPOSITORY}, "path": release.WORKFLOW,
                    "status": "completed", "conclusion": "success", "event": "workflow_dispatch",
                    "head_branch": "main", "head_sha": "a" * 40, "run_attempt": 1, "id": 42}
        self.jobs = {"total_count": 2, "jobs": [{"name": name, "run_id": 42, "run_attempt": 1,
                    "status": "completed", "conclusion": "success"} for name in release.JOBS]}
        self.artifacts = {"total_count": 2, "artifacts": [{"name": name, "id": i, "expired": False,
                          "workflow_run": {"id": 42, "head_sha": "a" * 40}} for i, name in enumerate((release.ARM, release.INTEL))]}

    def test_success(self):
        self.assertEqual(len(release.validate_metadata(self.run, self.jobs, self.artifacts)), 2)

    def test_bad_runs(self):
        for key, value in (("event", "pull_request"), ("conclusion", "failure"), ("status", "in_progress"),
                           ("head_branch", "other"), ("run_attempt", 2), ("path", "other.yml")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                release.validate_metadata(dict(self.run, **{key: value}), self.jobs, self.artifacts)

    def test_wrong_repository(self):
        self.run["repository"]["full_name"] = "koyasi777/mozkey"
        with self.assertRaises(ValueError):
            release.validate_metadata(self.run, self.jobs, self.artifacts)

    def test_bad_artifacts(self):
        for key, value in (("expired", True), ("name", "unknown"), ("workflow_run", {"id": 43, "head_sha": "b" * 40})):
            data = copy.deepcopy(self.artifacts)
            data["artifacts"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                release.validate_metadata(self.run, self.jobs, data)

    def test_failed_job(self):
        self.jobs["jobs"][0]["conclusion"] = "failure"
        with self.assertRaises(ValueError):
            release.validate_metadata(self.run, self.jobs, self.artifacts)

    def test_duplicate_contract(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "contract"
            path.write_text("a=1\na=2\n")
            with self.assertRaises(ValueError):
                release.contract(path)

    def test_deterministic_zip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stage = root / "stage"
            stage.mkdir()
            (stage / "file").write_text("hello")
            release.deterministic_zip(stage, root / "one.zip")
            (stage / "file").touch()
            release.deterministic_zip(stage, root / "two.zip")
            self.assertEqual(release.sha(root / "one.zip"), release.sha(root / "two.zip"))

    def test_unsafe_archives(self):
        for name in ("../escape", "/absolute", "a/../../escape", "C:/escape", "a\\escape"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                archive = Path(d) / "test.zip"
                with zipfile.ZipFile(archive, "w") as z:
                    z.writestr(name, "bad")
                with self.assertRaises(ValueError):
                    extract_safe(archive, Path(d) / "out")

    def test_zip_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "test.zip"
            info = zipfile.ZipInfo("link")
            info.external_attr = 0o120777 << 16
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr(info, "../escape")
            with self.assertRaises(ValueError):
                extract_safe(archive, Path(d) / "out")

    def test_safe_archive(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "test.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("audit/result.txt", "ok")
            extract_safe(archive, Path(d) / "out")
            self.assertEqual((Path(d) / "out/audit/result.txt").read_text(), "ok")


if __name__ == "__main__":
    unittest.main()
