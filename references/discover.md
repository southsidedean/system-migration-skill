# Phase 1: Discover

Read-only on every machine. The only thing written is output in this migration's folder, so create that first with `migrate.py init`.

## Run `discover` for each machine

Write the user's search terms to `terms.txt` in the migration folder, then run this from the machine you're on:

```sh
python3 migrate.py discover --dir <folder> --label source --machine me@old-mac
python3 migrate.py discover --dir <folder> --label dest
python3 migrate.py report --dir <folder> --source source --dest dest
```

`discover` runs `collect`, `inventory`, and `scan` on that machine, sending each script over SSH and saving the results to `discovery/` here. It leaves nothing on the source, including your terms. Without `--machine`, it runs locally. Use the same `--label` for later runs only if you mean to replace them. If the user has no terms, use `--no-scan` and list the scan as NOT VERIFIED. Leave `--dest` off `report` if the destination doesn't exist yet.

If a machine can't be reached, give the user the commands from `docs/commands.md` to run there.

## Read the report

`report` prints a summary, and writes every path to `discovery/report-<label>.json`. It answers most discovery questions, so read it before running anything else:

- Files unique to the source, by folder, and which apps and packages are missing
- Files matching the terms, with any copies by hash on either machine
- Likely secrets, and what wasn't searched
- Git repos with uncommitted, unpushed, or stashed work, or no remote
- What couldn't be collected, and the backup status

Matches in Claude's own files and the migration folder are counted separately, because they hold the terms and session text. A source's `~/.claude` can still hold real data from past sessions, so mention it.

Any exit other than 0 means discovery is incomplete. Unreadable, excluded, and cloud-placeholder counts are listed as NOT VERIFIED in `status.md`. Counts that look too small usually mean a bad argument, not a small disk.

## Collect beyond files

`collect` covers packages, services, and repos. Use the platform file for anything it doesn't cover:

- Installed apps, packages, and versions, including language-level tools
- Services, scheduled jobs, startup items
- Shell config, dotfiles, editor settings and extensions, SSH config, and known hosts
- Network, VPN, printers, sharing services, firewall
- Backups: destination, last success, whether a restore was ever tested
- Credential stores: which exist and what kind. List names only.
- Sync services: what's synced versus local-only

## Report back

Give the user a short summary by category, with sizes, and say what you couldn't read. Then move to Phase 2. Don't propose deletions yet.
