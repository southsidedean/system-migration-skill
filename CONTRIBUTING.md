# Contributing

Thanks for helping. Bug reports, tested platform notes, and new eval scenarios are all useful.

## Setting up

```sh
git clone https://github.com/southsidedean/system-migration-skill
cd system-migration-skill
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
scripts/check.sh
```

The skill itself needs only Python 3.9 or later. The tools in `requirements-dev.txt` are for checks. `shellcheck` is separate, and comes from your package manager.

## Making a change

1. Create a branch.
2. Make your change, and add a test for anything that changes behavior.
3. Run `scripts/check.sh`.
4. Open a pull request. Merges to `main` are squash merges, and need the required checks to pass.

## Design rules

- **Scripts handle facts, and Claude handles judgment.** If something should come out the same way every time, it belongs in a script.
- **Standard library only, Python 3.9 or later.** Users shouldn't need to install anything.
- **An empty result must not look like success.** Fail instead, or use a positive control.
- **Never print file contents or secrets.** Report paths, sizes, hashes, and counts.
- **Destructive commands need a dry run and an approved plan.**
- **Keep `SKILL.md` short.** It loads on every use. Detail goes in `references/`, and `scripts/validate_skill.py` enforces a limit.
- **Keep commands short by default.** Print a summary, write detail to a file, and use the fixed exit codes.

## Keep private data out

This repository is public. Use made-up names like `ExampleCustomer` and `old-mac`. Never commit real hostnames, employers, customers, or anything from a real migration. CI scans for secrets and stray migration output, but it can't recognize your private names, so check your own diff.

## The checks

`scripts/check.sh` runs what works locally. CI also runs tests on macOS and Ubuntu, tests over real SSH, `markdownlint`, `gitleaks`, `zizmor`, `actionlint`, CodeQL, dependency review, and a link check, which doesn't block merging. To run the SSH tests yourself, against a host that can read your temporary folder:

```sh
MIGRATE_TEST_HOST=user@host python3 scripts/test_migrate.py
```

## Evals

[Evals](evals/README.md) test how Claude behaves with the skill, using planted traps. `evals/test_evals.py` runs in CI, and checks that the traps exist and that the scoring can fail. Full sessions use tokens, so they run by hand:

```sh
python3 evals/run_eval.py build 1 /tmp/eval-1
# Run a Claude session with the printed prompt, somewhere disposable, then:
python3 evals/run_eval.py score 1 /tmp/eval-1 report.txt
```

Don't tell the session about the trap or the scoring. Record the tokens each run uses in `evals/RESULTS.md`.

## Docs

Write for someone who isn't an expert. Use plain language and short steps, and say what could go wrong. If you change a command, update `docs/commands.md`, and add a line to `CHANGELOG.md`.
