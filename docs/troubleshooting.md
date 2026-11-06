# Troubleshooting

## Setup

**Claude doesn't use the skill.** Check that it's at `~/.claude/skills/system-migration/SKILL.md`, then start a new Claude Code session, and ask it to "use the system-migration skill".

**`python3` isn't found, or it's too old.** You need 3.9 or later. On a Mac, run `xcode-select --install`. On Linux, use your package manager.

**`couldn't reach me@host`.** Test the connection: `ssh -o BatchMode=yes me@host python3 --version`. Your SSH key needs to be set up, and that machine needs `python3`. See [How to connect two machines](getting-started.md#how-to-connect-two-machines).

**`Host key verification failed`.** You haven't connected to that machine before. Connect once with `ssh me@host`, and check its fingerprint.

## Copying

**`different=1` and exit 1.** The destination already has a different version, and it wasn't overwritten. Details are in the `.result.json` file. Decide which to keep.

**`rsync dropped 1 item(s) while exiting 0`.** The file was recovered with `tar` and verified, so you don't need to do anything. Some `rsync` versions drop certain names.

**The dry run lists nothing.** Either everything's already there, or the plan is wrong. Check its paths.

**`the plan doesn't have "approved_by_user": true`.** A plan must be approved before it runs. Check it first, then have Claude set this, or set it yourself.

**`items must be paths inside the base folder`.** Items need to be relative paths, without `..`, such as `Documents/taxes`.

## Permissions

**`Operation not permitted` on a Mac.** macOS is protecting that folder. See [macOS notes](macos.md#privacy-protections). The skill records it as not verified, and doesn't work around it.

**A permission dialog appeared.** Something tried to read a protected app's settings. Read it before you click. If you've approved it, you can undo that in System Settings > Privacy & Security.

**`Permission denied` on Linux.** The path probably needs root. It's marked not verified, unless you choose to give access.

## Results

**Lots of `different` files.** Opening an app changes its files, so databases and `.DS_Store` often differ. Look at where they are before worrying, but don't dismiss them all without looking.

**A file shows as `moved`.** Its contents exist at another path. Check that this is what you expected.

**A folder is listed in `empty_dirs_at_dest`.** It has files on the source and none at the destination, which is usually a failed copy. Resolve each one.

**The gate failed, but I've done the checks.** Evidence goes stale after 24 hours, or when the source changes. Record the check again, once you've rechecked.

**Inventory says `#END` is missing.** The run didn't finish. Run it again.

**The scan says `SELF-TEST FAILED`.** Its search can't find a planted match, so results couldn't be trusted, and it won't run. Run `python3 scripts/test_scripts.py`, and [report it](https://github.com/southsidedean/system-migration-skill/issues).

**The machine went to sleep during a long job.** Use `scripts/run-awake.sh <command>`, and keep it on power.

## Questions

**Do I need this if my new Mac is untouched and I want everything?** Maybe not. Apple's Migration Assistant may be simpler. This skill is for leaving things behind, for merging, and for when you want proof.

**Does it work on Windows?** Not yet.

**Are archives encrypted?** No. Use your own tool, such as an encrypted disk image or `age`, and keep the password yourself.

**Will it use a lot of tokens?** Small jobs and normal phases are designed to use few, since scripts do the heavy work. Independent audits can use a lot, so Claude tells you first.

**Can I stop and come back?** Yes. Ask Claude to continue from your migration folder. It re-checks the current state, because things may have changed.

**What if Claude's wrong?** It can be. Read plans before you approve them, keep your own backups, and keep the old machine until the final check passes.

## Still stuck?

[Open an issue](https://github.com/southsidedean/system-migration-skill/issues). Please remove anything private first, including hostnames, paths, and customer names, since issues are public. For security problems, see [SECURITY.md](../SECURITY.md).
