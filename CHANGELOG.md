# Changelog

## Unreleased

The first version, for macOS and Linux.

### New

- A skill that guides a migration through seven phases, with a lighter path for small jobs.
- `scripts/migrate.py`: state, decisions, evidence, collection, copying, archiving, deletion, and a final check before erasing.
- Inventory, comparison, and sensitive-data scan scripts.
- Eval scenarios with planted traps. 3 of the 15 have fixtures and have been run.
- User guides in `docs/`.
- CI on macOS and Ubuntu, including copies over real SSH.

### Fixes

- `copy` recovers files that `rsync` drops. macOS's `rsync` silently drops `./#name` entries in a file list over SSH.
- `run-awake.sh` no longer stops a job where `systemd-inhibit` isn't allowed.
- `scan` and `inventory` no longer read credential stores, even as raw bytes.
- `init` refuses a folder that's in use, so two migrations can't collide.
