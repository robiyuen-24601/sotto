#!/usr/bin/env bash
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_DST="$HOME/Library/LaunchAgents/com.robertyuen.sotto.plist"
LABEL="com.robertyuen.sotto"

case "${1:-install}" in
  install)
    sed -e "s|__PYTHON__|$PROJECT/.venv/bin/python|" \
        -e "s|__PROJECT__|$PROJECT|" \
        -e "s|__HOME__|$HOME|" \
        "$PROJECT/scripts/$LABEL.plist.template" > "$PLIST_DST"
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
    echo "installed and started: $LABEL"
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST_DST"
    echo "uninstalled: $LABEL"
    ;;
esac
