# Getting started

This guide takes you from nothing installed to your first migration. Allow about 10 minutes for setup. The migration itself takes as long as your data does.

## Before you begin

You need:

- **[Claude Code](https://claude.com/claude-code)** on the machine you'll work from, usually the new one.
- **Python 3.9 or later** on every machine. Check with `python3 --version`. On a Mac without it, run `xcode-select --install`.
- **`rsync`** on both ends of a copy. It comes with macOS and most Linux systems.
- **A way for the machines to reach each other,** if you're copying between them. SSH keys are simplest; [How to connect two machines](#how-to-connect-two-machines) covers that.
- **A recent backup of anything you can't afford to lose.** The skill doesn't replace one.

## 1. Install the skill

```sh
git clone https://github.com/southsidedean/system-migration-skill ~/.claude/skills/system-migration
```

## 2. Check that it works

```sh
python3 ~/.claude/skills/system-migration/scripts/validate_skill.py
python3 ~/.claude/skills/system-migration/scripts/test_migrate.py
```

The first should end with `skill valid`, and the second with `OK`. It's normal for it to say `skipped=3`: those are the tests that need a remote machine.

## 3. Start a migration

Start Claude Code, and describe what you're doing in your own words:

> Help me migrate from my old Mac, `me@old-mac`, to this one. I want my documents and projects, but I don't need anything from my old job.

Claude loads the skill on its own. If it doesn't, ask it to "use the system-migration skill".

## 4. What happens next

Claude walks you through these phases, asking as it goes. [How it works](how-it-works.md) explains each one.

1. **Discover:** it inventories each machine without changing anything, and tells you what it couldn't read.
2. **Decide:** it asks what to keep, leave, archive, or delete, in small batches, with a recommendation for each.
3. **Plan:** it writes down what will happen, and separates what it can do from what needs you.
4. **Migrate:** it copies in stages, and checks each stage by hash before going on.
5. **Archive:** it saves anything that's leaving the active system, if you want that.
6. **Audit:** independent reviewers check the result, with no sampling.
7. **Decommission:** a final check before you erase the old machine.

You can stop at any point. Everything's recorded in a migration folder, such as `~/migration-old-mac-2026-11/`, so a later session can pick up where you left off:

> Let's continue the migration in `~/migration-old-mac-2026-11`.

## 5. Small jobs

You don't need the full process for one task. Ask directly, and Claude uses just the part it needs, with a dry run first:

> Copy `~/Documents/taxes` from `me@old-mac` to here, and verify it.

## How to connect two machines

Run these on the new machine.

1. Turn on SSH on the old machine:
   - **macOS:** System Settings > General > Sharing > Remote Login.
   - **Linux:** `sudo systemctl enable --now ssh`, or `sshd` on some systems.
2. Create a key, if you don't have one:

   ```sh
   ssh-keygen -t ed25519
   ```

3. Copy it to the old machine:

   ```sh
   ssh-copy-id me@old-machine
   ```

4. Test it. This should print `connected`, without asking for a password:

   ```sh
   ssh -o BatchMode=yes me@old-machine echo connected
   ```

If the machines can't connect, Claude can still give you commands to run on each one, or you can move data with an external drive.

## Tips

- **Keep the old machine intact** until the final check passes. It's your best safety net.
- **Keep both machines awake and on power** during long copies. On a Mac, the skill keeps a machine awake only while its own command runs.
- **Try a small job first** if you want to see how it behaves.

## Next steps

- [Scenarios](scenarios.md): walkthroughs for common migrations.
- [Safety](safety.md): what it will and won't do.
- [Troubleshooting](troubleshooting.md): if something doesn't work.
