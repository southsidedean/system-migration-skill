---
name: system-migration
description: Guide a user through migrating one or more computers to another, or consolidating systems into one. Use for moving to a new Mac or Linux machine, merging several machines, absorbing another system later, retiring an old machine, or deciding what to keep, leave, archive, or delete, including former-employer and other sensitive data. Inventories first, verifies every copy, and gates any erase.
---

# System migration

Walk the user through moving data, apps, and settings from one or more **sources** to a **destination**. Work in the phases below, and keep the user in charge of every decision that loses data or leaves their control.

Supported: macOS and Linux. Windows isn't supported yet; say so rather than improvising.

## Non-negotiable rules

1. **Read-only until the user approves a plan.** Discovery changes nothing on any machine.
2. **Success means verified.** An exit code is not proof. After every copy, compare counts and hashes with `scripts/compare.py`. An empty result is suspect until a positive control shows the check can find something.
3. **Classify by contents, not names.** A folder's name can mislead in either direction. Show unclear items to the user; don't guess.
4. **The user decides what happens to sensitive data.** Flag possible contractual or legal concerns and suggest they check, but don't give legal advice or decide for them.
5. **Never display secrets or sensitive contents.** Report paths, sizes, hashes, and match counts only. Don't read credential stores. Secrets never go in the migration docs.
6. **Name what you couldn't check.** List anything blocked, skipped, or not searchable as NOT VERIFIED. Don't describe it as clean.
7. **Delete and erase only on explicit instruction**, item by item, by exact path, with no wildcards. Show the target first. A request to delete one thing doesn't cover the next.
8. **Don't work around a block.** If the OS or a person denies access, record it and offer the user the choice. Don't request privileges or trigger permission prompts without warning them first.
9. **The source stays intact until the final gate** in Phase 7. Anything that changes it earlier gets recorded in the status doc.
10. **Keep the docs true.** Update `status.md` in the same step as the work, and re-check its claims before relying on them.

## Start or resume

Ask for or find the migration folder, default `~/migration-<YYYY-MM>/`. If it contains `status.md`, read it and `decisions.md`, re-verify the current state, summarize it, and continue. Otherwise create it from `templates/`.

Ask only what you need to start:
- **Shape:** one-to-one, many-to-one, or absorbing another system into one already in use. See `references/topologies.md`.
- **Machines:** names, OS, how they connect, and which can run commands.
- **Fate of each source:** keep, repurpose, or erase, and when.

Tell the user what you plan to do before each phase, and update them when something slow starts or the plan changes.

## Phases

Load the reference for each phase when you reach it.

| # | Phase | Goal | Load |
|---|---|---|---|
| 1 | Discover | Read-only inventory of every machine, with blocked paths listed | `references/discover.md`, plus the platform file |
| 2 | Decide | Keep, leave, archive, or delete, in small batches, recorded in `decisions.md` | `references/sensitive-data.md` |
| 3 | Plan | Runbook, split into what Claude can do and what needs the user | `templates/status.md` |
| 4 | Migrate | Copy in stages, verifying each stage before the next | `references/copy-and-verify.md` |
| 5 | Archive | Save anything leaving the active system, with verified archives | `references/sensitive-data.md` |
| 6 | Audit | Independent end-to-end review, with no sampling | `references/audit.md` |
| 7 | Decommission | Hard gate before any source is erased or repurposed | `references/decommission.md` |

Platform files: `references/platform-macos.md`, `references/platform-linux.md`. Load the ones for the machines involved.

## Scripts

Run with `python3`, on the machine that holds the files. They use only the standard library.

- `scripts/inventory.py`: complete file inventory with hashes. Records unreadable paths and caches instead of skipping them silently.
- `scripts/compare.py`: classifies every file, fails if the counts don't reconcile, and detects conflicts between sources.
- `scripts/scan_sensitive.py`: searches names and contents, and reports paths and counts only. Runs a positive control first.
- `scripts/run-awake.sh`: keeps a machine awake only for the life of one command.

Run `python3 scripts/test_scripts.py` if you change a script or don't trust a result.

## Working with the user

- Ask in small batches, each with a recommendation. Explain consequences in plain terms.
- Separate what you measured from what you inferred, and correct your own mistakes as soon as you find them.
- Copying credentials is the user's choice; offer to create new ones instead.
- Don't assume SSH, a NAS, a second machine being on, or a particular backup tool. Ask.
- Never send the user's data to an outside service, or upload anything to a third party, without asking.
