# Commands

Claude runs these for you, so you don't need to learn them. They're documented so you can see what's happening, or run them yourself. Everything's under `scripts/`, and needs only Python 3.9 or later.

```sh
python3 scripts/migrate.py <command> [options]
```

## Exit codes

| Code | Means |
|---|---|
| `0` | OK |
| `1` | A check failed |
| `2` | Bad input, or incomplete data |

Locations can be local paths or `user@host:/path`. Remote machines need SSH keys and `python3`.

## Migration state

### `init`

Creates a migration folder. It refuses a folder that's in use.

```sh
python3 scripts/migrate.py init --dir ~/migration-old-mac-2026-11 --shape one-to-one --source old-mac --dest new-mac
```

Shapes: `one-to-one`, `many-to-one`, `absorb`, `consolidate`. Repeat `--source` for each source.

### `status`

Prints the phase, decisions awaiting review, and the next step.

```sh
python3 scripts/migrate.py status --dir ~/migration-old-mac-2026-11
```

### `advance`

Moves to a phase, from 1 to 7.

```sh
python3 scripts/migrate.py advance --dir ~/migration-old-mac-2026-11 --to 2
```

### `decide`

Records a decision, and updates `decisions.md`.

```sh
python3 scripts/migrate.py decide --dir ~/migration-old-mac-2026-11 --source old-mac --item "Documents/old-job" --owner employer --secret no --action archive --reason "keep a copy for now"
```

- `--owner`: `personal`, `employer`, `client`, `regulated`, or `unknown`
- `--secret`: `yes` or `no`
- `--action`: `keep`, `leave`, `archive`, `encrypted-archive`, `delete`, or `review-later`

## Facts about a machine

### `collect`

Saves apps, packages, and some settings as JSON. Read-only. It skips secrets, and app settings that can trigger permission prompts.

```sh
python3 scripts/migrate.py collect --output old-mac.json
```

### `inventory`

Lists every file, with its hash. Run it on the machine that holds the files. Caches, known credential stores, password-manager files, and SSH private keys are counted, but not opened.

```sh
python3 scripts/migrate.py inventory --root home=$HOME --root apps=/Applications --output old-mac.tsv
```

Use the same `--root` labels on each machine, so paths line up across different usernames. Add `--exclude <glob>` to skip more.

### `compare`

Classifies every source file against the destination, and fails if the counts don't reconcile. [Safety](safety.md#what-the-results-mean) explains the classes.

```sh
python3 scripts/migrate.py compare --source old-mac.tsv --dest new-mac.tsv --output compare-1
```

It writes `compare-1/summary.json` and `compare-1/classified.tsv`. Excluded paths, such as caches and credential stores, are listed as not compared. For a merge, list paths that conflict across sources:

```sh
python3 scripts/migrate.py compare --conflicts laptop.tsv desktop.tsv --output conflicts
```

### `scan`

Searches names and contents for your terms, and flags likely secrets. It reports paths and counts, never matching text. If its self-test can't find a planted match, it refuses to run.

```sh
python3 scripts/migrate.py scan --root $HOME --terms terms.txt --output scan.tsv
```

## Actions that use a plan

A plan is a JSON file. To run, it needs an approval tied to its exact contents, so editing it afterward voids the approval:

```sh
python3 scripts/migrate.py approve --plan stage-1.json                        # shows the plan
python3 scripts/migrate.py approve --plan stage-1.json --user-said "go ahead" # records your words
```

### `copy`

A dry run by default. With `--run`, it copies, keeps newer destination files, retries anything dropped, and checks every file by hash. Run it on the destination.

```json
{
  "source": "me@old-mac:/Users/me",
  "dest": "/Users/me",
  "items": ["Documents", "Pictures/Trips", "notes.txt"]
}
```

```sh
python3 scripts/migrate.py copy --plan stage-1.json
python3 scripts/migrate.py copy --plan stage-1.json --run
```

Items are relative to `source`. Details go to `stage-1.json.result.json`, or the path in `--report`.

### `archive`

Builds a `.tar.gz`, checks every file against the source, and writes a checksum, file list, and manifest. It doesn't encrypt.

```json
{
  "name": "old-job",
  "source": "me@old-mac:/Users/me",
  "items": ["projects/old-job"],
  "dest_dir": "/Volumes/nas/archives",
  "notes": "Holds unencrypted credentials, by my choice."
}
```

```sh
python3 scripts/migrate.py archive --plan archive.json
```

`--replace` rebuilds an existing archive, but only if nothing in it would be lost. `--allow-shrink` allows losing entries.

### `delete`

A dry run by default. It deletes exact paths only, and stops without deleting anything if one is missing. Wildcards don't expand.

```json
{
  "base": "me@old-mac:/Users/me",
  "items": ["projects/old-job"]
}
```

```sh
python3 scripts/migrate.py delete --plan delete.json
python3 scripts/migrate.py delete --plan delete.json --run
```

`--verify-archive <file>` stops unless every file matches that archive, which needs to be on the machine running the command.

## The final check

### `record`

Records dated evidence for a source.

```sh
python3 scripts/migrate.py record --dir . --source old-mac --kind final-compare --status pass --file compare-1/summary.json
python3 scripts/migrate.py record --dir . --source old-mac --kind git-clean --status accepted-risk --note "I'm keeping these changes"
```

- `--kind`: `final-compare`, `final-backup`, `credentials-retested`, `secrets-reviewed`, `git-clean`, `local-app-data-checked`, `archives-verified`, or `licenses-and-accounts`
- `--status`: `pass`, `fail`, or `accepted-risk`, which needs a `--note`

### `gate`

Fails if evidence is missing or stale. It never erases anything.

```sh
python3 scripts/migrate.py gate --dir . --source old-mac --source-changed 2026-01-31T10:00:00-06:00
```

Evidence older than `--source-changed`, or than `--max-age-hours` (24 by default), counts as stale.

## Other scripts

| Script | Use |
|---|---|
| `scripts/run-awake.sh <command>` | Keeps the machine awake for one command, then stops |
| `scripts/validate_skill.py` | Checks that the skill is well formed |
| `scripts/check.sh` | Runs the local checks |
| `scripts/test_scripts.py`, `scripts/test_migrate.py` | The script tests |
| `evals/run_eval.py` | Builds and scores eval scenarios |
