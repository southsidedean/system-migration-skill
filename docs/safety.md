# Safety

A migration can lose data for good, so the skill is cautious by design. This page explains what it does to protect you, and where that protection ends.

## What it's designed never to do

- **Change anything before you approve a plan.** Discovery is read-only.
- **Overwrite newer files at the destination.** They're reported instead.
- **Delete by wildcard.** Deletes use exact paths, with a dry run first. If one path can't be found, nothing is deleted.
- **Show your secrets or file contents.** Reports use paths, sizes, hashes, and counts.
- **Read your credential stores,** such as keychains, even as raw bytes.
- **Erase a machine.** You do that yourself, after the final check.
- **Work around a permission block.** It tells you, and leaves the choice to you.
- **Send your data to an outside service** without asking.

## What the results mean

| You see | It means |
|---|---|
| `identical` | Same path, same hash. The copy's confirmed. |
| `moved` | Same contents at a different path |
| `different` | Same path, different contents. Review it. Opening an app can change its files. |
| `missing` | Not at the destination. Copy it, or confirm you meant to leave it. |
| `blocked` | The destination couldn't be read, so this wasn't checked |
| `unverified` | The file couldn't be hashed, so this wasn't checked |
| **NOT VERIFIED** | It couldn't be checked. That doesn't mean there's a problem, or that there isn't. |

Exit codes are fixed: `0` is OK, `1` means a check failed, and `2` means bad input or incomplete data.

## The final check

Before you erase a machine, the gate needs current evidence for eight things:

| Check | Means |
|---|---|
| `final-compare` | A comparison after your last use of the source, with nothing missing that you haven't decided about |
| `final-backup` | A backup that finished after the last change |
| `credentials-retested` | Copied credentials still open at the destination, tested again later |
| `secrets-reviewed` | You've reviewed anything that can't be copied |
| `git-clean` | No uncommitted or unpushed work you still want |
| `local-app-data-checked` | Local-only mail, notes, chat history, and app data have been checked |
| `archives-verified` | Archives are verified and readable |
| `licenses-and-accounts` | Licenses are deauthorized, and you've signed out where needed |

Evidence goes stale after 24 hours by default, or as soon as the source changes. You can accept a risk, with a note saying what you accepted, and it stays visible in the results.

## What it can't protect you from

Please know these limits:

- **Approval is a process, not a lock.** Plans need `"approved_by_user": true`, but Claude writes that file, based on what you've told it. Read what it shows you before you approve.
- **The final check trusts its evidence.** Most checks are recorded by Claude or you. Only the comparison reads actual results.
- **Blocked folders stay unknown.** Without Full Disk Access on macOS, it can't read Mail, Messages, and other protected data at the destination.
- **Content searches have gaps.** The scan can't read inside PDFs, Office files, images, or archive contents. It lists those as not searched.
- **Backups aren't tested.** It doesn't restore your backups to prove they work.
- **Session transcripts can hold what Claude has seen.** Claude Code keeps transcripts on your machine, so anything printed during a session may stay there.
- **It's software, and it can be wrong.** Keep your own backups, and read before you approve.

If something does go wrong, the old machine is your safety net, which is why it stays intact until the end.

## Your data

The scripts run on your own machines and don't send anything anywhere themselves. Your conversation with Claude goes to Anthropic under your account's terms, so what Claude reads in a session is part of that. The skill keeps reports to paths and counts partly for this reason.
