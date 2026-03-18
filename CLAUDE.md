# resell-bot — Project Instructions for Claude

## What this project is

An automated reselling assistant. It runs on a daily schedule to monitor eBay and Facebook Marketplace listings, handle routine buyer questions, and notify the user via Telegram when something important happens (sale, real offer, question it can't answer). A separate skill handles creating new listings from scratch. The user can also send photos of new items to the Telegram bot from their phone and listings are created automatically.

**Pricing priority** is set in `config.yaml` — check `selling.priority` to know whether to optimize for speed or price.

---

## Configuration

Read `config.yaml` at the start of any session. It contains:

```yaml
user:
  name: ""              # the user's first name — use this in notifications
selling:
  ebay_username: ""     # their eBay seller username
  priority: "speed"     # "speed" = quick sale, "price" = maximize profit
marketplaces:
  - "ebay"
  - "fb_marketplace"
```

If `config.yaml` does not exist, direct the user to run `python3 setup.py` before doing anything else.

---

## First-run check

Before starting any skill, verify the environment is configured:

1. `config.yaml` exists → read it for user settings
2. `notifications/.env` exists → Telegram credentials are present
3. `resell_inventory.xlsx` exists → inventory is set up

If any of these are missing, stop and tell the user:
> "Looks like setup isn't complete yet. Run `python3 setup.py` to get everything configured — it only takes a few minutes."

---

## Workspace layout

```
resell-bot/
├── CLAUDE.md                          ← you are here
├── config.yaml                        ← user settings (gitignored)
├── config.example.yaml                ← template for new users
├── setup.py                           ← interactive setup wizard
├── resell_inventory.xlsx              ← live inventory tracker (gitignored)
├── resell_inventory_template.xlsx     ← blank template for new users
├── requirements.txt                   ← Python deps for all scripts
├── skills/                            ← all skill docs live here
│   ├── setup/SKILL.md                 ← AI-guided first-time setup
│   ├── photo-inbox/SKILL.md           ← Telegram photo retrieval
│   ├── manage-listings/SKILL.md       ← daily listing monitoring
│   ├── create-listing/SKILL.md        ← new listing creation (photos → published)
│   ├── followup/SKILL.md              ← act on user's Telegram replies
│   ├── send-summary/SKILL.md          ← format + send Telegram summary
│   ├── instant-list/SKILL.md          ← real-time Telegram → Claude listing trigger
│   └── scheduled-runs/
│       ├── morning-run.md             ← orchestration: photo inbox + listing check
│       └── followup-run.md            ← orchestration: process user's replies
├── scripts/
│   ├── update_inventory.py            ← CLI tool for the spreadsheet
│   ├── convert_heic.py               ← converts iPhone HEIC photos → JPEG
│   ├── telegram_poll_bot.py           ← background Telegram watcher (instant research)
│   ├── install-listener.sh           ← installs poll bot as macOS service
│   └── com.resellbot.telegram-poll-bot.plist ← launchd config
├── logs/                              ← listener + Claude session logs (gitignored)
├── notifications/                     ← Telegram API + Python modules
│   ├── .env                           ← Telegram credentials (gitignored)
│   ├── .env.example                   ← template
│   ├── telegram.py                    ← raw Telegram Bot API
│   ├── telegram_reader.py             ← read incoming text messages
│   ├── photo_inbox.py                 ← read incoming photo messages
│   ├── reply_handler.py               ← match user's replies to pending actions
│   ├── notifier.py                    ← notify(message) — main interface
│   └── pending_actions.json           ← written by morning run, consumed by followup
├── photo-inbox/                       ← incoming photos from Telegram
│   └── processed.json                 ← tracks which photos have been downloaded
├── items/                             ← archived photos after listing created
└── schedule-prompts/                  ← thin pointers for Cowork scheduled tasks
    ├── morning.txt                    ← → skills/scheduled-runs/morning-run.md
    └── followup.txt                   ← → skills/scheduled-runs/followup-run.md
```

---

## Skills — when to use each

| Skill | When to use | How to invoke |
|-------|-------------|---------------|
| `skills/setup/SKILL.md` | First-time setup — walk a new user through full configuration | Read and follow the SKILL.md |
| `skills/photo-inbox/SKILL.md` | Check Telegram for new photos the user sent from their phone | Read and follow the SKILL.md |
| `skills/manage-listings/SKILL.md` | Daily monitoring — check listings, respond to buyers, send alerts | Read and follow the SKILL.md |
| `skills/create-listing/SKILL.md` | Create a new listing — photos, pricing research, description, posting | Read and follow the SKILL.md |
| `skills/followup/SKILL.md` | Act on the user's Telegram replies to pending decisions | Read and follow the SKILL.md |
| `skills/send-summary/SKILL.md` | Format and send the post-run Telegram summary | Read and follow the SKILL.md |
| `skills/instant-list/SKILL.md` | Real-time: Telegram photo → research + document in inventory | Runs via `scripts/telegram_poll_bot.py` |

### Scheduled runs

The `skills/scheduled-runs/` directory has orchestration docs that chain the skills together. Scheduled prompts in `schedule-prompts/` are thin pointers — all logic lives in the code.

| Run | Orchestration doc | Scheduled prompt |
|-----|-------------------|-----------------|
| Morning (daily) | `skills/scheduled-runs/morning-run.md` | `schedule-prompts/morning.txt` |
| Followup (1hr later) | `skills/scheduled-runs/followup-run.md` | `schedule-prompts/followup.txt` |

If running as a scheduled task, **check the photo inbox first** (photo-inbox skill), then run manage-listings. If new photos are found, hand off each item to create-listing for publishing.

---

## Python scripts

**One virtual environment for everything.** All deps live in a single root-level `requirements.txt` and `.venv`:
```bash
# First-time setup (run from repo root):
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Activate on subsequent sessions:
source .venv/bin/activate
```

### scripts/update_inventory.py
Manages `resell_inventory.xlsx`. Common commands:
```bash
# Add a new item
python3 scripts/update_inventory.py resell_inventory.xlsx add \
  --name "Item Name" --category "Category" --price-mid 75 --status listed \
  --marketplace "FB Marketplace" --listing-url "https://..."

# Mark an item as sold
python3 scripts/update_inventory.py resell_inventory.xlsx update \
  --name "Item Name" --status sold --sold-price 350

# List active items
python3 scripts/update_inventory.py resell_inventory.xlsx list --status listed
```

### scripts/convert_heic.py
Converts iPhone HEIC photos to JPEG for marketplace uploads:
```bash
python3 scripts/convert_heic.py /path/to/photos/ /path/to/output/
```

---

## Required MCPs / connectors

| MCP | Purpose | Required for |
|-----|---------|-------------|
| **Gmail MCP** | Read emails only (cannot send) | Optional — reading inbox for marketplace notifications |
| **Browser / Chrome** | Navigate eBay and Facebook Marketplace | All skills — listing checks, publishing, Telegram API |

Confirm Chrome is active before the first scheduled run. Notifications are sent via Telegram (see `notifications/` — no email MCP needed for sending).

### Fixing Chrome timeouts

If Chrome MCP tools time out (every call returns "did not respond in time"), do this in order:

1. Call `switch_browser` with `browser: "chrome"` — this reconnects the MCP to the Chrome extension.
2. Call `tabs_context_mcp` with `createIfEmpty: true` (boolean) — this creates a new tab group and returns a valid `tabId`.
3. Use that `tabId` (as a number) in all subsequent Chrome tool calls.

```
switch_browser(browser: "chrome")
tabs_context_mcp(createIfEmpty: true)   → returns tabId e.g. 73648610
navigate(url: "https://...", tabId: 73648610)
```

This resolved a full Chrome timeout loop in a scheduled run on 2026-03-15.

---

## Telegram notifications

The `notifications/` subdirectory handles all Telegram communication — sending alerts, reading the user's replies, and downloading photos.

```
notifications/
├── .env              ← Telegram credentials (gitignored)
├── .env.example      ← template — shows what keys are required
├── telegram.py       ← raw Telegram Bot API call
├── telegram_reader.py← read incoming text messages
├── photo_inbox.py    ← read incoming photo messages
├── reply_handler.py  ← match user's replies to pending actions
├── notifier.py       ← main interface: loads .env → Telegram
└── pending_actions.json ← written by morning run, consumed by followup
```

**Usage from any script in this repo:**
```python
from notifications.notifier import notify

notify("Your listing got a new offer: $380 — check it out")
```

Credentials flow: `.env` → Telegram bot token + chat ID → message sent directly via Telegram Bot API.

The `.env` is gitignored. On a new machine, run `python3 setup.py` to create it.

---

## Photo inbox — Telegram photo pipeline

The user sends photos of items to sell directly to the Telegram bot from their phone. The photo-inbox skill polls for these and downloads them automatically.

**User's workflow:** Take photos → send to Telegram bot with a caption (item name) → done.

**Claude's workflow:** Check `skills/photo-inbox/SKILL.md` → download new photos to `photo-inbox/<item-name>/` → hand off to `skills/create-listing/SKILL.md` for listing creation.

Photos are tracked in `photo-inbox/processed.json` to avoid re-downloading. After a listing is created, photos move to `items/<item-name>/`.

The Python module at `notifications/photo_inbox.py` handles parsing, grouping (albums), deduplication, and saving. In the Cowork sandbox, all Telegram API calls go through Chrome JS (same pattern as the notification sender).

---

## Behavioral rules — always enforced

These are hard limits. Never override without explicit user approval:

- **Never accept or decline an offer** — notify the user via Telegram with the offer amount and a recommendation, wait for them to decide
- **Never finalize a sale** — notify the user and let them handle shipping/fulfillment
- **Never change a listing price** — suggest it, don't do it
- **Never end or remove a listing**
- **Never share the user's personal info** (phone, address) with buyers
- **Never make pickup/meeting commitments**

Routine actions that are fine autonomously:
- Answer "is this still available?" messages
- Reply to questions covered by the listing (dimensions, condition, shipping)
- Update `resell_inventory.xlsx`

---

## Pricing strategy

**Default to Market Price** when creating a new listing. The strategy is:
1. List at the **Market Price** tier (median of comparable sold listings)
2. If no interest after 1-2 weeks, lower toward the **Quick Sale** tier
3. Never go below the Quick Sale price — that's the floor

This means `selling.priority` in `config.yaml` sets the *starting* strategy, but the general rule is: start at market, lower if needed. Never race to the bottom on day one.

---

## Active listings and pricing floors

All listing data lives in `resell_inventory.xlsx` — that is the source of truth. Read it at the start of every run.

The eBay seller username is in `config.yaml` under `selling.ebay_username`.

**Notify via:** Telegram (see `skills/send-summary/SKILL.md`)

---

## Inventory sync

After any inventory update, commit and push:
```bash
git add resell_inventory.xlsx
git commit -m "inventory update $(date +%Y-%m-%d)"
git push
```

Pull before running on a new machine:
```bash
git pull
```
