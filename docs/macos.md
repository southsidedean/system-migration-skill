# macOS notes

Behavior varies by macOS version, so treat these as a guide and check on your system.

## Privacy protections

macOS can refuse command-line access to some of your own folders, even with the right file permissions. You'll see `Operation not permitted`. Commonly protected:

- Mail, Messages, and Safari
- Photos and Photo Booth libraries
- Contacts, Calendar, Reminders, and Notes
- Some browser data in `~/Library/Application Support`

The skill records these as not verified, and asks you how to proceed.

### Full Disk Access

Granting Full Disk Access to your terminal lets commands read these folders, but it applies to everything that terminal runs. It's your choice, and the skill works without it, with more manual steps. To grant it: System Settings > Privacy & Security > Full Disk Access.

### Without Full Disk Access

- **Copying protected data:** archive it on the source, then unpack it with Finder at the destination. Finder usually isn't blocked.
- **Fixing permissions:** `chmod` can fail on protected folders. In Finder, select the folder, press Cmd-I, and use **Sharing & Permissions**.

### Permission pop-ups

Reading an app's settings can trigger a dialog on the Mac's screen. Approving it changes your privacy settings, so the skill avoids these reads where it can. If a dialog appears unexpectedly, read it before you click. You can review and undo approvals in System Settings > Privacy & Security.

## Copying with rsync

macOS includes its own `rsync`, called openrsync. Check with `rsync --version`.

- **Finder tags and some metadata aren't preserved.** Homebrew's `rsync` can keep extended attributes if you need them.
- **It can silently drop files.** A file list entry like `./#notes.txt` is dropped over SSH, and it still exits 0. `migrate.py copy` catches this and recovers.

## Apps

- **Homebrew:** a generated `Brewfile` makes reinstalling easier. Homebrew disables some casks that fail Apple's checks, though a formula may still exist.
- **App Store:** `mas` needs an App Store sign-in, and doesn't always find apps by ID.
- **Intel apps:** these need Rosetta. Install it with `softwareupdate --install-rosetta`.
- **Blocked downloads:** System Settings > Privacy & Security > **Open Anyway** overrides a safety check. Only use it for files from the vendor.
- **Version jumps:** reinstalling can move you up a major version, so check that licenses still apply.

## Passwords and keychains

- **Don't assume where your passwords are.** They may be in Passwords, a keychain, or a browser.
- **Login keychain:** `~/Library/Keychains/login.keychain-db` can be copied, then added with Keychain Access > File > Add Keychain. It opens with the keychain's password, which may differ from your current login password.
- **Local Items:** the folders with long ID names in `~/Library/Keychains` don't move as files, so review them on the old Mac.
- **Test it, and test again.** Copied keychains can change after you add them, and we've seen a copy start rejecting its password.
- **Browsers:** Chrome's saved passwords and cookies depend on a key in the old Mac's keychain, so they may not work after a copy. Firefox keeps its own.

## Mail

Accounts are best set up again by hand. Server-based mail downloads again when you sign in. Check for **On My Mac** mailboxes, which live only on that machine, and use Mailbox > Export Mailbox for those. Rules and signatures are in `~/Library/Mail/V*/MailData`, which Finder can copy. Restoring them is best effort, so take screenshots too.

## Sleep

Idle sleep can be short, even on power, and it can interrupt long jobs. Check with `pmset -g`. `scripts/run-awake.sh` keeps a Mac awake for one command, then stops.

## Time Machine

`tmutil` commands can hang or need Full Disk Access. Check backups in System Settings > General > Time Machine.

## Erasing

System Settings > General > Transfer or Reset > Erase All Content and Settings. Run the final check first.
