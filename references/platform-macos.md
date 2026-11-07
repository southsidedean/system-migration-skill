# macOS

Commands here read state only, except where noted. Behavior varies by macOS version, so confirm before relying on it.

## Privacy protections

Protected folders can refuse command-line access with `Operation not permitted`, even for your own files. Common ones: Mail, Messages, Safari, Photos libraries, Contacts, Calendar, Reminders, Notes, and some browser data in `~/Library/Application Support`.

- Record blocked paths as NOT VERIFIED.
- A read of app preferences can trigger a permission dialog on screen, and if approved, it changes privacy settings. Warn the user first.
- `chmod` can also be blocked on those folders. Finder's Get Info > Sharing & Permissions may still work, so give the user those steps.
- Full Disk Access is the user's choice. Offer it, explain what it grants, and accept "no". Without it, Finder can usually still copy these folders by hand, or archive them on the source and unpack at the destination.

## Inventory

```sh
system_profiler SPHardwareDataType SPSoftwareDataType
ls /Applications; ls ~/Applications
brew leaves --installed-on-request; brew list --cask; brew tap
brew bundle dump --file=- 2>/dev/null   # prints a Brewfile; writes nothing
mas list
code --list-extensions
launchctl list | grep -v com.apple; ls ~/Library/LaunchAgents /Library/LaunchAgents /Library/LaunchDaemons
crontab -l
lpstat -p; sharing -l; pmset -g
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
tmutil destinationinfo
```

`tmutil` subcommands and `log show` can hang or need Full Disk Access. Use a timeout.

## Copying

- `/usr/bin/rsync` may be openrsync, which lacks some GNU rsync flags and doesn't support extended attributes. Check with `rsync --version`. Finder tags and other metadata may not survive. Use Homebrew's rsync if they matter, and tell the user what's lost.
- Photo libraries and some app data refuse command-line writes. Archive on the source, then have the user unpack and place them in Finder.
- `tar` may store metadata as `._` entries. These count as extra files when compared.
- Migration Assistant suits moving a whole account onto a fresh machine. Don't suggest it for a machine already in use.
- Finder can create a `.DS_Store` in a folder when a file arrives there, and it can even match the source's by hash. It doesn't mean the copy brought it, and `report` leaves these out.
- iCloud can leave "dataless" placeholders. `inventory.py` records these and doesn't read them, to avoid triggering downloads.

## Apps

- Intel-only apps need Rosetta: `softwareupdate --install-rosetta` (this installs something, so ask first).
- Homebrew disables casks that fail Gatekeeper, and a formula may still exist. Check `brew info`.
- `mas` needs an App Store sign-in, and doesn't always find apps by ID. Some App Store apps change their names over time, so match by more than the name.
- Downloaded apps may be blocked. System Settings > Privacy & Security > Open Anyway overrides a safety check, so only suggest it for files from the vendor.
- Reinstalling can raise a major version, so check whether a license still applies.

## Credentials

- `~/Library/Keychains/login.keychain-db` can be copied as a file and added using Keychain Access > File > Add Keychain. It opens with the keychain's password, which may not match the current login password.
- The folders with UUID names under `~/Library/Keychains` hold Local Items, which don't move as files. Have the user review them on the source.
- Never give a copied keychain a name ending in `login`, such as `old-login.keychain-db`. In testing on macOS 26, those wouldn't unlock with the right password, in any folder, while `old-login-2.keychain-db` worked. So a failure under such a name proves nothing. Rename the copy and test again before concluding that it's bad.
- `inventory` and `compare` skip keychains, so they can't confirm a keychain copy. Report them as not compared, and test by opening them.
- Don't assume where passwords live. Check Passwords, the keychains, and browsers with the user.
- App data encrypted with a key in the source's keychain, such as Chrome's cookies and saved passwords, won't decrypt at the destination.

## Settings and awake state

- `defaults read <domain> <key>` compares settings. Quit an app before writing to its domain. `killall Dock Finder` applies changes to those two.
- Back up with `defaults export com.apple.dock backup.plist` before changing the Dock, and note the restore command in `status.md`.
- Idle sleep can be short, even on AC. `pmset -g` shows it. Use `run-awake.sh`, which wraps `caffeinate -i`.

## Erasing

System Settings > General > Transfer or Reset > Erase All Content and Settings. The user runs it after the Phase 7 gate.
