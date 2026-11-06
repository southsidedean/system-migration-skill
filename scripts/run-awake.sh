#!/bin/sh
# Keep this machine from idle-sleeping for the life of one command, then stop.
#   run-awake.sh <command> [args...]
# Exits with the command's exit status. Leaves nothing running afterward.
[ "$#" -gt 0 ] || { echo "usage: run-awake.sh <command> [args...]" >&2; exit 64; }

if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -i "$@"
elif command -v systemd-inhibit >/dev/null 2>&1 &&
  systemd-inhibit --what=idle:sleep --who=system-migration --why="migration job" true >/dev/null 2>&1; then
  exec systemd-inhibit --what=idle:sleep --who=system-migration --why="migration job" "$@"
else
  # A missing or refused inhibitor must not stop the job, so warn and carry on.
  echo "run-awake.sh: no usable keep-awake tool; running without one, so check sleep settings" >&2
  exec "$@"
fi
