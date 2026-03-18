---
name: instant-list
description: "Real-time Telegram poll bot that triggers Claude to research and document items as soon as the user sends photos. Runs as a background macOS launchd service."
---

# Instant List: Telegram-Triggered Research Workflow

## What it does

A background Python script (`scripts/telegram_poll_bot.py`) watches the Telegram bot chat in real time. When the user sends photos of an item:

1. Bot replies: "I see [item]! Send more photos/details, or reply 'go'."
2. User can send additional photos or text context
3. User replies "go" (or "yes", "list", "do it", etc.)
4. Bot downloads photos to `photo-inbox/<item>/`
5. Bot spawns a `claude -p` session that runs stages 1-5 of `skills/create-listing/SKILL.md`
6. Claude researches comps, prices the item, writes a listing draft, and updates the inventory
7. Claude sends Telegram progress updates and a final summary with next steps

**No publishing happens here.** The item is saved to the inventory with status "ready". Publishing happens when:
- The user tells Claude Cowork to publish it, OR
- The next morning scheduled run picks it up automatically (Step 4b in morning-run.md)

## Architecture

```
User's phone → Telegram Bot API → telegram_poll_bot.py (long polling)
                                         │
                                         ├─ Photos → photo-inbox/<item>/ → items/<item>/
                                         │
                                         └─ claude -p → research workflow (no Chrome)
                                                           │
                                                           ├─ Identify item (stage 1-2)
                                                           ├─ Research comps (WebSearch, stage 3)
                                                           ├─ Price item at market price (stage 4)
                                                           ├─ Write listing draft (stage 5)
                                                           ├─ Update inventory (status: ready)
                                                           └─ Telegram summary with next steps
```

## Requirements

- `notifications/.env` configured with Telegram credentials
- Python venv activated with deps installed
- Claude CLI installed and in PATH

No Chrome or browser extension needed — research uses WebSearch.

## Commands

```bash
# Test — check once and exit
python3 scripts/telegram_poll_bot.py --once

# Run in foreground (for debugging)
python3 scripts/telegram_poll_bot.py

# Install as a background service (starts on boot)
./scripts/install-listener.sh

# Stop the service
launchctl unload ~/Library/LaunchAgents/com.resellbot.telegram-poll-bot.plist

# Check logs
tail -f logs/poll-bot-stderr.log
```

## User commands (via Telegram)

| Message | Action |
|---------|--------|
| Send photo(s) with caption | Starts a new research session |
| Send more photos | Adds to current session |
| Any text (while session active) | Added as context/notes |
| "go" / "yes" / "list" / "do it" | Triggers research |
| "cancel" / "no" / "stop" | Cancels the current session |

Sessions expire after 30 minutes of inactivity.

## Telegram progress updates

Claude sends updates at these milestones:
1. After identifying the item — what it thinks the item is
2. After pricing — the 3 price tiers and recommendation
3. Final summary — listing draft, price, and next steps

## Pricing

Items are listed at **Market Price** by default. The strategy is to start at market and lower over time if there's no interest. See the Pricing Strategy section in CLAUDE.md.

## Logs

- Poll bot output: `logs/poll-bot-stderr.log`
- Per-item research sessions: `logs/research-<item-name>.log`
