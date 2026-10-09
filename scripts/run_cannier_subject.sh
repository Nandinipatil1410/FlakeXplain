#!/usr/bin/env bash
set -euo pipefail

# Keep the same launcher for baseline-only and full detection jobs.
args=("$SUBJECT" --work-dir "$FLAKEXPLAIN_WORK")
case "$1" in
  baseline-only) args+=(--baseline-only) ;;
  full) args+=(--reverse-rounds 1) ;;
  *) echo "Unknown experiment mode: $1" >&2; exit 2 ;;
esac

if [ "$SUBJECT" = salt ]; then
  # SSH login shells reset PATH; use setup-python's explicit interpreter output.
  python="${FLAKEXPLAIN_PYTHON:?Salt requires the setup-python interpreter path}"
  "$python" -c 'import sys; assert sys.version_info[:3] == (3, 8, 18), sys.version'
  # SSH supplies both a controlling terminal and a real utmp login record.
  # Quote each argument independently for the remote login shell.
  printf -v command 'cd %q && exec env HOME=/home/cannier USER=cannier LOGNAME=cannier PATH=%q %q %q' \
    "$GITHUB_WORKSPACE" "$(dirname "$python"):$PATH" "$python" "$GITHUB_WORKSPACE/scripts/run_salt_session.py"
  printf -v arguments ' %q' "${args[@]}"
  exec ssh -tt -p 2222 -i /home/cannier/.ssh/salt_ci \
    -o BatchMode=yes -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile=/home/cannier/.ssh/salt_known_hosts \
    cannier@127.0.0.1 "$command$arguments"
fi

exec runuser -u cannier -- env HOME=/home/cannier USER=cannier LOGNAME=cannier \
  python run_all.py "${args[@]}"
