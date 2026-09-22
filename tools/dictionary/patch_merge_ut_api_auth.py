"""Use optional CI authentication for merge-ut's GitHub commit lookup only."""
import argparse
from pathlib import Path

ORIGINAL = """    url = 'https://api.github.com/repos/google/mozc/commits/master'

    with urllib.request.urlopen(url) as response:"""
REPLACEMENT = """    url = 'https://api.github.com/repos/google/mozc/commits/master'

    # Mozkey CI: authenticate only this GitHub API request, not archive downloads.
    import os
    headers = {'User-Agent': 'mozkey-dictionary-builder'}
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:"""


def patch_source(content):
    if content.count(REPLACEMENT) == 1:
        return content
    if content.count(ORIGINAL) != 1:
        raise ValueError("merge-ut GitHub lookup changed; review the authentication patch")
    return content.replace(ORIGINAL, REPLACEMENT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    content = args.source.read_text(encoding="utf-8")
    patched = patch_source(content)
    if patched != content:
        args.source.write_text(patched, encoding="utf-8")


if __name__ == "__main__":
    main()
