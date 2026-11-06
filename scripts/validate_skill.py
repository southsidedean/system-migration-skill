#!/usr/bin/env python3
"""Check that the skill itself is well formed. Python 3.9+, standard library only.

  python3 scripts/validate_skill.py

Checks the SKILL.md frontmatter and length, that every file the docs mention exists, and that
every migrate.py command the skill documents exists.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_SKILL_LINES = 120  # SKILL.md loads on every use, so it has to stay short.
MAX_DESCRIPTION = 1024
PATH_RE = re.compile(r"`((?:references|scripts|templates|evals|docs)/[A-Za-z0-9_./-]+)`")
COMMAND_RE = re.compile(r"migrate\.py (?:<command>|([a-z]+))")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
        return handle.read()


def docs():
    found = ["SKILL.md", "README.md"]
    for folder in ("references", "docs", "templates", "evals"):
        path = os.path.join(ROOT, folder)
        if os.path.isdir(path):
            found += [os.path.join(folder, name) for name in sorted(os.listdir(path)) if name.endswith(".md")]
    return found


def main():
    errors = []
    skill = read("SKILL.md")
    match = re.match(r"---\n(.*?)\n---\n", skill, re.S)
    if not match:
        errors.append("SKILL.md has no frontmatter")
    else:
        fields = dict(line.split(": ", 1) for line in match.group(1).splitlines() if ": " in line)
        if not re.fullmatch(r"[a-z0-9-]{1,64}", fields.get("name", "")):
            errors.append("SKILL.md name must be lowercase letters, digits, and hyphens")
        if not 0 < len(fields.get("description", "")) <= MAX_DESCRIPTION:
            errors.append("SKILL.md description must be 1 to %d characters" % MAX_DESCRIPTION)
    lines = skill.count("\n")
    if lines > MAX_SKILL_LINES:
        errors.append("SKILL.md has %d lines; keep it to %d" % (lines, MAX_SKILL_LINES))

    helptext = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "migrate.py"), "--help"],
                              capture_output=True, text=True, check=True).stdout
    known = set(re.findall(r"^  ([a-z]+(?:, [a-z]+)*)\s{2,}", helptext, re.M))
    commands = {name for group in known for name in group.split(", ")}
    checked = 0
    for rel in docs():
        text = read(rel)
        for path in PATH_RE.findall(text):
            checked += 1
            if not os.path.exists(os.path.join(ROOT, path)):
                errors.append("%s mentions %s, which doesn't exist" % (rel, path))
        errors.extend("%s mentions migrate.py %s, which doesn't exist" % (rel, command)
                      for command in COMMAND_RE.findall(text) if command and command not in commands)
    if not commands or not checked:
        errors.append("found no commands or paths to check, so this check is broken")

    for error in errors:
        print("FAIL  %s" % error)
    print("skill %s: %d file references, %d commands" % ("INVALID" if errors else "valid", checked, len(commands)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
