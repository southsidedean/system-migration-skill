# Scenarios

Each walkthrough shows what to ask for and what to watch out for. The names are examples.

## A new Mac

**You have:** an old Mac and a new one on the same network.

**Ask:**

> Help me migrate from `me@old-mac` to this Mac. I want everything personal. Leave old job files behind.

**Expect:**

1. An inventory of both Macs, with a list of folders macOS blocks.
2. Questions in batches about apps, data, and settings.
3. Installs, often from a generated `Brewfile`.
4. Staged copies, each verified.
5. A list of things only you can do: sign-ins, licenses, and opening each app once.

**Watch for:** photo libraries and browser profiles usually can't be written from the command line. Claude will archive them, and ask you to unpack them in Finder. See [macOS notes](macos.md). If you want everything and the new Mac is untouched, Apple's Migration Assistant may be simpler.

## A new Linux machine

**You have:** an old and a new Linux machine, reachable by SSH.

**Ask:**

> Move my home folder and services from `me@old-box` to this machine. It's Ubuntu 24.04 on both.

**Expect:** the same phases, plus a look at `/etc`, `/opt`, and databases and containers under `/var/lib`, which are easy to forget.

**Watch for:** user IDs that differ, and live databases. Stop them or use their own dump tools. See [Linux notes](linux.md).

## Moving from Mac to Linux, or the reverse

**Ask:**

> I'm moving from my Mac, `me@old-mac`, to this Linux machine. I want my documents and projects.

**Expect:** files and most dotfiles can move. Apps and system settings generally can't, so Claude lists what to find and set up again.

**Watch for:** macOS Finder tags and other metadata don't carry over. Linux filenames are case-sensitive, so names that differ only by case aren't a problem going to Linux, but can collide going to a Mac.

## Merging several machines into one

**You have:** a work laptop and a home desktop, and one new machine.

**Ask:**

> Merge `me@laptop` and `me@desktop` into this new machine.

**Expect:**

1. Inventories of both before anything's copied.
2. A list of paths where the two hold different files.
3. A question about a rule. The usual choice is one primary machine that keeps its paths, with the other in `~/from-desktop/`.

**Watch for:** settings can only have one winner, so choose a primary for shell config and editor settings. The default keeps both copies of any conflicting file.

## Absorbing a machine into one you already use

**You have:** a machine you use every day, and an old one to fold in.

**Ask:**

> Bring what I need from `me@old-laptop` into this machine. This one's in daily use, so don't overwrite anything.

**Expect:** a backup check on your current machine first, then a copy into `~/from-old-laptop/` to merge by hand, or a copy that skips anything that exists.

**Watch for:** the destination has live data, so this is the riskiest shape if done carelessly. If you ran the skill before, Claude can reuse earlier decisions, but it asks first.

## Consolidating active systems

**You have:** several machines still in use, and you want fewer.

**Ask:**

> I want to retire `me@server-a` and move its services to `me@server-b`. Both are live.

**Expect:** a plan for which system is the authority for each kind of data, a final catch-up pass, and a cut-over date.

**Watch for:** data keeps changing until cut-over, and a scheduled job could run in two places, or none.

## Clearing out former-employer data

**Ask:**

> I've left my old job. Find what's still on this machine from them, and help me decide what to do.

**Expect:** a scan by name and contents, a list sorted by owner and whether it's secret, and your choice for each. See [Sensitive data](sensitive-data.md).

**Watch for:** browser profiles and old backups can still hold employer data after you've deleted the files.

## One small job

**Ask:**

> Copy `~/Documents/taxes` from `me@old-mac` to here, and verify it.

**Expect:** a dry run, the copy, and a hash check, with no migration folder or phases.
