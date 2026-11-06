# System migration skill

A [Claude Code](https://claude.com/claude-code) skill that guides you through moving to a new computer, merging several into one, or folding another system into one you already use. It works on macOS and Linux.

Most migration tools copy your files and report success. This one is built to prove it, and to help with the decisions a tool can't make for you: what to leave behind, what belongs to a former employer, and when it's safe to erase the old machine.

## Why use it

- **It checks every copy.** Files are compared by hash, because a copy tool can exit cleanly and still leave things behind.
- **It doesn't guess about sensitive data.** It looks at what's in a file as well as its name, then asks you.
- **It tells you what it couldn't check,** and doesn't call that clean.
- **You stay in charge.** Nothing changes until you approve a plan, and you run any erase yourself.

## Quick start

You need Claude Code, Python 3.9 or later, and `rsync`. Install the skill:

```sh
git clone https://github.com/southsidedean/system-migration-skill ~/.claude/skills/system-migration
```

Then start Claude Code and describe what you want:

> Help me migrate from my old Mac to my new one.

Claude starts by looking, without changing anything. See [Getting started](docs/getting-started.md) for the full walkthrough.

## Documentation

| Read this | To learn |
|---|---|
| [Getting started](docs/getting-started.md) | How to install it and run your first migration |
| [How it works](docs/how-it-works.md) | The seven phases, and who does what |
| [Safety](docs/safety.md) | What it will never do, and what its results mean |
| [Sensitive data](docs/sensitive-data.md) | Handling former-employer, customer, and credential data |
| [Scenarios](docs/scenarios.md) | Walkthroughs: a new Mac, a new Linux machine, merging, and more |
| [macOS notes](docs/macos.md) and [Linux notes](docs/linux.md) | Platform differences and permissions |
| [Commands](docs/commands.md) | Every `migrate.py` command, plan format, and exit code |
| [Troubleshooting](docs/troubleshooting.md) | Common problems and questions |
| [Contributing](CONTRIBUTING.md) | How to set up, test, and change the skill |
| [Security](SECURITY.md) | How to report a problem |

## Status

This is an early release. Use it alongside your own backups.

- **Tested:** the scripts run in CI on macOS and Ubuntu, on Python 3.9 and the latest Python, including copies over real SSH connections.
- **Partly tested:** 3 of the 15 [eval scenarios](evals/README.md) have run as real Claude sessions, once each, on Linux.
- **Not yet supported:** Windows, and encrypted archives. To encrypt an archive, use your own tool.

This skill reduces risk, but doesn't remove it. It flags possible contractual or legal concerns about data you hold, but it doesn't give legal advice.

## Project layout

| Path | What it is |
|---|---|
| `SKILL.md` | The rules and phases Claude follows |
| `references/` | Detail for Claude on each phase and platform, loaded when needed |
| `docs/` | Guides for people |
| `templates/` | Status doc, decisions log, and archive manifest |
| `scripts/` | `migrate.py` and its helpers, which do the deterministic work, plus tests |
| `evals/` | Test scenarios with planted traps |

## License

[MIT](LICENSE)
