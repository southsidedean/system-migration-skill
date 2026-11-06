# Phase 4: Copy and verify

Copy one stage at a time, and verify it before starting the next. Use `migrate.py copy`, which avoids the traps below and verifies every file by hash.

```json
{"source": "user@old-mac:/Users/me", "dest": "/Users/me", "items": ["Documents", "#notes.txt"], "approved_by_user": true}
```

```sh
python3 migrate.py copy --plan stage-1.json        # dry run
python3 migrate.py copy --plan stage-1.json --run  # copy and verify
```

Exit 0 means every planned file is at the destination with the same hash. Different files are never overwritten; they're reported for review. Read `stage-1.json.result.json` only if the result isn't clean.

## Before copying

- Confirm a recent, successful backup of the source and that the user approved the plan.
- Do a dry run, and confirm it prints the files it would transfer. A dry run that lists nothing proves nothing.
- Close apps whose data is being copied.
- Use `scripts/run-awake.sh` for anything long, on both ends.

## Known traps

For anything `migrate.py copy` can't handle, and so you recognize these in a user's own scripts:

| Trap | What happens | What to do |
|---|---|---|
| `rsync --files-from` | `-a` no longer implies `-r`, so listed folders arrive empty and it still exits 0 | Add `-r`, then verify |
| `#` or `;` starting a line in a files-from list | Treated as a comment and silently dropped, still with exit 0. On macOS, `./#name` is also dropped over SSH, though it works locally. | `migrate.py copy` retries anything missing through a `tar` stream, and then verifies. Elsewhere, verify and copy dropped files separately. |
| rsync without `--ignore-existing` on a re-run | Overwrites newer files at the destination | Don't call a copy script safe to re-run once the destination is in use. Re-run with `--ignore-existing` or `--update`. |
| Unquoted paths in remote commands | Spaces, unicode, or `#` split or truncate arguments | Use NUL-delimited lists or pipe a script over stdin |
| `ssh` in a loop or script | Reads the script's stdin | Use `ssh -n` unless deliberately piping |
| Background keep-awake over SSH | Killing the local `ssh` can leave the remote process running | Wrap the command itself: `run-awake.sh <command>` |
| Filters and pipelines | A bug can produce empty output that looks clean | Use positive controls and reconcile the counts |
| Hard links, sparse files, attributes, ACLs | Lost or expanded without the right flags | See the platform file, and say what wasn't preserved |
| Sync placeholders | Reading them downloads data, or fails | Find them first. Decide whether to download. |

## Verifying a stage

Inventory the destination again, and compare:

```sh
python3 compare.py --source source-a.tsv --dest dest.tsv --output compare-a
```

It writes `summary.json` and `classified.tsv`, and exits non-zero if the counts don't reconcile. Review each class:

| Class | Meaning | Action |
|---|---|---|
| `identical` | Same path, same hash | None |
| `moved` | Same hash at another path | Confirm this is expected, and confirm that it isn't just a coincidental match on a tiny file |
| `different` | Same path, different hash | Check which is newer and why. Opening an app changes its database. |
| `missing` | Not found at destination | Check against `decisions.md`. Copy it, or confirm that it was deliberately left. |
| `blocked` | Destination path unreadable | NOT VERIFIED. Offer the user a way to check. |
| `unverified` | Couldn't be hashed | NOT VERIFIED |
| `type-mismatch` | File versus folder or link | Investigate |

`empty_dirs_at_dest` lists folders with contents on the source but none at the destination. This is the signature of a copy that silently failed, so resolve every entry.

Report distinct content as well as file counts. Many duplicates can make something look bigger than it is, and look inside a folder before offering it as a choice.

Mapping decisions onto results is a judgment call. Report what remains, and don't round a large `different` or `missing` count down to "looks fine".

## Credentials

- Set restrictive permissions right after copying.
- Test that a copied credential store opens at the destination, immediately and again later. Some systems rewrite a store after it's added.
- Note that a copy goes stale as soon as the source changes.
