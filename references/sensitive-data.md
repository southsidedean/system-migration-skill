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

Keep, leave behind, archive, encrypted archive, delete, or review later. Record every decision in `decisions.md`. "Leave behind" on a source that will be erased means "delete", so say so.

## Finding it

Names aren't reliable. For example, a folder called `Insurance` might hold a customer's gateway configs.

1. Ask what past employers, clients, and regulated work the machine has seen. Offer to skip this if they'd rather not say.
2. Build a terms file, one per line: organization names, product names, email domains, and ticket formats. Terms stay in the migration folder, not in anything shared.
3. Run the scan on each machine:
   ```sh
   python3 scan_sensitive.py --root $HOME --terms terms.txt --output scan.tsv
   ```
4. Read `scan.tsv`, classify results, and discard obvious false positives, saying why. Public learning material mentioning a product isn't the same as a customer's data.
5. Report `not-searched` entries: PDFs, Office files, images, nested or encrypted archives, and oversized files. Have the user review the ones that matter.
6. Also ask about Downloads, Desktop, Trash, and app data, where work files tend to collect.

Treat "nothing found" as unproven if the scan's self-test failed or if much of the disk was unreadable.

## Asking the user

Group items and give a recommendation. Say when something may be subject to an employment agreement, NDA, or data-protection rules, and suggest they check those before making a new long-term copy. Don't interpret the agreement. If they choose to keep something, respect that and record it.

Prefer encrypted archives for secrets and client data. Offer new credentials instead of copying old ones, and suggest revoking credentials for organizations they've left.

## Building archives

1. Confirm the destination is writable and has room. Note how much will be free afterward.
2. Check for an earlier archive. Don't assume same-named paths hold the same contents.
3. Write each archive under a temporary name, and rename it only after it's complete.
4. Verify all of these:
   - The stream hash matches a fresh hash read back from the destination.
   - The archive lists without errors.
   - The entry count matches the source.
   - Symlinks that point outside the archive are listed and either added or explained.
5. Save with the archive: its `.sha256`, a file list, and a manifest using `templates/archive-manifest.md`. Say in the manifest if it holds unencrypted secrets or client data.
6. Delete the originals only as a separate, explicit step.

Encrypted archives need a password the user controls. Never handle it yourself, and have them type it at a prompt. Remind them that losing it loses the archive.
