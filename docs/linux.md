# Linux notes

The scripts are tested in CI on Ubuntu. These notes also cover other distributions, but haven't all been tested on them, so check on your system.

## What's different from a Mac

- **More lives outside your home folder.** Check `/etc`, `/opt`, `/usr/local`, `/srv`, and data under `/var/lib`.
- **Reading some paths needs root.** The skill won't ask for root on its own. Anything it can't read is marked not verified, unless you choose to give it access.
- **Services matter more.** Check `systemctl` units, timers, and cron jobs.

## Packages

The right command depends on your distribution:

| Distribution | Packages you installed |
|---|---|
| Debian, Ubuntu | `apt-mark showmanual` |
| Fedora, RHEL | `dnf repoquery --userinstalled` |
| Arch | `pacman -Qqe` |
| Any | `flatpak list --app`, `snap list` |

`migrate.py collect` runs the ones it finds and saves the results.

## Copying

- **Compare user and group IDs first.** Run `id` on both machines. A mismatch can leave files owned by the wrong person.
- **Preserve what you need.** For a system copy, a typical command is `rsync -aHAX --numeric-ids`. Drop `--numeric-ids` if IDs differ and you want names matched instead. `migrate.py copy` uses a simpler `-a`, which doesn't keep hard links, ACLs, or extended attributes.
- **Stop databases and containers first,** or use their own dump tools. A copy of live files can be corrupt even though its hash matches.
- **SELinux contexts may not transfer.** On Fedora or RHEL, you may need `restorecon`.

## Passwords and keys

- **GNOME Keyring:** `~/.local/share/keyrings`
- **KWallet:** `~/.local/share/kwalletd`
- **Others:** `~/.gnupg`, `~/.ssh`, `~/.password-store`, and cloud tool folders

The scan and inventory skip the keyring, KWallet, GnuPG, and `pass` stores on purpose. For GPG keys, prefer `gpg --export-secret-keys`, which you'd run yourself, over copying the folder between versions.

## Desktop settings

GNOME keeps settings in `dconf`, which you can see with `dconf dump /`, and KDE keeps them in `~/.config`. Restoring across major desktop versions can break things, so review these and reapply what you need.

## Sleep

`scripts/run-awake.sh` uses `systemd-inhibit` where it's allowed. If it isn't, it warns you and runs the command anyway. Servers usually don't sleep, but check laptops.

## Erasing

It depends on your disk and setup: reinstall the OS, or use `blkdiscard` or an encrypted disk's key wipe. These act immediately, so double-check the device name with `lsblk`. Run the final check first.
