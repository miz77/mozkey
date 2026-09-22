import os
import unittest
from unittest.mock import patch
import urllib.request

from patch_merge_ut_api_auth import ORIGINAL, REPLACEMENT, patch_source


class ApiAuthenticationTests(unittest.TestCase):
    def request(self, token):
        source = "def fetch():\n" + ORIGINAL + "\n        return response.read()\n"
        namespace = {"urllib": __import__("urllib")}
        with patch.dict(os.environ, {"GITHUB_TOKEN": token}, clear=True), \
                patch("urllib.request.urlopen") as urlopen:
            exec(patch_source(source), namespace)
            namespace["fetch"]()
            return urlopen.call_args

    def test_authenticated_request_is_to_github_api(self):
        args, kwargs = self.request("test-token")
        self.assertEqual(args[0].full_url, "https://api.github.com/repos/google/mozc/commits/master")
        self.assertEqual(args[0].get_header("Authorization"), "Bearer test-token")
        self.assertEqual(kwargs["timeout"], 60)

    def test_local_build_without_token_remains_unauthenticated(self):
        args, _ = self.request("")
        self.assertIsNone(args[0].get_header("Authorization"))

    def test_idempotent_and_preserves_archive_download(self):
        archive = "\n    urllib.request.urlretrieve(archive_url, archive_path)\n"
        patched = patch_source(ORIGINAL + archive)
        self.assertEqual(patch_source(patched), patched)
        self.assertTrue(patched.endswith(archive))
        self.assertEqual(patched.count(REPLACEMENT), 1)

    def test_changed_or_ambiguous_upstream_code_requires_review(self):
        for source in ("unrecognized lookup", ORIGINAL + ORIGINAL):
            with self.subTest(source=source), self.assertRaises(ValueError):
                patch_source(source)


if __name__ == "__main__":
    unittest.main()
