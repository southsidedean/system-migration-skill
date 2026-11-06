#!/usr/bin/env python3
"""Deterministic helpers for system migrations. Python 3.8+, standard library only.

Commands print a short summary, write detail to files, and use fixed exit codes:
  0 ok   1 failed a check   2 bad input or incomplete data

  init       create state.json and decisions.json in a migration folder
  status     print the phase, next step, and gaps
  advance    move to a phase
  decide     record a decision and render decisions.md
  record     record dated evidence for the gate
  collect    write apps, packages, and settings to JSON (read-only)
  copy       copy from a plan: dry run by default, verified with --run
  archive    build an archive from a plan, read it back, and verify it
  delete     delete exact paths from a plan: dry run by default
  gate       check a source against the erase gate. Never erases anything.
  inventory, compare, scan   run the matching script

Locations are local paths or user@host:/path. Remote hosts need SSH keys and python3.
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
import platform
import posixpath
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OK, FAILED, BAD = 0, 1, 2
OWNERS = ("personal", "employer", "client", "regulated", "unknown")
ACTIONS = ("keep", "leave", "archive", "encrypted-archive", "delete", "review-later")
SHAPES = ("one-to-one", "many-to-one", "absorb", "consolidate")
GATE_KINDS = ("final-compare", "final-backup", "credentials-retested", "secrets-reviewed",
              "git-clean", "local-app-data-checked", "archives-verified", "licenses-and-accounts")
NEXT = {
    1: "Run `collect` and `inventory` on every machine, and list what couldn't be read.",
    2: "Run `scan`, then record each choice with `decide`, in small batches.",
    3: "Write the runbook, and have the user approve copy, archive, and delete plans.",
    4: "Run `copy` one stage at a time, and resolve every missing or different file.",
    5: "Run `archive` for anything leaving the active system.",
    6: "Start independent auditors. Check major findings before relaying them.",
    7: "Run `gate` per source, right before erasing. The user runs the erase.",
}

# Runs on the machine that holds the files, locally or over SSH stdin.
TREE_SCRIPT = r'''
import base64, hashlib, json, os, stat, sys
req = json.loads(base64.b64decode(sys.argv[1]))
base, items, delete = req["base"], req["items"], req.get("delete", False)
out = {"entries": {}, "errors": [], "deleted": 0}
def record(rel):
    path = os.path.join(base, rel)
    try:
        st = os.lstat(path)
    except OSError as exc:
        out["errors"].append([rel, exc.strerror])
        return
    if stat.S_ISLNK(st.st_mode):
        out["entries"][rel] = ["l", os.readlink(path)]
    elif stat.S_ISDIR(st.st_mode):
        out["entries"][rel] = ["d"]
        try:
            names = sorted(os.listdir(path))
        except OSError as exc:
            out["errors"].append([rel, exc.strerror])
            return
        for name in names:
            record(os.path.join(rel, name))
    elif stat.S_ISREG(st.st_mode):
        digest = hashlib.sha256()
        try:
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
        except OSError as exc:
            out["errors"].append([rel, exc.strerror])
            return
        out["entries"][rel] = ["f", st.st_size, digest.hexdigest()]
    else:
        out["entries"][rel] = ["o"]
if delete:
    import shutil
    for rel in items:
        path = os.path.join(base, rel)
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
            out["deleted"] += 1
        except OSError as exc:
            out["errors"].append([rel, exc.strerror])
    out["left"] = [rel for rel in items if os.path.lexists(os.path.join(base, rel))]
else:
    for rel in items:
        record(rel)
json.dump(out, sys.stdout)
'''


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def split_location(location):
    head, sep, tail = location.partition(":")
    if sep and "/" not in head and head:
        return head, tail
    return None, location


def run_tree(location, items, delete=False):
    """Hash or delete items on the machine that holds them."""
    host, base = split_location(location)
    payload = base64.b64encode(json.dumps({"base": base, "items": items, "delete": delete}).encode()).decode()
    if host:
        command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", host, "python3", "-", payload]
    else:
        command = [sys.executable, "-", payload]
    done = subprocess.run(command, input=TREE_SCRIPT, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit("couldn't reach %s: %s" % (location, done.stderr.strip()[:300]))
    return json.loads(done.stdout)


def load_json(path, label="file"):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        raise SystemExit("%s not found: %s" % (label, path))
    except ValueError as exc:
        raise SystemExit("%s isn't valid JSON: %s (%s)" % (label, path, exc))


def save_json(path, data):
    tmp = path + ".partial"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def check_items(items, require_nonempty=True):
    """Items must be plain relative paths. No shell is used, so wildcards never expand."""
    if require_nonempty and not items:
        raise SystemExit("the plan lists no items")
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise SystemExit("bad item: %r" % (item,))
        norm = posixpath.normpath(item)
        if item.startswith("/") or norm in (".", "..") or norm.startswith("../"):
            raise SystemExit("items must be paths inside the base folder: %r" % item)


def load_plan(path, needs):
    plan = load_json(path, "plan")
    for key in needs:
        if key not in plan:
            raise SystemExit("plan is missing %r: %s" % (key, path))
    check_items(plan["items"])
    return plan


def require_approval(plan):
    if plan.get("approved_by_user") is not True:
        raise SystemExit("the plan doesn't have \"approved_by_user\": true. Show it to the user first.")


def state_path(folder):
    return os.path.join(folder, "state.json")


def load_state(folder):
    return load_json(state_path(folder), "state")


# --- init, status, advance

def cmd_init(args):
    os.makedirs(args.dir, exist_ok=True)
    if os.path.exists(state_path(args.dir)):
        raise SystemExit("already initialized: %s. Use `status`." % args.dir)
    save_json(state_path(args.dir), {
        "shape": args.shape, "phase": 1, "sources": args.source, "destination": args.dest,
        "created": now(), "evidence": [],
    })
    save_json(os.path.join(args.dir, "decisions.json"), {"decisions": []})
    for name in ("status.md",):
        target = os.path.join(args.dir, name)
        if not os.path.exists(target):
            shutil.copyfile(os.path.join(HERE, "..", "templates", name), target)
    print("initialized %s: phase 1. Next: %s" % (args.dir, NEXT[1]))
    return OK


def cmd_status(args):
    state = load_state(args.dir)
    decisions = load_json(os.path.join(args.dir, "decisions.json"), "decisions")["decisions"]
    pending = [d["id"] for d in decisions if d["action"] == "review-later"]
    print("shape=%s phase=%d sources=%s destination=%s" % (
        state["shape"], state["phase"], ",".join(state["sources"]), state["destination"]))
    print("decisions=%d review_later=%s evidence=%d" % (len(decisions), ",".join(pending) or "none", len(state["evidence"])))
    print("next: %s" % NEXT[state["phase"]])
    return OK


def cmd_advance(args):
    state = load_state(args.dir)
    if args.to not in NEXT:
        raise SystemExit("phase must be 1 to 7")
    state["phase"] = args.to
    save_json(state_path(args.dir), state)
    print("phase=%d next: %s" % (args.to, NEXT[args.to]))
    return OK


# --- decide

def render_decisions(folder, decisions):
    lines = ["# Decisions", "", "Rendered from decisions.json. Holds no secrets or file contents.", "",
             "| ID | Date | Source | Item | Owner | Secret | Action | Reason |", "|---|---|---|---|---|---|---|---|"]
    for d in decisions:
        cells = [d["id"], d["date"][:10], d["source"], d["item"], d["owner"],
                 "yes" if d["secret"] else "no", d["action"], d.get("reason", "")]
        lines.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    with open(os.path.join(folder, "decisions.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def cmd_decide(args):
    path = os.path.join(args.dir, "decisions.json")
    data = load_json(path, "decisions")
    entry = {"id": "D%d" % (len(data["decisions"]) + 1), "date": now(), "source": args.source, "item": args.item,
             "owner": args.owner, "secret": args.secret == "yes", "action": args.action, "reason": args.reason or ""}
    data["decisions"].append(entry)
    save_json(path, data)
    render_decisions(args.dir, data["decisions"])
    print("%s: %s -> %s" % (entry["id"], args.item, args.action))
    return OK


# --- evidence and gate

def cmd_record(args):
    state = load_state(args.dir)
    entry = {"source": args.source, "kind": args.kind, "date": now(), "status": args.status, "note": args.note or ""}
    if args.status == "accepted-risk" and not args.note:
        raise SystemExit("accepted-risk needs a --note saying what the user accepted")
    if args.file:
        summary = load_json(args.file, "evidence file")
        entry["file"] = os.path.abspath(args.file)
        if args.kind == "final-compare":
            entry["classes"] = summary.get("classes")
            entry["empty_dirs"] = len(summary.get("empty_dirs_at_dest", []))
    state["evidence"].append(entry)
    save_json(state_path(args.dir), state)
    print("recorded %s for %s: %s" % (args.kind, args.source, args.status))
    return OK


def cmd_gate(args):
    state = load_state(args.dir)
    if args.source not in state["sources"]:
        raise SystemExit("%s isn't a source here: %s" % (args.source, ", ".join(state["sources"])))
    current = datetime.datetime.now(datetime.timezone.utc)
    last_change = None
    if args.source_changed:
        last_change = datetime.datetime.fromisoformat(args.source_changed)
        if last_change.tzinfo is None:
            last_change = last_change.astimezone()
    results = []
    for kind in GATE_KINDS:
        found = [e for e in state["evidence"] if e["source"] == args.source and e["kind"] == kind]
        if not found:
            results.append((kind, "fail", "no evidence"))
            continue
        entry = found[-1]
        when = datetime.datetime.fromisoformat(entry["date"])
        if entry["status"] == "accepted-risk":
            results.append((kind, "accepted", entry["note"]))
        elif entry["status"] != "pass":
            results.append((kind, "fail", "recorded as %s" % entry["status"]))
        elif last_change and when < last_change:
            results.append((kind, "fail", "stale: the source changed afterward"))
        elif (current - when).total_seconds() > args.max_age_hours * 3600:
            results.append((kind, "fail", "stale: older than %d hours" % args.max_age_hours))
        elif kind == "final-compare" and (entry.get("empty_dirs") or (entry.get("classes") or {}).get("missing")):
            results.append((kind, "fail", "missing files or empty folders remain; decide them or accept the risk"))
        elif kind == "final-compare" and not entry.get("classes"):
            results.append((kind, "fail", "no compare summary was recorded with --file"))
        else:
            results.append((kind, "pass", entry["date"]))
    for kind, verdict, detail in results:
        print("%-9s %-24s %s" % (verdict.upper(), kind, detail))
    failed = sum(1 for r in results if r[1] == "fail")
    print("GATE %s for %s: %d failing. This check never erases; the user runs the erase." % (
        "FAILED" if failed else "PASSED", args.source, failed))
    return FAILED if failed else OK


# --- collect

COMMON = {
    "git_config_names": ["git", "config", "--global", "--name-only", "--list"],
    "vscode_extensions": ["code", "--list-extensions"],
    "npm_global": ["npm", "-g", "ls", "--depth=0"],
    "pipx": ["pipx", "list", "--short"],
    "crontab": ["crontab", "-l"],
    "printers": ["lpstat", "-p"],
}
MACOS = {
    "os": ["sw_vers"],
    "applications": ["ls", "/Applications"],
    "brew_formulae": ["brew", "leaves", "--installed-on-request"],
    "brew_casks": ["brew", "list", "--cask"],
    "brew_taps": ["brew", "tap"],
    "brew_services": ["brew", "services", "list"],
    "mas": ["mas", "list"],
    "launch_agents": ["ls", os.path.expanduser("~/Library/LaunchAgents"), "/Library/LaunchAgents", "/Library/LaunchDaemons"],
    "sharing": ["sharing", "-l"],
    "firewall": ["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"],
    "power": ["pmset", "-g"],
    "time_machine": ["tmutil", "destinationinfo"],
}
LINUX = {
    "os": ["cat", "/etc/os-release"],
    "disks": ["lsblk", "-f"],
    "apt_manual": ["apt-mark", "showmanual"],
    "dnf_user": ["dnf", "repoquery", "--userinstalled"],
    "pacman_explicit": ["pacman", "-Qqe"],
    "flatpak": ["flatpak", "list", "--app"],
    "snap": ["snap", "list"],
    "user_units": ["systemctl", "--user", "list-unit-files", "--state=enabled"],
    "system_units": ["systemctl", "list-unit-files", "--state=enabled"],
    "autostart": ["ls", os.path.expanduser("~/.config/autostart")],
    "connections": ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
}


def cmd_collect(args):
    table = dict(COMMON)
    table.update(MACOS if platform.system() == "Darwin" else LINUX)
    results = {}
    absent = failed = 0
    for name, command in sorted(table.items()):
        if not shutil.which(command[0]):
            results[name] = {"status": "absent"}
            absent += 1
            continue
        try:
            done = subprocess.run(command, capture_output=True, text=True, errors="replace",
                                  timeout=args.timeout, stdin=subprocess.DEVNULL)
            results[name] = {"status": "ok" if done.returncode == 0 else "exit-%d" % done.returncode,
                             "output": done.stdout.splitlines()}
            failed += done.returncode != 0
        except subprocess.TimeoutExpired:
            results[name] = {"status": "timeout"}
            failed += 1
    save_json(args.output, {"host": platform.node(), "system": platform.system(), "date": now(), "results": results})
    print("collected=%d absent=%d not_ok=%d output=%s" % (len(table), absent, failed, args.output))
    print("Not collected on purpose: secrets, and app settings that can trigger permission prompts.")
    return OK


# --- copy

def compare_trees(source, dest):
    missing, different = [], []
    for rel, entry in source["entries"].items():
        other = dest["entries"].get(rel)
        if other is None:
            missing.append(rel)
        elif entry[0] != other[0] or (entry[0] == "f" and entry[2] != other[2]) or (entry[0] == "l" and entry[1] != other[1]):
            different.append(rel)
    return missing, different


def cmd_copy(args):
    plan = load_plan(args.plan, ("source", "dest", "items"))
    if args.run:
        require_approval(plan)
    host, _ = split_location(plan["dest"])
    if host:
        raise SystemExit("copy runs on the destination, so dest must be a local path")
    if args.run:
        os.makedirs(plan["dest"], exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".list", delete=False) as handle:
        handle.write("".join("./%s\n" % item.rstrip("/") for item in plan["items"]))
        listing = handle.name
    src_host, src_base = split_location(plan["source"])
    src = "%s/" % src_base.rstrip("/")
    if src_host:
        src = "%s:%s" % (src_host, src.replace(" ", "\\ "))
    # -r because --files-from turns off -a's recursion. --ignore-existing protects newer destination files.
    command = ["rsync", "-a", "-r", "--ignore-existing", "--files-from=" + listing, src, plan["dest"].rstrip("/") + "/"]
    try:
        if not args.run:
            done = subprocess.run(command[:1] + ["-n", "-v"] + command[1:], capture_output=True, text=True, errors="replace")
            if done.returncode != 0:
                print(done.stderr[:500], file=sys.stderr)
                return FAILED
            names = [line for line in done.stdout.splitlines() if line.strip() and not line.startswith(("sent ", "total ", "Transfer ", "receiving ", "sending ", "building "))]
            print("DRY RUN: rsync lists %d entries for %d planned item(s). Nothing was written." % (len(names), len(plan["items"])))
            if not names:
                print("It lists nothing, which proves nothing. Check the plan, or whether everything already exists.")
            return OK
        done = subprocess.run(command, capture_output=True, text=True, errors="replace")
    finally:
        os.unlink(listing)
    if done.returncode != 0:
        print("rsync exit %d: %s" % (done.returncode, done.stderr[:500]), file=sys.stderr)
    source = run_tree(plan["source"], plan["items"])
    dest = run_tree(plan["dest"], [i for i in plan["items"] if os.path.lexists(os.path.join(plan["dest"], i))])
    missing, different = compare_trees(source, dest)
    report = {"date": now(), "source_entries": len(source["entries"]), "missing": missing, "different": different,
              "source_errors": source["errors"], "dest_errors": dest["errors"]}
    report_path = (args.report or args.plan + ".result.json")
    save_json(report_path, report)
    files = sum(1 for e in source["entries"].values() if e[0] == "f")
    print("source_entries=%d files=%d missing=%d different=%d unreadable=%d report=%s" % (
        len(source["entries"]), files, len(missing), len(different), len(source["errors"]) + len(dest["errors"]), report_path))
    if different:
        print("Different files weren't overwritten; the destination kept its version. Review them.")
    if not source["entries"]:
        print("The source listed nothing, so this proves nothing.", file=sys.stderr)
        return FAILED
    return FAILED if (done.returncode or missing or different or source["errors"] or dest["errors"]) else OK


# --- archive

def cmd_archive(args):
    plan = load_plan(args.plan, ("name", "source", "items", "dest_dir"))
    require_approval(plan)
    host, base = split_location(plan["source"])
    name, dest_dir = plan["name"], plan["dest_dir"]
    if os.path.basename(name) != name:
        raise SystemExit("archive name can't include a folder")
    if not os.path.isdir(dest_dir):
        raise SystemExit("destination folder doesn't exist: %s" % dest_dir)
    final = os.path.join(dest_dir, name + ".tar.gz")
    partial = final + ".partial"
    if os.path.exists(final) and not args.replace:
        raise SystemExit("%s exists. Use --replace to rebuild it after verification." % final)
    source = run_tree(plan["source"], plan["items"])
    if not source["entries"]:
        print("the source listed nothing", file=sys.stderr)
        return FAILED

    tar = ["tar", "-czf", "-", "-C", base, "-T", "-"]
    if host:
        command = ["ssh", "-o", "BatchMode=yes", host, "COPYFILE_DISABLE=1 tar -czf - -C %s -T -" % shlex_quote(base)]
        env = None
    else:
        command, env = tar, dict(os.environ, COPYFILE_DISABLE="1")
    listing = "".join(item + "\n" for item in plan["items"]).encode()
    digest = hashlib.sha256()
    with tempfile.TemporaryFile() as stdin, open(partial, "wb") as out:
        stdin.write(listing)
        stdin.seek(0)
        proc = subprocess.Popen(command, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        for chunk in iter(lambda: proc.stdout.read(1 << 20), b""):
            digest.update(chunk)
            out.write(chunk)
        errors = proc.stderr.read().decode(errors="replace")
        proc.wait()

    def fail(message):
        os.unlink(partial)
        print("ARCHIVE FAILED: %s. Any existing archive is untouched." % message, file=sys.stderr)
        return FAILED

    if proc.returncode != 0:
        return fail("tar exit %d: %s" % (proc.returncode, errors[:300]))
    with open(partial, "rb") as handle:
        back = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            back.update(chunk)
    if back.hexdigest() != digest.hexdigest():
        return fail("the read-back hash doesn't match the stream")
    members = {}
    with tarfile.open(partial, "r:gz") as archive:
        for member in archive:
            key = member.name.rstrip("/")
            if os.path.basename(key).startswith("._"):
                continue
            kind = "d" if member.isdir() else "l" if member.issym() else "f" if member.isfile() else "o"
            members[key] = kind
            if kind == "f":
                data = archive.extractfile(member)
                sha = hashlib.sha256()
                for chunk in iter(lambda: data.read(1 << 20), b""):
                    sha.update(chunk)
                expected = source["entries"].get(key)
                if expected is None or expected[0] != "f" or expected[2] != sha.hexdigest():
                    return fail("member differs from the source: %s" % key)
    absent = [rel for rel in source["entries"] if rel not in members]
    if absent:
        return fail("%d source entries aren't in the archive, such as %s" % (len(absent), absent[0]))
    if os.path.exists(final):
        with tarfile.open(final, "r:gz") as old:
            lost = [m.name for m in old if m.name.rstrip("/") not in members and not os.path.basename(m.name).startswith("._")]
        if lost and not args.allow_shrink:
            return fail("%d entries from the old archive would be lost, such as %s" % (len(lost), lost[0]))
    roots = [posixpath.normpath(i) for i in plan["items"]]
    outside = []
    for rel, entry in source["entries"].items():
        if entry[0] == "l":
            target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), entry[1]))
            if entry[1].startswith("/") or not any(target == r or target.startswith(r + "/") for r in roots):
                outside.append([rel, entry[1]])
    os.replace(partial, final)
    sha = back.hexdigest()
    with open(final + ".sha256", "w", encoding="utf-8") as handle:
        handle.write("%s  %s\n" % (sha, os.path.basename(final)))
    with open(os.path.join(dest_dir, name + ".filelist.txt"), "w", encoding="utf-8", errors="surrogateescape") as handle:
        handle.write("".join(key + "\n" for key in sorted(members)))
    save_json(os.path.join(dest_dir, name + ".manifest.json"), {
        "name": name, "created": now(), "source": plan["source"], "items": plan["items"], "sha256": sha,
        "size": os.path.getsize(final), "entries": len(members), "encrypted": False,
        "symlinks_pointing_outside": outside, "source_unreadable": source["errors"], "notes": plan.get("notes", ""),
    })
    print("%s.tar.gz size=%d entries=%d verified_files=%d symlinks_outside=%d unreadable=%d" % (
        name, os.path.getsize(final), len(members), sum(1 for k in members.values() if k == "f"), len(outside), len(source["errors"])))
    if outside:
        print("Symlinks pointing outside the archive are stored as links only. See the manifest.")
    return FAILED if source["errors"] else OK


def shlex_quote(text):
    return "'" + text.replace("'", "'\\''") + "'"


# --- delete

def archive_hashes(path):
    hashes = {}
    with tarfile.open(path, "r:*") as archive:
        for member in archive:
            if member.isfile():
                data = archive.extractfile(member)
                sha = hashlib.sha256()
                for chunk in iter(lambda: data.read(1 << 20), b""):
                    sha.update(chunk)
                hashes[member.name] = sha.hexdigest()
    return hashes


def cmd_delete(args):
    plan = load_plan(args.plan, ("base", "items"))
    if args.run:
        require_approval(plan)
    tree = run_tree(plan["base"], plan["items"])
    absent = [e[0] for e in tree["errors"] if e[0] in plan["items"]]
    if absent:
        print("Stopping: %d planned path(s) can't be found, such as %r. Nothing was deleted." % (len(absent), absent[0]), file=sys.stderr)
        return FAILED
    if args.verify_archive:
        hashes = archive_hashes(args.verify_archive)
        unmatched = [rel for rel, e in tree["entries"].items() if e[0] == "f" and hashes.get(rel) != e[2]]
        if unmatched:
            print("Stopping: %d file(s) don't match the archive, such as %r. Nothing was deleted." % (len(unmatched), unmatched[0]), file=sys.stderr)
            return FAILED
        print("archive check: all %d file(s) match" % sum(1 for e in tree["entries"].values() if e[0] == "f"))
    if not args.run:
        print("DRY RUN: would delete %d item(s), %d entries in total. Use --run." % (len(plan["items"]), len(tree["entries"])))
        return OK
    result = run_tree(plan["base"], plan["items"], delete=True)
    print("deleted=%d left=%d errors=%d" % (result["deleted"], len(result["left"]), len(result["errors"])))
    return FAILED if (result["left"] or result["errors"]) else OK


# --- entry point

def passthrough(script):
    return os.path.join(HERE, script)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("inventory", "compare", "scan"):
        script = {"inventory": "inventory.py", "compare": "compare.py", "scan": "scan_sensitive.py"}[sys.argv[1]]
        return subprocess.call([sys.executable, passthrough(script)] + sys.argv[2:])

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("--dir", required=True)
    p.add_argument("--shape", choices=SHAPES, required=True)
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--dest", required=True)
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("status")
    p.add_argument("--dir", required=True)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("advance")
    p.add_argument("--dir", required=True)
    p.add_argument("--to", type=int, required=True)
    p.set_defaults(func=cmd_advance)

    p = sub.add_parser("decide")
    p.add_argument("--dir", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--item", required=True)
    p.add_argument("--owner", choices=OWNERS, required=True)
    p.add_argument("--secret", choices=("yes", "no"), required=True)
    p.add_argument("--action", choices=ACTIONS, required=True)
    p.add_argument("--reason")
    p.set_defaults(func=cmd_decide)

    p = sub.add_parser("record")
    p.add_argument("--dir", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--kind", choices=GATE_KINDS, required=True)
    p.add_argument("--status", choices=("pass", "fail", "accepted-risk"), required=True)
    p.add_argument("--note")
    p.add_argument("--file")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("gate")
    p.add_argument("--dir", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--max-age-hours", type=int, default=24)
    p.add_argument("--source-changed", help="ISO time the source last changed; older evidence is stale")
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("collect")
    p.add_argument("--output", required=True)
    p.add_argument("--timeout", type=int, default=30)
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("copy")
    p.add_argument("--plan", required=True)
    p.add_argument("--run", action="store_true")
    p.add_argument("--report")
    p.set_defaults(func=cmd_copy)

    p = sub.add_parser("archive")
    p.add_argument("--plan", required=True)
    p.add_argument("--replace", action="store_true")
    p.add_argument("--allow-shrink", action="store_true")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("delete")
    p.add_argument("--plan", required=True)
    p.add_argument("--run", action="store_true")
    p.add_argument("--verify-archive")
    p.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
