# resell-bot

An AI-assisted reselling tool that helps you sell personal items on eBay and Facebook Marketplace. Give it photos of an item, and it researches pricing, writes the listing description, and publishes it via your browser. It can also monitor your active listings, reply to buyer questions, and flag offers for your review.

You stay in control — the bot never accepts offers, finalizes sales, or makes commitments without your explicit approval.

---

## What it does

When you want to sell something:

- Give Claude photos (upload them, or point to a folder on your machine)
- Claude identifies the item, researches comparable sold listings, and recommends pricing
- Claude writes the listing title and description, then publishes via Chrome
- Your inventory spreadsheet is updated automatically

When you want to check on listings:

- Ask Claude to check your listings
- Claude visits each active listing on eBay/FB, checks for messages, offers, and sales
- Routine buyer questions are answered automatically; offers and decisions come to you

---

## Repo contents

```
resell-bot/
├── CLAUDE.md                          # Project instructions loaded automatically by Claude
├── config.yaml                        # Your settings (gitignored — created by setup.py)
├── config.example.yaml                # Template showing what config.yaml should contain
├── user-preferences.yaml              # Your selling preferences (gitignored — created by setup.py)
├── setup.py                           # Interactive setup wizard — run this first
├── resell_inventory.xlsx              # Your live inventory (gitignored — created by setup.py)
├── resell_inventory_template.xlsx     # Blank inventory template
├── requirements.txt                   # Python dependencies
├── skills/                            # Skill docs — Claude reads and follows these
│   ├── setup/SKILL.md                 # AI-guided first-time setup
│   ├── organize-photos/SKILL.md       # Photo intake, naming, dedup, cleanup
│   ├── create-listing/SKILL.md        # Create a new listing from photos
│   ├── manage-listings/SKILL.md       # Check listings, handle buyer messages
│   └── review-issues/SKILL.md         # Review and fix skill issues
├── scripts/
│   ├── update_inventory.py            # CLI tool for the inventory spreadsheet
│   └── convert_heic.py               # Convert iPhone HEIC photos to JPEG
├── logs/issues/                       # Per-skill issue logs (gitignored)
├── photo-inbox/                       # Staging area for incoming photos
└── items/                             # Archived photos after listing created
```

---

## Getting started

### What you need

| Requirement | Notes |
|---|---|
| **Git** | Clone and sync the repo |
| **Python 3.8+** | Run scripts and the setup wizard |
| **Claude (Cowork)** | Runs the skills |
| **Chrome** | Must be logged into eBay and Facebook — Claude uses it for marketplace actions |

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/djmorgan26/resell-bot.git
cd resell-bot
```

### Step 2 — Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3 — Configure resell-bot

```bash
python3 setup.py
```

This creates `config.yaml`, `user-preferences.yaml`, and `resell_inventory.xlsx`. Takes about 2 minutes.

### Step 4 — Log in to Chrome

Open Chrome and log in to eBay and Facebook. Claude uses Chrome directly for marketplace actions.

### Step 5 — Open Cowork and select this folder

1. Open the Claude desktop app
2. Start a new Cowork session
3. Select the `resell-bot` folder as your workspace

For a guided setup experience, tell Claude:
> "Follow the setup skill at `skills/setup/SKILL.md`"

---

## Adding a listing manually

```bash
source .venv/bin/activate
python3 scripts/update_inventory.py resell_inventory.xlsx add \
  --name "My Item" --category "Electronics" --price-mid 75 \
  --status listed --marketplace "FB Marketplace" \
  --listing-url "https://www.facebook.com/marketplace/item/XXXXX"
```

## Marking an item sold

```bash
python3 scripts/update_inventory.py resell_inventory.xlsx update \
  --name "My Item" --status sold --sold-price 65
```

---

## Troubleshooting

**"Looks like setup isn't complete yet"**
Run `python3 setup.py` — it will walk you through what's missing.

**eBay or Facebook shows as logged out**
Log in to both in Chrome before asking Claude to check listings.

**Chrome times out**
Follow the Chrome timeout fix in `CLAUDE.md` — it's a two-step reconnect procedure.

**Inventory is out of date on a second machine**
Run `git pull` before starting any session.
