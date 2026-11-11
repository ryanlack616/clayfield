#!/usr/bin/env python3
"""Check every relative markdown link in a tree resolves on disk.

Usage:
    python3 scripts/check_md_links.py [root]

Prints one `MISS <file> -> <target>` line per broken link and a summary line
`files=N broken=M` first. Exit 1 if any link is broken, 0 otherwise.
Read-only: opens files, writes nothing.

Why a script and not a grep: a markdown link's target is relative to the file
that contains it, so a correct check needs each file's own directory. A
repo-wide grep for the target string reports false misses for the same reason.

Vendor trees are skipped: node_modules ships its own READMEs whose relative
links point at files the packager did not publish, and they are not ours to fix.
"""

import argparse
import os
import re
import sys

LINK = re.compile(r"\]\(([^)\s]+)\)")
SCHEME_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:", "#")

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "target",
    ".pnpm",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "coverage",
}


def iter_md(root: str, ext: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(ext):
                yield os.path.join(dirpath, name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--ext", default=".md", help="file extension to scan")
    args = ap.parse_args()

    files = sorted(iter_md(args.root, args.ext))
    broken = []
    for path in files:
        base = os.path.dirname(path)
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as exc:
            broken.append((os.path.relpath(path, args.root), f"<unreadable: {exc}>"))
            continue
        for match in LINK.finditer(text):
            target = match.group(1)
            if target.startswith(SCHEME_PREFIXES):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = os.path.normpath(os.path.join(base, target))
            if not os.path.exists(resolved):
                broken.append((os.path.relpath(path, args.root), match.group(1)))

    print(f"files={len(files)} broken={len(broken)}")
    for src, target in broken:
        print(f"MISS {src} -> {target}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
