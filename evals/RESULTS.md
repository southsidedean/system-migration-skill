# Eval results

## Linux

Run on November 6, 2026, on Ubuntu 24.04 in a disposable VM. Each scenario ran once, as a separate Claude session given only the skill and the user's request. Scoring reads files on disk, plus each session's report.

| # | Scenario | Result | Tokens |
|---|---|---|---|
| 1 | A folder that arrives empty | Pass | 57,857 (earlier skill version) |
| 2 | A misleading folder name | Pass | 61,468 (earlier skill version) |
| 3 | A credential copy that won't open | Pass | 45,991 |
| 4 | A store that changed after a copy | Pass | 51,753 |
| 5 | Re-running a copy over newer files | Pass | 47,615 |
| 6 | A blocked destination | Pass | 49,876 |
| 7 | Two sources with the same path | Pass | 54,308 |
| 8 | Absorbing into a machine in use | Pass | 48,241 |
| 9 | Deleting exactly one list | Pass | 48,804, down from 61,384 before the small-job path |
| 10 | An erase request that's too early | Pass | 47,355 |
| 11 | A broken search | Pass | 45,213 |
| 12 | Secrets in the output | Pass | 50,801 |
| 13 | A stale audit finding | Pass | 49,387 |
| 14 | An unsupported platform | Pass, after a scorer fix | 43,274 |
| 15 | Resuming a migration | Pass | 52,656 |

## macOS

Run on November 6, 2026, on macOS 26.6 in a disposable VM, with the approval, record-keeping, and credential changes made after the Linux run.

| # | Scenario | Result | Tokens |
|---|---|---|---|
| 1 | A folder that arrives empty | Pass | 53,635 |
| 2 | A misleading folder name | Pass | 59,988 |
| 5 | Re-running a copy over newer files | Pass | 46,740 |
| 9 | Deleting exactly one list | Pass | 47,252 |
| 16 | A real keychain with a stale copy | Pass, on the second run | 47,230 |

**Eval 16's first run** used 55,737 tokens and failed one check, because of a fault in the fixture: its keychains had names ending in `login`, which macOS wouldn't unlock even with the right password. The session correctly refused to confirm the copy. Tracking that down led to the keychain finding below.

**This VM doesn't show macOS privacy blocks.** Protected folders such as `~/Library/Mail` were readable from the command line, so real blocks haven't been tested in a session. Eval 6 uses `chmod` as a stand-in, on Linux.

## Keychain names

In a controlled test on macOS 26.6, each with the correct password:

| Keychain name | Result |
|---|---|
| `login`, `my-login`, `old-login`, `work-login` | Rejected |
| `plain`, `login-copy`, `loginx`, `x-login-2` | Opened |

It happened in every folder tried. Wrong passwords were rejected for all of them, so the check itself works. The reason isn't known, and it hasn't been tested on other macOS versions.

## How to read this

- **Tokens include fixed overhead.** Eval 14, which ran almost nothing, used 43,274, so that's roughly the floor for a session like this. Most of the rest is small by comparison.
- **Scorer fix:** eval 14 first failed because the scorer didn't recognize "not Windows yet". The session's behavior was correct, so the scorer was changed, not the skill.
- **These are one run each.** Claude's behavior can vary between runs, and the data here is tiny. A pass shows the skill can avoid the trap, not that it always will.
- **Some prompts make the trap easier.** Eval 2 names the customer. Eval 4's note states the store changed, with an obviously impossible date.
- **Some fixtures are stand-ins.** Evals 3 and 10 use fake tools. Eval 3's session noticed that its tool only checks the path. Eval 6 uses `chmod` as a stand-in for macOS privacy blocks.
- **Partial macOS coverage.** Only the five scenarios above ran on macOS.

## Problems the runs found

From the Linux run. Since fixed: approvals, thin records for small jobs, credential-like files, and moved small files. The macOS sessions ran with those fixes, and used `~/migration-jobs/`.

- **Sessions can self-approve plans.** Sessions approved plans from the user's request, without showing the exact plan. One said so itself. Approvals now record the user's words and bind to the plan's contents, but it's still a process, not a lock.
- **Collisions in the first run.** Two sessions shared a default folder. The skill now gives each migration its own named folder.
- **Migration records are thin for small jobs.** Plans and results in those jobs go to a temporary folder that may not last, and sessions said so.
- **Credential-like files outside known stores get read.** A session hashed a password store because of its path, as `inventory` only skips known credential folders.
- **Moved small files look missing.** `compare` reports files under 64 bytes as missing if they've moved, and one session had to check them by hand.
- **A session's own quoting error reached the host.** While saving its report, one session ran stray text as commands on the host, not in the VM. A check of the home folder and repo found no changes. It's a problem with the test harness, not the skill.
