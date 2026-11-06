#!/usr/bin/env python3
"""Compare inventories from inventory.py. Python 3.9+, standard library only.

  compare.py --source a.tsv --dest b.tsv --output compare-a
  compare.py --conflicts a.tsv b.tsv c.tsv --output conflicts

Comparing writes <output>/summary.json and <output>/classified.tsv, classifying
every source file. Exits 2 if an inventory is incomplete or the counts don't
reconcile. Exit 0 means the comparison is sound, not that the copy is complete,
so read the summary.

Conflict mode lists paths that hold different content across sources.
"""
import argparse
import collections
import json
import os
import sys

CLASSES = ["identical", "moved", "different", "missing", "blocked", "unverified", "type-mismatch"]
MIN_MOVE_SIZE = 64  # smaller matches are too likely to be a coincidence


def load(path):
    """Return {key: (type, status, size, sha)} and the #END counts. Refuses partial files."""
    entries = {}
    end = None
    with open(path, encoding="ascii") as handle:
        for line in handle:
            text = line.rstrip("\n")
            if text.startswith("#END\t"):
                end = json.loads(text.split("\t", 1)[1])
            elif text.startswith("#") or not text:
                continue
            else:
                fields = text.split("\t")
                if len(fields) != 8:
                    raise SystemExit("%s: malformed line: %r" % (path, text[:120]))
                typ, status, size, _mode, _mtime, sha, _link, key = fields
                entries[key] = (typ, status, int(size), sha)
    if end is None:
        raise SystemExit("%s: no #END line, so the inventory didn't finish" % path)
    if len(entries) != end["entries"]:
        raise SystemExit("%s: has %d entries but #END says %d" % (path, len(entries), end["entries"]))
    return entries, end


def blocked_ancestor(key, blocked):
    parts = key.split("/")
    return any("/".join(parts[:i]) in blocked for i in range(1, len(parts)))


def hashable(entry):
    return entry[0] == "f" and entry[1] in ("ok",) and len(entry[3]) == 64


def classify(source, dest):
    blocked = {k for k, e in dest.items() if e[1].startswith("err:") or e[1] in ("dataless", "mount", "excluded")}
    hashes: dict = {}
    for key, entry in dest.items():
        if hashable(entry):
            hashes.setdefault(entry[3], key)

    rows = []
    for key, entry in source.items():
        if entry[0] != "f":
            continue
        other = dest.get(key)
        where = "-"
        if not hashable(entry):
            verdict = "unverified"
        elif other is None:
            if blocked_ancestor(key, blocked):
                verdict = "blocked"
            elif entry[2] >= MIN_MOVE_SIZE and entry[3] in hashes:
                verdict, where = "moved", hashes[entry[3]]
            else:
                verdict = "missing"
        elif other[0] != "f":
            verdict = "blocked" if other[1] in ("excluded", "dataless", "mount") else "type-mismatch"
        elif not hashable(other):
            verdict = "blocked" if other[1].startswith("err:") else "unverified"
        elif other[3] == entry[3]:
            verdict = "identical"
        else:
            verdict = "different"
        rows.append((verdict, entry[2], key, where))
    return rows, blocked


def empty_dirs(source, dest, blocked):
    """Directories with files on the source but none at the destination."""
    def file_parents(entries):
        seen = set()
        for key, entry in entries.items():
            if entry[0] == "f":
                parts = key.split("/")
                for i in range(1, len(parts)):
                    seen.add("/".join(parts[:i]))
        return seen

    source_full = file_parents(source)
    dest_full = file_parents(dest)
    found = []
    for key, entry in dest.items():
        if entry[0] == "d" and key in source_full and key not in dest_full and key not in blocked:
            found.append(key)
    # Report the deepest folders only; their parents are empty as a consequence.
    return sorted(k for k in found if not any(o.startswith(k + "/") for o in found))


def run_compare(args):
    source, source_end = load(args.source)
    dest, dest_end = load(args.dest)
    rows, blocked = classify(source, dest)

    totals = collections.Counter(row[0] for row in rows)
    source_files = sum(1 for e in source.values() if e[0] == "f")
    classified = sum(totals.values())
    summary = {
        "source_files": source_files,
        "classified": classified,
        "classes": {name: totals.get(name, 0) for name in CLASSES},
        "bytes_missing": sum(row[1] for row in rows if row[0] == "missing"),
        "dest_only_files": sum(1 for k, e in dest.items() if e[0] == "f" and k not in source),
        "empty_dirs_at_dest": empty_dirs(source, dest, blocked),
        "dest_unreadable_roots": sorted(k for k in blocked if dest[k][1].startswith("err:")),
        "source_counts": source_end,
        "dest_counts": dest_end,
    }
    os.makedirs(args.output, exist_ok=True)
    with open(os.path.join(args.output, "classified.tsv"), "w", encoding="ascii") as out:
        out.write("class\tsize\tpath\tfound_at\n")
        for row in sorted(rows):
            out.write("\t".join(str(x) for x in row) + "\n")
    with open(os.path.join(args.output, "summary.json"), "w", encoding="ascii") as out:
        json.dump(summary, out, indent=2, sort_keys=True)

    print(json.dumps({k: summary[k] for k in ("source_files", "classified", "classes", "dest_only_files")}, sort_keys=True))
    if summary["empty_dirs_at_dest"]:
        print("EMPTY AT DESTINATION: %d folder(s), listed in summary.json" % len(summary["empty_dirs_at_dest"]))
    if classified != source_files or source_files == 0:
        print("COUNTS DON'T RECONCILE: %d source files, %d classified" % (source_files, classified), file=sys.stderr)
        return 2
    return 0


def run_conflicts(args):
    seen: dict = collections.defaultdict(dict)
    for path in args.conflicts:
        entries, _ = load(path)
        label = os.path.basename(path)
        for key, entry in entries.items():
            if entry[0] == "f":
                seen[key][label] = entry[3] if hashable(entry) else "unhashed"

    os.makedirs(args.output, exist_ok=True)
    conflicts = same = single = 0
    with open(os.path.join(args.output, "conflicts.tsv"), "w", encoding="ascii") as out:
        out.write("path\tsources\n")
        for key in sorted(seen):
            values = seen[key]
            if len(values) == 1:
                single += 1
            elif len(set(values.values())) == 1 and "unhashed" not in values.values():
                same += 1
            else:
                conflicts += 1
                out.write("%s\t%s\n" % (key, ",".join(sorted(values))))
    print(json.dumps({"paths": len(seen), "conflicts": conflicts, "same_everywhere": same, "one_source_only": single}, sort_keys=True))
    return 2 if not seen else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source")
    parser.add_argument("--dest")
    parser.add_argument("--conflicts", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.conflicts:
        return run_conflicts(args)
    if args.source and args.dest:
        return run_compare(args)
    parser.error("give --source and --dest, or --conflicts")


if __name__ == "__main__":
    sys.exit(main())
