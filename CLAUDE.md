# resell-bot — Project Instructions for Claude

## What this project is

An automated reselling assistant. It runs on a daily schedule to monitor eBay and Facebook Marketplace listings, handle routine buyer questions, and email David when something important happens (sale, real offer, question it can't answer). A separate skill handles creating new listings from scratch.

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
└── resell-skill/
    ├── SKILL.md                       ← new listing creation skill
    └── scripts/
        ├── update_inventory.py        ← CLI tool for the spreadsheet
        └── convert_heic.py            ← converts iPhone HEIC photos → JPEG
```

---

## Skills — when to use each

| Skill | When to use | How to invoke |
|-------|-------------|---------------|
| `manage-listings-skill/SKILL.md` | Daily monitoring run — check listings, respond to buyers, send alerts | Read and follow the SKILL.md |
| `resell-skill/SKILL.md` | Creating a new listing — photos, pricing research, description, posting | Read and follow the SKILL.md |

If running as a scheduled task, use the manage-listings skill. Use `scheduled-task-prompt.txt` as the task prompt — it contains the active listings and pricing floors.

---

## Python scripts

**Install dependencies first** (see `requirements.txt`):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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
| **Gmail MCP** | Send email alerts to davidjmorgan26@gmail.com | Daily monitoring (manage-listings skill) |
| **Browser / Chrome** | Navigate eBay and Facebook Marketplace | Both skills — listing checks and publishing |

Confirm both are active before the first scheduled run. Test Gmail with: "Send me a test email using Gmail MCP."

---

## Behavioral rules — always enforced

These are hard limits. Never override without explicit user approval:

- **Never accept or decline an offer** — email David with the offer amount and a recommendation, wait for him to decide
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

**Notify emails:** davidjmorgan26@gmail.com and lynnlmorgan64@gmail.com

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
