# resell-bot — Project Instructions for Claude

## What this project is

An automated reselling assistant. It runs on a daily schedule to monitor eBay and Facebook Marketplace listings, handle routine buyer questions, and notify David via Telegram when something important happens (sale, real offer, question it can't answer). A separate skill handles creating new listings from scratch.

David prioritizes **speed of sale over maximizing price**.

---

## Workspace layout

```
resell-bot/
├── CLAUDE.md                          ← you are here
├── scheduled-task-prompt.txt          ← paste this into the daily scheduled task
├── resell_inventory.xlsx              ← live inventory tracker (source of truth)
├── manage-listings-skill/
│   └── SKILL.md                       ← daily monitoring skill
├── resell-skill/
│   ├── SKILL.md                       ← new listing creation skill
│   └── scripts/
│       ├── update_inventory.py        ← CLI tool for the spreadsheet
│       └── convert_heic.py            ← converts iPhone HEIC photos → JPEG
└── notifications/
    ├── .env                           ← Azure SP credentials (gitignored, copy manually)
    ├── .env.example                   ← template
    ├── telegram.py                    ← raw Telegram API
    └── notifier.py                    ← notify(message) — main interface
```

---

## Skills — when to use each

| Skill | When to use | How to invoke |
|-------|-------------|---------------|
| `manage-listings-skill/SKILL.md` | Daily monitoring run — check listings, respond to buyers, send alerts | Read and follow the SKILL.md |
| `resell-skill/SKILL.md` | Creating a new listing — photos, pricing research, description, posting | Read and follow the SKILL.md |

If running as a scheduled task, use the manage-listings skill. Use `scheduled-task-prompt.txt` as the task prompt — it orchestrates the full workflow including the Telegram summary at the end.

---

## Python scripts

**One virtual environment for everything.** All deps for all scripts (inventory, photos, notifications) live in a single root-level `requirements.txt` and `.venv`:
```bash
# First-time setup (run from repo root):
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Activate on subsequent sessions:
source .venv/bin/activate
```

### update_inventory.py
Manages `resell_inventory.xlsx`. Common commands:
```bash
# Add a new item
python3 resell-skill/scripts/update_inventory.py resell_inventory.xlsx add \
  --name "Item Name" --category "Category" --price-mid 75 --status listed \
  --marketplace "FB Marketplace" --listing-url "https://..."

# Mark an item as sold
python3 resell-skill/scripts/update_inventory.py resell_inventory.xlsx update \
  --name "Item Name" --status sold --sold-price 350

# List active items
python3 resell-skill/scripts/update_inventory.py resell_inventory.xlsx list --status listed
```

### convert_heic.py
Converts iPhone HEIC photos to JPEG for marketplace uploads:
```bash
python3 resell-skill/scripts/convert_heic.py /path/to/photos/ /path/to/output/
```

---

## Required MCPs / connectors

| MCP | Purpose | Required for |
|-----|---------|-------------|
| **Gmail MCP** | Read emails only (cannot send) | Optional — reading inbox for marketplace notifications |
| **Browser / Chrome** | Navigate eBay and Facebook Marketplace | Both skills — listing checks and publishing |

Confirm Chrome is active before the first scheduled run. Notifications are sent via Telegram (see `notifications/` — no email MCP needed for sending).

---

## Telegram notifications

The `notifications/` subdirectory is a self-contained service for sending Telegram messages — primarily for listing event alerts (new offers, sales, questions).

```
notifications/
├── .env              ← Azure SP credentials (gitignored, must be copied manually to each machine)
├── .env.example      ← template — shows what keys are required
├── telegram.py       ← raw Telegram Bot API call
└── notifier.py       ← main interface: loads .env → Key Vault → Telegram
```

**Setup on a new machine:**
```bash
# From the repo root:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Then copy your .env into notifications/
cp notifications/.env.example notifications/.env
# Fill in the Azure credentials
```

**Usage from any script in this repo:**
```python
from notifications.notifier import notify

notify("PS5 listing got a new offer: $380 — check it out")
```

Credentials flow: `.env` → Azure Service Principal → Key Vault → Telegram bot token + chat ID → message sent.

The `.env` is gitignored and must be copied manually between machines (contains the Azure SP secret).

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

See `scheduled-task-prompt.txt` for the current active listing URLs and pricing floors. Update that file when listings are added, removed, or prices change.

**Seller account:** `davimorga-30` on eBay

**Notify via:** Telegram (see `notifications/SKILL.md`)

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
