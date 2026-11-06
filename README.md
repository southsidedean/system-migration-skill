# System migration skill

A Claude skill that guides you through moving to a new computer, merging several into one, or folding another system into one you already use. It supports macOS and Linux. Windows may come later.

Most migration tools move your files and report success. This skill is built around proving it, and around the decisions a tool can't make for you: what to leave behind, what belongs to a former employer, and when it's safe to erase the old machine.

## What it does

1. **Discover:** read-only inventory of every machine, including what it couldn't read.
2. **Decide:** you choose keep, leave, archive, or delete, in small batches.
3. **Plan:** a runbook separating what Claude can do from what needs you.
4. **Migrate:** copies in stages, verifying each by hash before moving on.
5. **Archive:** verified archives for anything leaving the active system.
6. **Audit:** independent end-to-end review, with no sampling.
7. **Decommission:** a hard gate before anything is erased.

## Safety

- Nothing changes until you approve a plan.
- Reports show paths, sizes, and counts, not file contents or secrets.
- Deleting and erasing need your explicit instruction, and you run the erase yourself.
- Anything it couldn't check is listed as not verified, not reported as clean.

It flags possible contractual or legal concerns with data you hold, but it doesn't give legal advice. Check any agreements you're bound by. Keep your own backups: this skill reduces risk, but doesn't remove it.

## Install

Copy or clone this folder into your Claude skills folder, for example:

```sh
git clone https://github.com/southsidedean/system-migration-skill ~/.claude/skills/system-migration
```

Then ask Claude something like "Help me migrate from my old Mac to my new one."

## Layout

| Path | What it is |
|---|---|
| `SKILL.md` | The rules and phases |
| `references/` | Detail for each phase and platform, loaded when needed |
| `templates/` | Status doc, decisions log, archive manifest |
| `scripts/` | `migrate.py` and its helpers, which do the deterministic work, plus tests |
| `evals/` | Test scenarios with planted traps |

## Development

The scripts need Python 3.9 or later and nothing else.

```sh
python3 scripts/test_scripts.py
python3 scripts/test_migrate.py
MIGRATE_TEST_HOST=user@host python3 scripts/test_migrate.py  # also tests over SSH
```

The script tests pass on macOS and on Ubuntu 24.04. The tests over SSH have only run on Ubuntu so far.

## License

[MIT](LICENSE)
