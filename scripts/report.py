#!/usr/bin/env python3
"""Summarize a discovery run, so nobody has to write this analysis by hand. Python 3.9+, standard library only.

  report.py --dir <migration folder> --source source [--dest dest]

Reads discovery/<label>.tsv, .json, and -scan.tsv, as written by `migrate.py discover`.
Prints a short summary, and writes every path to discovery/report-<source>.json.
Reports paths, sizes, and counts, never file contents. It classifies by path only: a person
still decides what's sensitive, and "system data" doesn't mean safe to lose.
"""
import argparse
import collections
import json
import os
import re
import sys
import urllib.parse

from compare import classify, load

NOISE = {".DS_Store", ".localized", ".CFUserTextEncoding"}
MEDIA_LIBRARY = re.compile(r"\.(photoslibrary|musiclibrary|tvlibrary|imovielibrary)(/|$)|^home/(Music/Music|Movies/TV)(/|$)")
# Installed tools and their caches, which can be reinstalled. Counted by folder, so they don't bury the user's files.
TOOL_FOLDER = re.compile(r"^(?:home/)?(\.cache|\.npm|\.rbenv|\.pyenv|\.nvm|\.cargo|\.rustup|\.gem|\.gradle|\.m2|\.claude/plugins)(/|$)|(^|/)node_modules(/|$)")
MAX_ROWS = 25
MAX_WIDTH = 170
PACKAGE_LISTS = ("applications", "brew_formulae", "brew_casks", "brew_taps", "brew_services", "mas", "npm_global", "pipx",
                 "vscode_extensions", "apt_manual", "dnf_user", "pacman_explicit", "flatpak", "snap")


def show(key):
    """A readable path, unless decoding it would print control characters."""
    text = urllib.parse.unquote(key)
    return key if any(ord(c) < 32 or ord(c) == 127 for c in text) else text


def kind_of(key):
    parts = key.split("/")
    if parts[-1] in NOISE:
        return "noise"
    if parts[0] != "home":
        return "apps" if parts[0] == "apps" else "user"
    if (len(parts) > 1 and parts[1] in ("Library", ".Trash")) or MEDIA_LIBRARY.search(key):
        return "system"
    return "tools" if TOOL_FOLDER.search(key) else "user"


def group_of(key, kind):
    parts = key.split("/")
    return "/".join(parts[:3] if kind != "apps" else parts[:2])


def load_roots(path):
    roots = []
    with open(path, encoding="ascii") as handle:
        for line in handle:
            if line.startswith("#ROOT\t"):
                _, label, where = line.rstrip("\n").split("\t")
                roots.append((urllib.parse.unquote(label), urllib.parse.unquote(where).rstrip("/")))
            elif not line.startswith("#"):
                break
    return roots


def to_key(path, roots):
    """Turn an absolute path from a scan into a decoded inventory key."""
    for label, where in roots:
        if path == where or path.startswith(where + "/"):
            return label + path[len(where):]
    return None


def read_scan(path):
    if not os.path.exists(path):
        return None
    rows = []
    with open(path, encoding="ascii") as handle:
        next(handle, None)
        for line in handle:
            kind, location, term, count, size, where = line.rstrip("\n").split("\t")
            rows.append({"kind": kind, "location": location, "term": term, "count": int(count), "size": int(size),
                         "path": urllib.parse.unquote(where)})
    return rows


def own_record(path, root_home, migration_dir):
    """Files that mention the terms because of this migration or Claude's own logs, not because they hold the data."""
    return bool(migration_dir and path.startswith(migration_dir + "/")) or bool(root_home and path.startswith(root_home + "/.claude/"))


def summarize_matches(rows, roots, entries, other_entries, migration_dir):
    home = dict(roots).get("home")
    decoded = {urllib.parse.unquote(k): e for k, e in entries.items()}
    by_path: dict = {}
    for row in rows:
        if row["kind"] == "match":
            by_path.setdefault(row["path"], {}).setdefault(row["term"], 0)
            by_path[row["path"]][row["term"]] += row["count"]
    term_files, secret_files, tool_secrets, own_files = [], [], 0, []
    for path, terms in sorted(by_path.items()):
        named = {t: n for t, n in terms.items() if not t.startswith("builtin:")}
        if own_record(path, home, migration_dir):
            own_files.append(path)
            continue
        if any(t.startswith("builtin:") for t in terms):
            # A tool folder's matches are mostly public certificates. Term matches are still listed below.
            if TOOL_FOLDER.search(path[len(home) + 1:] if home and path.startswith(home + "/") else path):
                tool_secrets += 1
            else:
                secret_files.append(path)
        if named:
            key = to_key(path, roots)
            sha = decoded[key][3] if key in decoded else None
            real = sha is not None and len(sha) == 64
            term_files.append({
                "path": path, "terms": named,
                "same_content_elsewhere": sorted(show(k) for k, e in entries.items() if real and e[3] == sha and urllib.parse.unquote(k) != key),
                "same_content_on_dest": sorted(show(k) for k, e in other_entries.items() if real and e[3] == sha),
            })
    return term_files, secret_files, tool_secrets, own_files


def summarize_unsearched(rows, roots):
    home = dict(roots).get("home") or ""
    reasons: collections.Counter = collections.Counter()
    user_paths = []
    system_areas: collections.Counter = collections.Counter()
    tool_files = 0
    for row in rows:
        if row["kind"] != "not-searched":
            continue
        reasons[row["location"]] += 1
        rel = row["path"][len(home) + 1:] if row["path"].startswith(home + "/") else row["path"]
        parts = rel.split("/")
        if parts[0] in ("Library", ".Trash") or MEDIA_LIBRARY.search("home/" + rel):
            system_areas["/".join(parts[:2])] += 1
        elif TOOL_FOLDER.search(rel) or parts[0] == ".claude":
            tool_files += 1
        else:
            user_paths.append(rel)
    return dict(reasons), sorted(user_paths), dict(system_areas.most_common()), tool_files


def package_lines(lines):
    return {re.sub(r"^[\s│├└─+`|-]+", "", line).strip() for line in lines if line.strip()}


def diff_packages(source, dest):
    found = {}
    sources = source.get("results", {})
    dests = (dest or {}).get("results", {})
    for name in PACKAGE_LISTS:
        entry = sources.get(name)
        if not entry or entry.get("status") != "ok":
            continue
        only = package_lines(entry.get("output", [])) - package_lines(dests.get(name, {}).get("output", []))
        if name == "npm_global":
            only = {line for line in only if not line.startswith("/")}
        if only:
            found[name] = sorted(only)
    return found


def repos_needing_care(collected):
    found = {}
    for path, state in collected.get("git_repos", {}).items():
        if state.get("status") != "ok":
            found[path] = {"problem": state.get("status")}
        elif state["uncommitted"] or state["unpushed"] or state["stashes"] or not state["remotes"]:
            found[path] = state
    return found


def load_collected(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def rows_for(title, rows, out):
    print(title, file=out)
    for row in rows[:MAX_ROWS]:
        print("  " + (row if len(row) <= MAX_WIDTH else row[:MAX_WIDTH] + "..."), file=out)
    if len(rows) > MAX_ROWS:
        print("  ... and %d more, in the report file" % (len(rows) - MAX_ROWS), file=out)


def build(args):
    folder = os.path.join(args.dir, "discovery")
    source_tsv = os.path.join(folder, args.source + ".tsv")
    source, source_end = load(source_tsv)
    roots = load_roots(source_tsv)
    dest, dest_end, dest_roots = {}, None, []
    if args.dest:
        dest_tsv = os.path.join(folder, args.dest + ".tsv")
        dest, dest_end = load(dest_tsv)
        dest_roots = load_roots(dest_tsv)
    rows, _blocked = classify(source, dest)
    migration_dir = os.path.abspath(args.dir)

    groups: dict = {"user": {}, "apps": {}, "system": {}, "tools": {}}
    files: dict = {"user": [], "apps": []}
    classes: collections.Counter = collections.Counter()
    noise = 0
    for verdict, size, key, where in rows:
        classes[verdict] += 1
        if verdict == "identical":
            continue
        kind = kind_of(key)
        if kind == "noise":
            noise += 1
            continue
        group = groups[kind].setdefault(group_of(key, kind), {"files": 0, "bytes": 0, "classes": collections.Counter()})
        group["files"] += 1
        group["bytes"] += size
        group["classes"][verdict] += 1
        if kind in files:
            files[kind].append({"path": show(key), "class": verdict, "size": size, "found_at": show(where) if where != "-" else None})

    report = {
        "source": args.source, "dest": args.dest,
        "counts": {"source": source_end, "dest": dest_end, "classes": dict(classes), "noise_files_not_listed": noise},
        "groups": {kind: {show(k): dict(v, classes=dict(v["classes"])) for k, v in value.items()} for kind, value in groups.items()},
        "files": files,
    }

    for label, entries, other, side_roots, name in ((args.source, source, dest, roots, "source"), (args.dest, dest, source, dest_roots, "dest")):
        if not label:
            continue
        scan = read_scan(os.path.join(folder, label + "-scan.tsv"))
        if scan is None:
            report[name + "_scan"] = None
            continue
        term_files, secret_files, tool_secrets, own_files = summarize_matches(scan, side_roots, entries, other, migration_dir)
        reasons, user_paths, system_areas, tool_files = summarize_unsearched(scan, side_roots)
        report[name + "_scan"] = {"term_files": term_files, "secret_files": secret_files, "tool_folder_secret_matches": tool_secrets,
                                  "own_records": own_files, "not_searched_reasons": reasons, "not_searched_user_paths": user_paths,
                                  "not_searched_system_areas": system_areas, "not_searched_tool_files": tool_files}

    collected = load_collected(os.path.join(folder, args.source + ".json"))
    collected_dest = load_collected(os.path.join(folder, args.dest + ".json")) if args.dest else None
    if collected:
        report["packages_only_on_source"] = diff_packages(collected, collected_dest)
        report["repos_needing_care"] = repos_needing_care(collected)
        results = collected.get("results", {})
        report["not_collected"] = sorted("%s (%s)" % (k, v.get("status")) for k, v in results.items() if v.get("status") != "ok")
        report["backup"] = results.get("time_machine", {}).get("output", [])[:3]
    return report


def scan_summary(name, scan, out):
    if scan is None:
        print("\n%s scan: NOT RUN, so nothing was searched there." % name, file=out)
        return
    rows_for("\n%s, files matching your terms: %d" % (name, len(scan["term_files"])), [
        "%s  %s%s%s" % (item["path"], item["terms"],
                        "  also at: %s" % item["same_content_elsewhere"] if item["same_content_elsewhere"] else "",
                        "  ON DEST: %s" % item["same_content_on_dest"] if item["same_content_on_dest"] else "")
        for item in scan["term_files"]], out)
    rows_for("%s, likely secrets: %d, plus %d in tool folders" % (
        name, len(scan["secret_files"]), scan["tool_folder_secret_matches"]), scan["secret_files"], out)
    if scan["own_records"]:
        print("%s, %d more match(es) in Claude's own files or this migration's folder. Those hold terms and session text, not necessarily the data." % (
            name, len(scan["own_records"])), file=out)
    print("%s, not searched: %s" % (name, json.dumps(scan["not_searched_reasons"], sort_keys=True)), file=out)
    rows_for("  In user folders: %d. Tool folders: %d." % (len(scan["not_searched_user_paths"]), scan["not_searched_tool_files"]),
             scan["not_searched_user_paths"], out)
    areas = sorted(scan["not_searched_system_areas"].items(), key=lambda item: -item[1])[:8]
    print("  In app and system data, top areas: %s" % ", ".join("%s (%d)" % area for area in areas), file=out)


def print_summary(report, path, out):
    counts = report["counts"]
    print("%s: %d file(s). %s" % (report["source"], sum(counts["classes"].values()), json.dumps(counts["classes"], sort_keys=True)), file=out)
    for label, end in (("source", counts["source"]), ("dest", counts["dest"])):
        if end:
            print("%s unreadable=%d excluded=%d cloud-placeholders=%d" % (
                label, end.get("errors", 0), end.get("excluded_roots", 0), end.get("dataless", 0)), file=out)
    for kind, title in (("user", "User files not identical at the destination, by folder"), ("apps", "Apps not identical at the destination")):
        rows = sorted(report["groups"][kind].items(), key=lambda item: item[0])
        rows_for("\n%s: %d folder(s)" % (title, len(rows)), [
            "%-50s %6d file(s) %10.1f MB  %s" % (k, v["files"], v["bytes"] / 1e6, v["classes"]) for k, v in rows], out)
    tools = report["groups"]["tools"]
    if tools:
        print("\nInstalled tools and caches not identical: %d file(s). Reinstall these, rather than copy them." % sum(v["files"] for v in tools.values()), file=out)
    system = sorted(report["groups"]["system"].items(), key=lambda item: -item[1]["files"])
    print("\nApp and system data not identical: %d area(s), %d file(s), by path only. Check it before saying nothing's lost." % (
        len(system), sum(v["files"] for _, v in system)), file=out)
    for name in ("source", "dest"):
        if name + "_scan" in report:
            scan_summary(name, report[name + "_scan"], out)
    if "packages_only_on_source" in report:
        packages = report["packages_only_on_source"]
        rows_for("\nPackages only on the source: %d list(s)" % len(packages), [
            "%s: %s" % (k, ", ".join(v[:12]) + (" and %d more" % (len(v) - 12) if len(v) > 12 else "")) for k, v in packages.items()], out)
        repos = report["repos_needing_care"]
        rows_for("Git repos with work that may exist only here: %d" % len(repos), ["%s  %s" % item for item in sorted(repos.items(), key=lambda i: i[0])], out)
        print("Not collected, or failed: %s" % (", ".join(report["not_collected"]) or "none"), file=out)
        if report["backup"]:
            print("Time Machine says: %s" % " ".join(report["backup"]), file=out)
    print("\nAll paths: %s" % path, file=out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", required=True)
    parser.add_argument("--source", required=True, help="the source's discover label")
    parser.add_argument("--dest", help="the destination's label. Leave it out if it doesn't exist yet.")
    args = parser.parse_args()
    report = build(args)
    path = os.path.join(args.dir, "discovery", "report-%s.json" % args.source)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
    print_summary(report, path, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
