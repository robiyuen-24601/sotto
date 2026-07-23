#!/usr/bin/env bash
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_DST="$HOME/Library/LaunchAgents/com.robertyuen.sotto.plist"
LABEL="com.robertyuen.sotto"

case "${1:-install}" in
  install)
    mkdir -p "$HOME/Library/LaunchAgents"
    # sed assumes $PROJECT and $HOME contain no sed metacharacters (&, \, |)
    sed -e "s|__PYTHON__|$PROJECT/.venv/bin/python|" \
        -e "s|__PROJECT__|$PROJECT|" \
        -e "s|__HOME__|$HOME|" \
        "$PROJECT/scripts/$LABEL.plist.template" > "$PLIST_DST"
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
    echo "installed and started: $LABEL"
    echo "check: launchctl print gui/$(id -u)/$LABEL"
    echo "note: grant Microphone + Accessibility to $PROJECT/.venv/bin/python, then: launchctl kickstart -k gui/$(id -u)/$LABEL"
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST_DST"
    echo "uninstalled: $LABEL"
    ;;
  *)
    echo "usage: $0 [install|uninstall]" >&2
    exit 2
    ;;
esac
