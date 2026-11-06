#!/usr/bin/env python3
"""Read-only file inventory with SHA-256 hashes. Python 3.9+, standard library only.

  inventory.py --root home=$HOME --root apps=/Applications --output source-a.tsv

Each --root takes a label, used so paths line up across machines. Never follows
symlinks, never crosses a mount, never opens non-regular files, and never reads
cloud placeholders (which could trigger a download).

Output is tab-separated, with percent-encoded paths:
  type  status  size  mode  mtime  sha256  link_target  label/relative/path
type: f file, d dir, l link, o other, x excluded root (size and sha256 hold bytes and count)
status: ok, dataless, changed, mount, or err:<errno>
Comment lines: #START, #ROOT, and #END. A file with no #END didn't finish.
"""
import argparse
import errno
import fnmatch
import hashlib
import json
import os
import stat
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

SF_DATALESS = 0x40000000  # macOS: contents live in the cloud
SAFE = set(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/._-+=,@~ ()[]")
DEFAULT_EXCLUDES = [
    "Library/Caches", ".cache", ".npm/_cacache",
    "Library/Developer/Xcode/DerivedData", "Library/Developer/CoreSimulator/Caches",
    "go/pkg/mod/cache", "*/__pycache__", "__pycache__",
    # Credential stores are counted but never opened, even to hash them.
    "Library/Keychains", ".local/share/keyrings", ".local/share/kwalletd", ".gnupg", ".password-store",
]


def enc(raw):
    return "".join(chr(c) if c in SAFE else "%%%02X" % c for c in raw)


class Inventory:
    def __init__(self, out, excludes):
        self.out = out
        self.excludes = excludes
        self.lock = threading.Lock()
        self.slots = threading.BoundedSemaphore(2000)
        self.count = {"entries": 0, "files": 0, "bytes_hashed": 0, "errors": 0,
                      "dataless": 0, "changed": 0, "excluded_roots": 0}

    def emit(self, typ, status, size, mode, mtime, sha, link, key):
        line = "\t".join(str(x) for x in (typ, status, size, "%o" % mode, "%.6f" % mtime, sha, link, key))
        with self.lock:
            self.out.write(line + "\n")
            self.count["entries"] += 1

    def bump(self, name, amount=1):
        with self.lock:
            self.count[name] += amount

    def error(self, typ, exc, key):
        self.bump("errors")
        code = errno.errorcode.get(exc.errno, exc.errno)
        self.emit(typ, "err:%s" % code, 0, 0, 0, "-", "-", key)

    def hash_file(self, path, st, key):
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
        except OSError as exc:
            self.error("f", exc, key)
            return
        try:
            digest = hashlib.sha256()
            total = 0
            while True:
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    break
                digest.update(chunk)
                total += len(chunk)
            after = os.fstat(fd)
            status = "ok"
            if after.st_size != st.st_size or after.st_mtime != st.st_mtime or total != after.st_size:
                status = "changed"
                self.bump("changed")
            self.bump("files")
            self.bump("bytes_hashed", total)
            self.emit("f", status, after.st_size, stat.S_IMODE(after.st_mode), after.st_mtime,
                      digest.hexdigest(), "-", key)
        except OSError as exc:
            self.error("f", exc, key)
        finally:
            os.close(fd)

    def is_excluded(self, rel):
        text = os.fsdecode(rel)
        return any(fnmatch.fnmatchcase(text, pattern) for pattern in self.excludes)

    def tally(self, path):
        files = size = 0
        stack = [path]
        while stack:
            try:
                with os.scandir(stack.pop()) as entries:
                    for entry in entries:
                        try:
                            st = entry.stat(follow_symlinks=False)
                        except OSError:
                            continue
                        if stat.S_ISDIR(st.st_mode):
                            if not getattr(st, "st_flags", 0) & SF_DATALESS:
                                stack.append(entry.path)
                        else:
                            files += 1
                            size += st.st_size
            except OSError:
                pass
        return files, size

    def walk(self, label, root, pool):
        root_b = os.fsencode(root.rstrip("/") or "/")
        prefix = enc(label.encode())
        try:
            root_st = os.lstat(root_b)
        except OSError as exc:
            self.error("d", exc, prefix)
            return
        device = root_st.st_dev
        stack = [(root_b, b"", root_st)]

        def task(path, st, key):
            try:
                self.hash_file(path, st, key)
            except Exception:  # never lose a record silently
                self.bump("errors")
                self.emit("f", "err:python", 0, 0, 0, "-", "-", key)
            finally:
                self.slots.release()

        while stack:
            path, rel, st = stack.pop()
            key = prefix + ("/" + enc(rel) if rel else "")
            if rel and self.is_excluded(rel):
                files, size = self.tally(path)
                self.emit("x", "excluded", size, 0, 0, files, "-", key)
                self.bump("excluded_roots")
                continue
            if getattr(st, "st_flags", 0) & SF_DATALESS:
                self.bump("dataless")
                self.emit("d", "dataless", 0, stat.S_IMODE(st.st_mode), st.st_mtime, "-", "-", key)
                continue
            if st.st_dev != device:
                self.emit("d", "mount", 0, stat.S_IMODE(st.st_mode), st.st_mtime, "-", "-", key)
                continue
            try:
                with os.scandir(path) as listing:
                    names = sorted(entry.name for entry in listing)
            except OSError as exc:
                self.error("d", exc, key)
                continue
            self.emit("d", "ok", 0, stat.S_IMODE(st.st_mode), st.st_mtime, "-", "-", key)
            for name in names:
                child = os.path.join(path, name)
                child_rel = os.path.join(rel, name) if rel else name
                child_key = prefix + "/" + enc(child_rel)
                try:
                    cst = os.lstat(child)
                except OSError as exc:
                    self.error("?", exc, child_key)
                    continue
                mode = cst.st_mode
                if stat.S_ISDIR(mode):
                    stack.append((child, child_rel, cst))
                elif stat.S_ISLNK(mode):
                    try:
                        target = enc(os.readlink(child))
                    except OSError:
                        target = "err"
                    self.emit("l", "ok", cst.st_size, stat.S_IMODE(mode), cst.st_mtime, "-", target, child_key)
                elif stat.S_ISREG(mode):
                    if self.is_excluded(child_rel):
                        self.emit("x", "excluded", cst.st_size, 0, 0, 1, "-", child_key)
                        self.bump("excluded_roots")
                    elif getattr(cst, "st_flags", 0) & SF_DATALESS:
                        self.bump("dataless")
                        self.emit("f", "dataless", cst.st_size, stat.S_IMODE(mode), cst.st_mtime, "-", "-", child_key)
                    else:
                        self.slots.acquire()
                        pool.submit(task, child, cst, child_key)
                else:
                    self.emit("o", "ok", 0, stat.S_IMODE(mode), cst.st_mtime, "-", "-", child_key)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", action="append", required=True, help="label=/path")
    parser.add_argument("--output", required=True)
    parser.add_argument("--exclude", action="append", default=[], help="extra glob, relative to the root")
    parser.add_argument("--no-default-excludes", action="store_true")
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 4))
    args = parser.parse_args()

    roots = []
    for item in args.root:
        label, sep, path = item.partition("=")
        if not sep or not label or not path:
            parser.error("--root needs label=/path, got %r" % item)
        if not os.path.exists(path):
            parser.error("root doesn't exist: %s" % path)
        roots.append((label, path))

    excludes = args.exclude + ([] if args.no_default_excludes else DEFAULT_EXCLUDES)
    tmp = args.output + ".partial"
    with open(tmp, "w", encoding="ascii") as out:
        out.write("#START\t%s\t%s\n" % (os.uname().nodename, time.strftime("%Y-%m-%dT%H:%M:%S%z")))
        inventory = Inventory(out, excludes)
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for label, path in roots:
                out.write("#ROOT\t%s\t%s\n" % (enc(label.encode()), enc(os.fsencode(path))))
                inventory.walk(label, path, pool)
        out.write("#END\t%s\n" % json.dumps(inventory.count, sort_keys=True))
    os.replace(tmp, args.output)
    print(json.dumps(inventory.count, sort_keys=True))
    if inventory.count["entries"] == 0:
        print("warning: nothing was inventoried, so check the --root paths", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
