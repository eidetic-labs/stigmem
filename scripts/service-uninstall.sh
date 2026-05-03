#!/usr/bin/env bash
# Stops and unregisters the stigmem LaunchAgent. Does not delete the database.
set -euo pipefail

PLIST_LABEL="com.eidetic-labs.stigmem"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
GUI_DOMAIN="gui/$(id -u)"

if launchctl print "${GUI_DOMAIN}/${PLIST_LABEL}" &>/dev/null; then
  launchctl bootout "${GUI_DOMAIN}" "$PLIST_PATH"
  echo "stigmem service stopped and unregistered."
else
  echo "stigmem service is not currently registered."
fi

if [[ -f "$PLIST_PATH" ]]; then
  rm "$PLIST_PATH"
  echo "Removed plist: $PLIST_PATH"
fi
