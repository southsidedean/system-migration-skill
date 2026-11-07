# Changelog

## Unreleased

The first version, for macOS and Linux.

### New

- A skill that guides a migration through seven phases, with a lighter path for small jobs.
- `scripts/migrate.py`: state, decisions, evidence, collection, copying, archiving, deletion, and a final check before erasing.
- Inventory, comparison, and sensitive-data scan scripts.
- 16 eval scenarios with planted traps, run on Linux and partly on macOS. See `evals/RESULTS.md`.
- User guides in `docs/`.
- `discover` runs inventory, collection, and the scan on a machine over SSH, leaving nothing there, including search terms.
- `report` summarizes discovery, so a session doesn't have to write its own analysis scripts.
- CI on macOS and Ubuntu, including copies over real SSH.
- CI installs its dev tools from a file locked with hashes.

### Fixes

- `collect` finds Homebrew and npm over SSH, without a login shell, and stops npm writing a log file on the source. It also counts Git work that may exist only on that machine.
- Auditors are told to write nothing on a source, and to send no data between machines.
- Claude asks for decisions when they come up, rather than listing them and waiting.
- `copy` recovers files that `rsync` drops. macOS's `rsync` silently drops `./#name` entries in a file list over SSH.
- `run-awake.sh` no longer stops a job where `systemd-inhibit` isn't allowed.
- `scan` and `inventory` no longer read credential stores, even as raw bytes.
- `init` refuses a folder that's in use, so two migrations can't collide.
- Approvals are tied to a plan's exact contents and record the user's words, so an edited plan can't run.
- `inventory` and `scan` skip common password-manager files and SSH private keys, wherever they are.
- `compare` reports small files with a match elsewhere as `possibly-moved`, not `missing`.
- Small jobs keep their plan and result in `~/migration-jobs/`, not a temporary folder.
- A full migration creates its folder before the first inventory, and a destination that doesn't exist yet no longer prompts a question.
- `compare` lists excluded paths as not compared, so a skipped keychain can't look like a clean result.
