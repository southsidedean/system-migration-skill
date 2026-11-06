# Phases 2 and 5: Decide and archive

Ask two separate questions about each item, then have the user choose an action.

## Whose is it?

| Owner | Examples |
|---|---|
| Personal | The user's own files |
| Employer | Current or former employer's code, docs, tools, and notes |
| Client or customer | Support tickets, logs, config dumps, or exports from someone else's systems |
| Regulated | Health, financial, or government ID data, or data under a similar legal regime |
| Unknown | Anything you can't place. Ask. |

## Is it a secret?

Yes or no, regardless of owner. Includes passwords, tokens, private keys, cloud logins, kubeconfigs, `.env` files, and session stores.

Two items can share an owner and need different handling: a former employer's training slides and that employer's cloud login are both "employer", but only one is a secret.

## Actions

Keep, leave behind, archive, encrypted archive (with the user's own tool), delete, or review later. Record every decision in `decisions.md`. "Leave behind" on a source that will be erased means "delete", so say so.

## Finding it

Names aren't reliable. For example, a folder called `Insurance` might hold a customer's gateway configs.

1. Ask what past employers, clients, and regulated work the machine has seen. Offer to skip this if they'd rather not say.
2. Build a terms file, one per line: organization names, product names, email domains, and ticket formats. Terms stay in the migration folder, not in anything shared.
3. Run the scan on each machine:

   ```sh
   python3 scan_sensitive.py --root $HOME --terms terms.txt --output scan.tsv
   ```

   It skips credential stores, even as raw bytes. Never write your own search that prints matching lines or record fields, because those end up in transcripts.
4. Read `scan.tsv`, classify results, and discard obvious false positives, saying why. Public learning material mentioning a product isn't the same as a customer's data.
5. Report `not-searched` entries: PDFs, Office files, images, nested or encrypted archives, and oversized files. Have the user review the ones that matter.
6. Also ask about Downloads, Desktop, Trash, and app data, where work files tend to collect.

Terms derived from one employer's material won't find another's customers. Say so. Short terms can match inside words and random bytes, so treat them as weak evidence.

Treat "nothing found" as unproven if the scan's self-test failed or if much of the disk was unreadable.

## Asking the user

Group items and give a recommendation. Say when something may be subject to an employment agreement, NDA, or data-protection rules, and suggest they check those before making a new long-term copy. Don't interpret the agreement. If they choose to keep something, respect that and record it.

For secrets and client data, suggest encryption. `migrate.py archive` doesn't encrypt, so the user would encrypt with their own tool, such as an encrypted disk image or `age`. Offer new credentials instead of copying old ones, and suggest revoking credentials for organizations they've left.

## Building archives

Confirm the destination has room, and check for an earlier archive. Don't assume same-named paths hold the same contents. Scope by contents and Git remotes, and check that nothing belonging to that owner was missed.

```json
{"name": "employer-a", "source": "user@old-mac:/Users/me", "items": ["projects/employer-a"], "dest_dir": "/Volumes/nas/archives", "approved_by_user": true, "notes": "Holds unencrypted credentials, by owner's choice."}
```

```sh
python3 migrate.py archive --plan archive.json
```

It builds under a temporary name, hashes the stream and the read-back, checks every file against the source, and writes `.sha256`, a file list, and a manifest. An existing archive is replaced only with `--replace`, and only if nothing from it would be lost. Report any `symlinks_pointing_outside`: those are stored as links only, so add the target or explain why not. Say in `notes` if it holds unencrypted secrets or client data.

Deleting originals is a separate, explicit step:

```json
{"base": "user@old-mac:/Users/me", "items": ["projects/employer-a"], "approved_by_user": true}
```

```sh
python3 migrate.py delete --plan delete.json --verify-archive /Volumes/nas/archives/employer-a.tar.gz
python3 migrate.py delete --plan delete.json --verify-archive /Volumes/nas/archives/employer-a.tar.gz --run
```

If the user encrypts an archive, they set and hold the password. Never handle it yourself. Remind them that losing it loses the archive, and that verifying afterward means they must open it.
