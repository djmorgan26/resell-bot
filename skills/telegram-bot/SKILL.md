---
name: telegram-bot
description: "The single consumer of all Telegram updates. Routes photos to batch research, text to scheduled runs, and reply-format messages to the followup system. Runs as a background macOS launchd service via scripts/telegram_poll_bot.py."
---

# Telegram Bot: Message Routing & Batch Research

## What it does

A background Python script (`scripts/telegram_poll_bot.py`) watches the Telegram bot chat in real time. It is the **single consumer** of all Telegram updates — no other system should call `getUpdates` directly.

When the user sends photos (batch mode supported):

1. Each distinct caption creates a separate item in the queue
2. Bot replies with a running summary: "I have 3 item(s) queued..."
3. User can keep sending more items or add context by replying to the bot
4. User replies "go" (or "yes", "list", "do it", etc.)
5. Bot downloads all photos and spawns **one** Claude session for all items
6. Claude sees all items together, can merge duplicates, researches and prices each
7. Claude sends Telegram progress updates and a final summary

**No publishing happens here.** Items are saved to the inventory with status "ready". Publishing happens when:
- The user tells Claude Cowork to publish it, OR
- The next morning scheduled run picks it up automatically (Step 4b in morning-run.md)

## Architecture

```
User's phone → Telegram Bot API → telegram_poll_bot.py (long polling)
                                         │
                                         ├─ Photos → queued by caption
                                         │           → "go" triggers download + research
                                         │
                                         ├─ Text replies to bot → context for queued items
                                         │
                                         ├─ General text → saved to consumed_updates.json
                                         │                  → picked up by morning/followup run
                                         │
                                         └─ ONE claude -p session for ALL items
                                              │
                                              ├─ Smart grouping (merges duplicates)
                                              ├─ Identify items (stage 1-2)
                                              ├─ Research comps (WebSearch, stage 3)
                                              ├─ Price at market price (stage 4)
                                              ├─ Write listing drafts (stage 5)
                                              ├─ Update inventory (status: ready)
                                              └─ Telegram summary with next steps
```

## Message routing

The poll bot routes ALL Telegram messages:

| Message type | What happens |
|---|---|
| Photos with caption | New item queued (distinct caption = distinct item) |
| Photos without caption | Added to most recent queued item |
| "go" / "yes" / "list" / "do it" | Triggers research for ALL queued items |
| "cancel" / "stop" / "no" | Cancels all queued items |
| Text replying to bot message | Added as context to queued items |
| General text (no pending items) | Saved to `consumed_updates.json` for scheduled runs |
| General text (items pending) | Saved to `consumed_updates.json`, bot acknowledges |

All updates are saved to `notifications/consumed_updates.json` (24-hour rolling window) so that the followup skill and morning run can read messages the bot already consumed.

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

# Restart the service (after code changes)
launchctl stop com.resellbot.telegram-poll-bot
launchctl start com.resellbot.telegram-poll-bot

# Check logs
tail -f logs/poll-bot-stderr.log
```

## Telegram progress updates

Claude sends updates at these milestones:
1. After identifying items — how many distinct items, any merges
2. After pricing each item — the 3 price tiers and recommendation
3. Final summary — all listing drafts, prices, and next steps

## Pricing

Items are listed at **Market Price** by default. The strategy is to start at market and lower over time if there's no interest. See the Pricing Strategy section in CLAUDE.md.

## Logs

- Poll bot output: `logs/poll-bot-stderr.log`
- Batch research sessions: `logs/research-batch-<timestamp>.log`

Sessions expire after 30 minutes of inactivity.
