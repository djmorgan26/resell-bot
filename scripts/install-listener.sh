#!/bin/bash
# Install the Telegram poll bot as a macOS background service (launchd).
#
# This makes the poll bot start automatically on login and restart on crash.
# The service watches Telegram for photos and triggers Claude to research items.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$REPO_ROOT/scripts/com.resellbot.telegram-poll-bot.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.resellbot.telegram-poll-bot.plist"
OLD_PLIST="$HOME/Library/LaunchAgents/com.resellbot.telegram-listener.plist"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python3"

echo "=== Resell Bot Telegram Poll Bot Installer ==="
echo ""

# Check prerequisites
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Python venv not found at $VENV_PYTHON"
    echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

if [ ! -f "$REPO_ROOT/notifications/.env" ]; then
    echo "ERROR: Telegram credentials not configured."
    echo "Run: python3 setup.py"
    exit 1
fi

if ! command -v claude &> /dev/null; then
    echo "ERROR: claude CLI not found in PATH."
    echo "Install Claude Code: https://docs.anthropic.com/en/docs/claude-code"
    exit 1
fi

# Create logs directory
mkdir -p "$REPO_ROOT/logs"

# Stop old listener if running (renamed from telegram-listener)
if launchctl list 2>/dev/null | grep -q "com.resellbot.telegram-listener"; then
    echo "Stopping old telegram-listener service..."
    launchctl unload "$OLD_PLIST" 2>/dev/null || true
    rm -f "$OLD_PLIST"
fi

# Stop existing poll bot if running
if launchctl list 2>/dev/null | grep -q "com.resellbot.telegram-poll-bot"; then
    echo "Stopping existing poll bot..."
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

# Update paths in plist to match this machine
sed "s|/Users/morganlynn/repos/resell-bot|$REPO_ROOT|g" "$PLIST_SRC" > "$PLIST_DST"

# Load the service
launchctl load "$PLIST_DST"

echo ""
echo "Poll bot installed and started!"
echo ""
echo "  Status:  launchctl list | grep resellbot"
echo "  Logs:    tail -f $REPO_ROOT/logs/poll-bot-stdout.log"
echo "  Stop:    launchctl unload $PLIST_DST"
echo "  Restart: launchctl unload $PLIST_DST && launchctl load $PLIST_DST"
echo ""
echo "Send a photo to your Telegram bot to test it!"
