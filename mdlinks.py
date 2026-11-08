#!/usr/bin/env python3
"""mdlinks: find broken local links in Markdown. Python 3, no dependencies.
Usage: python3 mdlinks.py [DIR_OR_FILE ...]     (default: current dir)
Checks [text](path), [ref]: path, and #anchors (GitHub heading slugs,
<a id>, {#id}). A missing x.html is looked up as x.md (mdBook).
Skips URLs and code. Exit 1 if broken or on a bad argument. CC0.
"""
import re
import sys
from pathlib import Path
from urllib.parse import unquote

LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
REF = re.compile(r"^\s{0,3}\[[^\]^][^\]]*\]:\s*<?(\S+?)>?(?:\s|$)")
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
FENCE = re.compile(r"^\s{0,3}(```|~~~)")


def body_lines(path, code=False):
    """Lines outside fenced code; inline code removed unless code=True."""
    fenced = False
    for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            yield n, line if code else re.sub(r"`[^`]*`", "", line)


def slug(heading):
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors(path, cache={}):
    if path not in cache:
        seen, out = {}, set()
        for _, line in body_lines(path, code=True):
            out.update(re.findall(r"<a\s[^>]*(?:name|id)=[\"']([^\"']+)", line))
            m = re.match(r"^[\s>]{0,8}#{1,6}\s+(.*?)\s*#*\s*$", line)
            if m:
                head = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", m.group(1))
                head = re.sub(r"[`*]|(?<!\w)_|_(?!\w)", "", head)
                custom = re.search(r"\s*\{#([^}\s]+)\}$", head)
                s = custom.group(1) if custom else slug(head)
                k = seen[s] = seen.get(s, -1) + 1
                out.add(s if k == 0 else f"{s}-{k}")
        cache[path] = out
    return cache[path]


def check(md, root):
    for n, line in body_lines(md):
        for target in (t for t in LINK.findall(line) + REF.findall(line)
                       if not SCHEME.match(t)):
            part, _, anchor = unquote(target).partition("#")
            base = root if part.startswith("/") else md.parent
            dest = (base / part.split("?")[0].lstrip("/")).resolve() if part else md
            if dest.suffix == ".html" and not dest.exists():  # mdBook style
                dest = dest.with_suffix(".md")
            if not dest.exists():
                yield f"{md}:{n}: missing {target}"
            elif anchor and dest.suffix == ".md" and anchor.lower() not in anchors(dest):
                yield f"{md}:{n}: no heading #{anchor} in {dest.name}"


def main(args):
    if any(a.startswith("-") for a in args) or not all(map(Path.exists, map(Path, args))):
        sys.exit(__doc__)
    bad = 0
    for root in map(Path, args or ["."]):
        mds = [root] if root.is_file() else sorted(root.rglob("*.md"))
        for md in (m for m in mds if not {".git", "node_modules"} & set(m.parts)):
            for problem in check(md, root if root.is_dir() else md.parent):
                print(problem)
                bad += 1
    print(f"mdlinks: {bad} broken link(s)", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
