# resell-bot — Project Instructions for Claude

## What this project is

An automated reselling assistant. It runs on a daily schedule to monitor eBay and Facebook Marketplace listings, handle routine buyer questions, and notify David via Telegram when something important happens (sale, real offer, question it can't answer). A separate skill handles creating new listings from scratch. David can also send photos of new items to the Telegram bot from his phone and listings are created automatically.

David prioritizes **speed of sale over maximizing price**.

---

## Workspace layout

```
resell-bot/
├── CLAUDE.md                          ← you are here
├── resell_inventory.xlsx              ← live inventory tracker (source of truth)
├── requirements.txt                   ← Python deps for all scripts
├── skills/                            ← all skill docs live here
│   ├── photo-inbox/SKILL.md           ← Telegram photo retrieval
│   ├── manage-listings/SKILL.md       ← daily listing monitoring
│   ├── create-listing/SKILL.md        ← new listing creation (photos → published)
│   ├── followup/SKILL.md              ← act on David's Telegram replies
│   ├── send-summary/SKILL.md          ← format + send Telegram summary
│   └── scheduled-runs/
│       ├── morning-run.md             ← orchestration: photo inbox + listing check
│       └── followup-run.md            ← orchestration: process David's replies
├── scripts/
│   ├── update_inventory.py            ← CLI tool for the spreadsheet
│   └── convert_heic.py               ← converts iPhone HEIC photos → JPEG
├── notifications/                     ← Telegram API + Python modules
│   ├── .env                           ← Telegram credentials (gitignored)
│   ├── .env.example                   ← template
│   ├── telegram.py                    ← raw Telegram Bot API
│   ├── telegram_reader.py             ← read incoming text messages
│   ├── photo_inbox.py                 ← read incoming photo messages
│   ├── reply_handler.py               ← match David's replies to pending actions
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
| `skills/photo-inbox/SKILL.md` | Check Telegram for new photos David sent from his phone | Read and follow the SKILL.md |
| `skills/manage-listings/SKILL.md` | Daily monitoring — check listings, respond to buyers, send alerts | Read and follow the SKILL.md |
| `skills/create-listing/SKILL.md` | Create a new listing — photos, pricing research, description, posting | Read and follow the SKILL.md |
| `skills/followup/SKILL.md` | Act on David's Telegram replies to pending decisions | Read and follow the SKILL.md |
| `skills/send-summary/SKILL.md` | Format and send the post-run Telegram summary | Read and follow the SKILL.md |

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

The `notifications/` subdirectory handles all Telegram communication — sending alerts, reading David's replies, and downloading photos.

```
notifications/
├── .env              ← Telegram credentials (gitignored, copy manually to each machine)
├── .env.example      ← template — shows what keys are required
├── telegram.py       ← raw Telegram Bot API call
├── telegram_reader.py← read incoming text messages
├── photo_inbox.py    ← read incoming photo messages
├── reply_handler.py  ← match David's replies to pending actions
├── notifier.py       ← main interface: loads .env → Telegram
└── pending_actions.json ← written by morning run, consumed by followup
```

**Setup on a new machine:**
```bash
# From the repo root:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Then copy your .env into notifications/
cp notifications/.env.example notifications/.env
# Fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

**Usage from any script in this repo:**
```python
from notifications.notifier import notify

notify("PS5 listing got a new offer: $380 — check it out")
```

Credentials flow: `.env` → Telegram bot token + chat ID → message sent directly via Telegram Bot API.

The `.env` is gitignored and must be copied manually between machines.

---

## Photo inbox — Telegram photo pipeline

David sends photos of items to sell directly to the Telegram bot from his iPhone. The photo-inbox skill polls for these and downloads them automatically.

**David's workflow:** Take photos → send to Telegram bot with a caption (item name) → done.

**Claude's workflow:** Check `skills/photo-inbox/SKILL.md` → download new photos to `photo-inbox/<item-name>/` → hand off to `skills/create-listing/SKILL.md` for listing creation.

Photos are tracked in `photo-inbox/processed.json` to avoid re-downloading. After a listing is created, photos move to `items/<item-name>/`.

The Python module at `notifications/photo_inbox.py` handles parsing, grouping (albums), deduplication, and saving. In the Cowork sandbox, all Telegram API calls go through Chrome JS (same pattern as the notification sender).

---

## Behavioral rules — always enforced

These are hard limits. Never override without explicit user approval:

- **Never accept or decline an offer** — notify David via Telegram with the offer amount and a recommendation, wait for him to decide
- **Never finalize a sale** — notify David and let him handle shipping/fulfillment
- **Never change a listing price** — suggest it, don't do it
- **Never end or remove a listing**
- **Never share David's personal info** (phone, address) with buyers
- **Never make pickup/meeting commitments**

Routine actions that are fine autonomously:
- Answer "is this still available?" messages
- Reply to questions covered by the listing (dimensions, condition, shipping)
- Update `resell_inventory.xlsx`

---

## Active listings and pricing floors

All listing data lives in `resell_inventory.xlsx` — that is the source of truth. Read it at the start of every run.

**Seller account:** `davimorga-30` on eBay

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
