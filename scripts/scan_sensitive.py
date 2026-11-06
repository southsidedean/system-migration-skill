#!/usr/bin/env python3
"""Search names and contents for terms. Reports paths and counts, never matching text.
Python 3.8+, standard library only.

  scan_sensitive.py --root $HOME --terms terms.txt --output scan.tsv

The terms file holds one case-insensitive term per line. Built-in patterns also flag
likely secrets by name and content. A self-test runs first; if it can't find a planted
match, the scan refuses to run, because a broken search looks exactly like a clean one.

Output is tab-separated: kind  location  term  count  size  percent-encoded path
kind: match, or not-searched (the location column gives the reason).
Files in formats it can't read are reported as not-searched, not as clean.
"""
import argparse
import json
import os
import re
import stat
import sys
import tarfile
import tempfile
import zipfile

SF_DATALESS = 0x40000000
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
UNREADABLE_FORMATS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".key", ".pages", ".numbers",
    ".jpg", ".jpeg", ".png", ".gif", ".heic", ".tif", ".tiff", ".bmp", ".webp",
    ".mp3", ".mp4", ".mov", ".m4a", ".flac", ".wav", ".mkv", ".avi", ".dmg", ".iso",
    ".7z", ".rar", ".gpg", ".age", ".enc", ".sqlite", ".db",
}
ARCHIVES = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")
SECRET_NAMES = re.compile(
    rb"(^|/)(\.env(\.[^/]*)?|id_rsa|id_ed25519|id_ecdsa|credentials|kubeconfig|[^/]*\.pem|[^/]*\.p12|[^/]*\.pfx)$",
    re.I,
)
SECRET_CONTENT = {
    "builtin:private-key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "builtin:aws-access-key-id": re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
}
SAFE = set(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/._-+=,@~ ()[]")
BOM = (b"\xff\xfe", b"\xfe\xff")


def enc(raw):
    return "".join(chr(c) if c in SAFE else "%%%02X" % c for c in raw)


def compile_terms(terms):
    return {term: re.compile(re.escape(term.encode()), re.I) for term in terms}


def count_content(path, patterns, chunk_size=1 << 20, overlap=256):
    """Count matches across chunks. Returns None if the file looks binary."""
    counts = {}
    previous = b""
    with open(path, "rb", buffering=0) as handle:
        first = True
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            if first:
                first = False
                if chunk.startswith(BOM):
                    chunk = chunk.decode("utf-16", "ignore").encode()
                elif b"\0" in chunk[:8192]:
                    return None
            data = previous + chunk
            limit = len(previous)
            for name, pattern in patterns.items():
                # Count each match once: only those ending past the overlap region.
                found = sum(1 for m in pattern.finditer(data) if m.end() > limit)
                if found:
                    counts[name] = counts.get(name, 0) + found
            previous = data[-overlap:]
    return counts


def archive_names(path):
    """Return member names, or None if the archive can't be listed."""
    lower = path.lower()
    try:
        if lower.endswith(b".zip"):
            with zipfile.ZipFile(os.fsdecode(path)) as archive:
                return [name.encode("utf-8", "surrogateescape") for name in archive.namelist()]
        with tarfile.open(os.fsdecode(path)) as archive:
            return [name.encode("utf-8", "surrogateescape") for name in archive.getnames()]
    except Exception:
        return None


def self_test():
    """Prove that the search finds a planted match in each place it claims to look."""
    canary = "zzcanaryterm"
    patterns = compile_terms([canary])
    with tempfile.TemporaryDirectory() as tmp:
        text = os.path.join(tmp, "plain.txt")
        with open(text, "w") as handle:
            handle.write("before ZZCANARYTERM after zzcanaryterm\n")
        counts = count_content(text, patterns)
        boundary = os.path.join(tmp, "boundary.txt")
        with open(boundary, "wb") as handle:
            handle.write(b"x" * ((1 << 20) - 5) + canary.encode() + b"\n")
        crossing = count_content(boundary, patterns)
        packed = os.path.join(tmp, "packed.zip")
        with zipfile.ZipFile(packed, "w") as archive:
            archive.writestr("zzcanaryterm-inside.txt", "x")
        names = archive_names(os.fsencode(packed)) or []
    return (counts == {canary: 2}
            and crossing == {canary: 1}
            and any(patterns[canary].search(name) for name in names))


def scan(root, patterns, output, max_size):
    totals = {"files_seen": 0, "content_searched": 0, "matches": 0, "not_searched": 0}
    names_only = {k: v for k, v in patterns.items() if not k.startswith("builtin:")}

    def write(kind, location, term, count, size, path):
        output.write("\t".join(str(x) for x in (kind, location, term, count, size, enc(path))) + "\n")
        totals["matches" if kind == "match" else "not_searched"] += 1

    def skipped(reason, size, path):
        write("not-searched", reason, "-", 0, size, path)

    stack = [os.fsencode(root)]
    while stack:
        directory = stack.pop()
        try:
            with os.scandir(directory) as listing:
                entries = sorted(listing, key=lambda e: e.name)
        except OSError as exc:
            skipped("unreadable-dir:%s" % exc.errno, 0, directory)
            continue
        for entry in entries:
            path = entry.path
            name = entry.name
            try:
                st = entry.stat(follow_symlinks=False)
            except OSError as exc:
                skipped("unreadable:%s" % exc.errno, 0, path)
                continue
            for term, pattern in names_only.items():
                if pattern.search(name):
                    write("match", "name", term, 1, st.st_size, path)
            if stat.S_ISLNK(st.st_mode):
                continue
            if stat.S_ISDIR(st.st_mode):
                if name in {s.encode() for s in SKIP_DIRS}:
                    skipped("skipped-dir", 0, path)
                elif getattr(st, "st_flags", 0) & SF_DATALESS:
                    skipped("cloud-placeholder", 0, path)
                else:
                    stack.append(path)
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            totals["files_seen"] += 1
            if SECRET_NAMES.search(path):
                write("match", "name", "builtin:secret-filename", 1, st.st_size, path)
            if getattr(st, "st_flags", 0) & SF_DATALESS:
                skipped("cloud-placeholder", st.st_size, path)
                continue
            lower = name.lower()
            if lower.endswith(tuple(a.encode() for a in ARCHIVES)):
                members = archive_names(path)
                if members is None:
                    skipped("archive-unlistable", st.st_size, path)
                else:
                    for term, pattern in names_only.items():
                        hits = sum(1 for member in members if pattern.search(member))
                        if hits:
                            write("match", "archive-member-name", term, hits, st.st_size, path)
                    skipped("archive-contents-not-searched", st.st_size, path)
                continue
            if os.path.splitext(lower)[1].decode("utf-8", "ignore") in UNREADABLE_FORMATS:
                skipped("format", st.st_size, path)
                continue
            if max_size and st.st_size > max_size:
                skipped("too-large", st.st_size, path)
                continue
            try:
                counts = count_content(path, patterns)
            except OSError as exc:
                skipped("unreadable:%s" % exc.errno, st.st_size, path)
                continue
            if counts is None:
                skipped("binary", st.st_size, path)
                continue
            totals["content_searched"] += 1
            for term, count in sorted(counts.items()):
                write("match", "content", term, count, st.st_size, path)
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", action="append", required=True)
    parser.add_argument("--terms", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-size-mb", type=int, default=200, help="0 means no limit")
    args = parser.parse_args()

    with open(args.terms, encoding="utf-8") as handle:
        terms = [line.strip() for line in handle if line.strip() and not line.startswith("#")]
    if not terms:
        parser.error("the terms file is empty, so the scan would look clean without searching")
    if not self_test():
        print("SELF-TEST FAILED: the search can't find planted matches. Not scanning.", file=sys.stderr)
        return 3
    patterns = compile_terms(terms)
    patterns.update(SECRET_CONTENT)
    for root in args.root:
        if not os.path.isdir(root):
            parser.error("root isn't a folder: %s" % root)

    tmp = args.output + ".partial"
    results = []
    with open(tmp, "w", encoding="ascii") as out:
        out.write("kind\tlocation\tterm\tcount\tsize\tpath\n")
        for root in args.root:
            results.append(scan(root, patterns, out, args.max_size_mb << 20))
    os.replace(tmp, args.output)
    print(json.dumps({"self_test": "passed", "terms": len(terms), "roots": args.root, "results": results}))
    if not any(r["files_seen"] for r in results):
        print("warning: no files were seen, so check the --root paths", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
