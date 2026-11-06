# Changelog

## Unreleased

The first version, for macOS and Linux.

### New

- A skill that guides a migration through seven phases, with a lighter path for small jobs.
- `scripts/migrate.py`: state, decisions, evidence, collection, copying, archiving, deletion, and a final check before erasing.
- Inventory, comparison, and sensitive-data scan scripts.
- 15 eval scenarios with planted traps, each run once on Linux. See `evals/RESULTS.md`.
- User guides in `docs/`.
- CI on macOS and Ubuntu, including copies over real SSH.

### Fixes

- `copy` recovers files that `rsync` drops. macOS's `rsync` silently drops `./#name` entries in a file list over SSH.
- `run-awake.sh` no longer stops a job where `systemd-inhibit` isn't allowed.
- `scan` and `inventory` no longer read credential stores, even as raw bytes.
- `init` refuses a folder that's in use, so two migrations can't collide.
- Approvals are tied to a plan's exact contents and record the user's words, so an edited plan can't run.
- `inventory` and `scan` skip common password-manager files and SSH private keys, wherever they are.
- `compare` reports small files with a match elsewhere as `possibly-moved`, not `missing`.
- Small jobs keep their plan and result in `~/migration-jobs/`, not a temporary folder.
