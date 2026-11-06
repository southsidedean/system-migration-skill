# Linux

Commands here read state only. Distributions differ, so check which tools exist. Reading some system paths needs root, so if the user doesn't want to grant that, list them as NOT VERIFIED.

## Inventory

```sh
cat /etc/os-release; uname -a; lsblk -f; df -h
# One of these, depending on the distribution:
apt-mark showmanual
dnf repoquery --userinstalled
pacman -Qqe
flatpak list --app; snap list
pipx list; npm -g ls --depth=0; cargo install --list; go env GOPATH
code --list-extensions
systemctl --user list-unit-files --state=enabled
systemctl list-unit-files --state=enabled
crontab -l; ls /etc/cron.d
ls ~/.config/autostart; ls ~/.config/systemd/user
ip addr; nmcli connection show; lpstat -p
ss -tlnp; ufw status; firewall-cmd --state
```

Also check for changed system config: `/etc`, `/opt`, `/usr/local`, `/srv`, and database or container data under `/var/lib`. These are often overlooked, and aren't in the home folder.

## Copying

- Use `rsync -aHAX --numeric-ids` to preserve hard links, ACLs, and extended attributes when both ends support them. Omit `--numeric-ids` if user IDs differ and you want names mapped.
- Compare user and group IDs on both machines before copying. A mismatch leaves files owned by the wrong person.
- Stop databases and containers before copying their data, or use their own dump tools. Copying live files can produce a corrupt copy that still hashes consistently.
- SELinux contexts may not transfer. On Fedora or RHEL, plan for `restorecon`, with the user's approval.
- Check for sparse files and for mount points you'd cross. `inventory.py` doesn't cross mounts and records them.

## Desktop and credentials

- GNOME Keyring: `~/.local/share/keyrings`. KWallet: `~/.local/share/kwalletd`. Both may be locked to the login password.
- Also consider `~/.gnupg`, `~/.ssh`, `~/.password-store`, and cloud CLI folders.
- For GPG, prefer `gpg --export-secret-keys` run by the user, over copying the folder between versions. They'll be prompted for the passphrase.
- Desktop settings: `dconf dump /` on GNOME and `~/.config` files on KDE. Restoring these across major desktop versions can break things, so offer to review them and not restore them blindly.

## Awake state

`run-awake.sh` wraps `systemd-inhibit` when it's available. Without it, tell the user to check the machine's suspend settings. Servers usually don't sleep.

## Erasing

Depends on the disk and the plan: reinstall the OS, or use `blkdiscard` or an encrypted-disk key wipe. Give the steps for their hardware, and have them run it after the Phase 7 gate. Double-check the device name with them, because these commands act immediately.
