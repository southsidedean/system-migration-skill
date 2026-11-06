# Phase 7: Decommission gate

Erasing a source can't be undone. This gate runs separately for each source, right before erasing, even if an earlier phase passed.

## Confirm each one against the current state

Don't reuse old results. Record each check, then run the gate, which fails on missing or stale evidence:

```sh
python3 migrate.py record --dir . --source old-mac --kind final-compare --status pass --file compare/summary.json
python3 migrate.py record --dir . --source old-mac --kind git-clean --status accepted-risk --note "user keeps these changes"
python3 migrate.py gate --dir . --source old-mac --source-changed 2026-01-31T10:00:00-06:00
```

Kinds: `final-compare`, `final-backup`, `credentials-retested`, `secrets-reviewed`, `git-clean`, `local-app-data-checked`, `archives-verified`, `licenses-and-accounts`. Only record `pass` after actually checking. The checklist below says what each covers.

**Data**

- [ ] A final inventory and comparison ran after the source's last use, with every remaining `missing` item decided
- [ ] Every NOT VERIFIED item is resolved or accepted
- [ ] No uncommitted or unpushed Git work that the user wants
- [ ] Local-only app data checked: mail, notes, chat history, app databases, browser profiles
- [ ] Sync services confirmed caught up, on the destination rather than just the source

**Secrets**

- [ ] Credential stores copied again after the source's last change, opened at the destination, and retested later
- [ ] Stores that can't be copied have been reviewed by the user at the source
- [ ] SSH keys: each host using an old key works with the new one, or the key was kept deliberately

**Archives and backups**

- [ ] Archives verified, and readable from the destination
- [ ] A final source backup finished after the last change
- [ ] The user knows if that backup holds data they've decided not to keep, and has decided what to do with it

**Licenses and accounts**

- [ ] Per-machine licenses deauthorized
- [ ] Signed out of accounts that need it: cloud, app store, device-locating services
- [ ] Old keys removed from services, and credentials for organizations the user has left revoked

## Ask, then stop

Show the remaining failures and accepted risks. Then ask the user to confirm for that specific machine, by name. Record their answer in `decisions.md`.

Have the user run the erase themselves, and give them the steps for that platform. Don't erase a machine remotely.
