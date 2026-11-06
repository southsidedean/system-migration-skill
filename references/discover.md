# Phase 1: Discover

Read-only on every machine. The only thing written is output in this migration's folder, so create that first with `migrate.py init`.

## Inventory each machine

Run on the machine that holds the files, so contents aren't streamed across the network to be hashed:

```sh
python3 inventory.py --root home=$HOME --root apps=/Applications --output source-a.tsv
```

Use the same `--root` labels on every machine, so paths line up across different usernames. Copy each `.tsv` into the migration folder. If a machine can't run commands remotely, give the user the command.

Check the end of each run:

- The file has an `#END` line. Without one, the run didn't finish.
- `errors` and `dataless` counts are listed as NOT VERIFIED in `status.md`.
- The counts look plausible. A nearly empty inventory usually means a bad argument, not a small disk.

## Collect beyond files

Run `python3 migrate.py collect --output source-a.json` on each machine. Use the platform file for anything it doesn't cover:

- Installed apps, packages, and versions, including language-level tools
- Services, scheduled jobs, startup items
- Shell config, dotfiles, editor settings and extensions, SSH config, and known hosts
- Git repos with uncommitted or unpushed work
- Network, VPN, printers, sharing services, firewall
- Backups: destination, last success, whether a restore was ever tested
- Credential stores: which exist and what kind. List names only.
- Sync services: what's synced versus local-only

## Report back

Give the user a short summary by category, with sizes, and say what you couldn't read. Then move to Phase 2. Don't propose deletions yet.
