#!/usr/bin/env bash
# Notification hook: desktop toast when Claude Code is waiting on the user.
msg="$(jq -r '.message // "Claude Code needs your attention"' 2>/dev/null)"
repo="$(basename "${CLAUDE_PROJECT_DIR:-$PWD}")"
notify-send --app-name="Claude Code" --icon=dialog-information "Claude Code · $repo" "$msg" 2>/dev/null
exit 0
