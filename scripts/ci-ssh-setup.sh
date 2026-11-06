#!/bin/sh
# CI only: let this throwaway runner SSH to itself, so remote copies run over a real connection.
# Don't run this on your own machine: it changes SSH settings and starts the SSH server.
set -eu
[ "${CI:-}" = true ] || { echo "This is for CI runners only." >&2; exit 2; }

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
ssh-keygen -q -t ed25519 -N "" -f "$HOME/.ssh/id_ci" </dev/null
cat "$HOME/.ssh/id_ci.pub" >>"$HOME/.ssh/authorized_keys"
chmod 600 "$HOME/.ssh/authorized_keys"
printf 'Host 127.0.0.1\n  IdentityFile ~/.ssh/id_ci\n  StrictHostKeyChecking accept-new\n' >>"$HOME/.ssh/config"
chmod 600 "$HOME/.ssh/config"

case "$(uname -s)" in
Darwin) sudo launchctl load -w /System/Library/LaunchDaemons/ssh.plist || true ;;
*) sudo systemctl start ssh || sudo service ssh start ;;
esac
chmod go-w "$HOME"

tries=0
until ssh -n -o BatchMode=yes -o ConnectTimeout=5 "$(id -un)@127.0.0.1" true; do
  tries=$((tries + 1))
  [ "$tries" -lt 10 ] || { echo "SSH to this runner never came up." >&2; exit 1; }
  sleep 2
done
echo "SSH to this runner works."
