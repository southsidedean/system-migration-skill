# Security

## Reporting a problem

Please report security problems privately, through GitHub: on the repository's **Security** tab, choose **Report a vulnerability**, or use [this link](https://github.com/southsidedean/system-migration-skill/security/advisories/new). Please don't open a public issue.

Say what the problem is and how to reproduce it. Remove any real data from your report.

This is a personal project, so responses are on a best-effort basis.

## Supported versions

Only the latest version on `main` gets fixes.

## What counts as a security problem

For example:

- A script printing secrets or file contents
- A delete, copy, or archive touching paths outside its plan
- Credential stores being read
- A check reporting success when it shouldn't, in a way that could lose data
- Unsafe handling of file names that could run a command

## How the skill limits the damage

- **No dependencies:** the skill uses only Python's standard library.
- **No network calls of its own:** the scripts only contact machines you name, over SSH.
- **No shell for file names:** paths go to tools as arguments or over stdin. The one exception is the base folder in a remote `tar` command, which is quoted.
- **Plans and dry runs:** destructive commands need an approved plan, and `copy` and `delete` default to a dry run.
- **A pinned CI:** actions are pinned to exact commits, with minimal permissions.

## Limits

[Safety](docs/safety.md) covers what the skill can't protect you from, including that plan approval is a process, not a lock.

## Your data

The scripts don't send anything anywhere themselves. Your conversation with Claude is subject to your account's terms, and Claude Code keeps session transcripts on your machine. Your migration folder can name real people and organizations, so keep it private.
