# resell-bot

Automated daily monitoring of eBay and Facebook Marketplace listings using Claude (Cowork). Checks for messages, offers, and sales — auto-responds to routine questions and emails you when something important happens.

---

## What it does

Every morning at 9 AM, Claude:

- Checks all your active eBay and Facebook Marketplace listings
- Replies automatically to "is this available?" and basic buyer questions
- Emails you at davidjmorgan26@gmail.com and lynnlmorgan64@gmail.comif something sold, an offer came in, or a buyer asked something it can't answer
- Updates `resell_inventory.xlsx` with any changes
- Stays quiet if nothing happened (no spam)

It never accepts offers, finalizes sales, or makes commitments without you.

---

## Repo contents

```
resell-bot/
├── CLAUDE.md                     # Project instructions loaded automatically by Claude
├── manage-listings-skill/
│   └── SKILL.md                  # Daily monitoring: check listings, respond to buyers, email alerts
├── resell-skill/
│   ├── SKILL.md                  # Creating new listings: research, pricing, photos, posting
│   └── scripts/
│       ├── update_inventory.py   # CLI tool for managing the inventory spreadsheet
│       └── convert_heic.py       # Converts iPhone HEIC photos to JPEG for listings
├── resell_inventory.xlsx         # Your live inventory tracker
├── requirements.txt              # Python dependencies
├── scheduled-task-prompt.txt     # The prompt pasted into the scheduled task
└── README.md
```

---

## Setup on a new computer

### Step 1 — Prerequisites

You need:

- **Cowork** installed (the Claude desktop app with Cowork mode)
- **Gmail MCP** connected in Cowork (for email notifications)
- **Chrome** open and logged into your eBay and Facebook accounts

### Step 2 — Clone the repo

```bash
git clone https://github.com/djmorgan26/resell-bot.git
cd resell-bot
```

### Step 3 — Set up the Python environment

Create a virtual environment and install all dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This installs:
- `openpyxl` — inventory spreadsheet management
- `Pillow` + `pillow-heif` — HEIC photo conversion

Activate the venv (`source .venv/bin/activate`) whenever you run the scripts manually.

### Step 4 — Open Cowork and select the folder

1. Open the Claude desktop app
2. Start a new Cowork session
3. When prompted to select a folder, choose the `resell-bot` folder you just cloned
4. Cowork will mount that folder as your workspace

### Step 5 — Set up the scheduled task

1. In Cowork, open `scheduled-task-prompt.txt` from your workspace — this is the full prompt for the daily job
2. Open the **Schedule** feature in Cowork (or ask Claude: "Set up a scheduled task for me")
3. Use these settings:
   - **Task name:** `daily-listing-check`
   - **Schedule:** `0 9 * * *` (every day at 9:00 AM)
   - **Prompt:** paste the full contents of `scheduled-task-prompt.txt`
4. Save the task

That's it — Claude will run the check automatically every morning.

### Step 6 — Confirm Gmail MCP is connected

The scheduled task uses your Gmail to send you notifications. Make sure the Gmail connector is active in Cowork before the first run. You can test it by asking Claude: "Send me a test email using Gmail MCP."

---

## Creating new listings (resell-skill)

The `resell-skill/SKILL.md` is for when you want Claude to help create a new listing from scratch — researching comps, pricing, writing descriptions, organizing photos, and posting. Use it in a regular Cowork session (not the scheduled task) by asking Claude: "Use the resell skill at `resell-skill/SKILL.md` to help me list this item."

The `convert_heic.py` script converts iPhone photos to JPEG before uploading:

```bash
python3 resell-skill/scripts/convert_heic.py /path/to/photos/
```

---

## Keeping inventory in sync

`resell_inventory.xlsx` is the source of truth for your listings. After Claude updates it during a daily check, commit and push the changes so it stays current across machines:

```bash
git add resell_inventory.xlsx
git commit -m "inventory update $(date +%Y-%m-%d)"
git push
```

If you add new listings on one machine, pull before running on another:

```bash
git pull
```

---

## Adding or removing listings

To add a listing to the daily check, edit two places:

**1. `scheduled-task-prompt.txt`** — add a line under `ACTIVE LISTINGS TO CHECK`:

```
- Facebook Marketplace: My New Item — https://www.facebook.com/marketplace/item/XXXXX ($75)
```

**2. `resell_inventory.xlsx`** — add the item using the update script:

```bash
python3 resell-skill/scripts/update_inventory.py resell_inventory.xlsx add \
  --name "My New Item" \
  --category "Furniture" \
  --price-mid 75 \
  --status listed \
  --marketplace "FB Marketplace" \
  --listing-url "https://www.facebook.com/marketplace/item/XXXXX"
```

Then commit both files and push.

---

## Email notifications

You'll get an email at `davidjmorgan26@gmail.com` when:

| Event                      | Subject line                           |
| -------------------------- | -------------------------------------- |
| Item sold                  | `Item Sold — [Item Name] for $[Price]` |
| Offer received             | `Offer on [Item Name]: $[Amount]`      |
| Buyer question (needs you) | `Listing Update — [Date]`              |

No email = nothing happened today.

---

## Pricing floors (for offer evaluation)

Claude uses these floors when deciding whether to recommend accepting an offer:

| Item                     | Listed | Floor |
| ------------------------ | ------ | ----- |
| Singer Featherweight 221 | $380   | $300  |
| Tarkay Lithograph        | $350   | $150  |
| Home Theater Bundle      | $900   | $700  |
| Asian Shadow Box         | $55    | $40   |
| Tapestry Armchair        | $125   | $75   |
| Pushback Recliner        | $150   | $100  |

To update a floor price, edit the `PRICING FLOORS` section in `scheduled-task-prompt.txt`.

---

## Troubleshooting

**Claude can't find the inventory file**
Make sure you selected the `resell-bot` folder (not a parent folder) as your Cowork workspace.

**No emails arriving**
Check that the Gmail MCP connector is active in your Cowork session settings.

**eBay or Facebook shows as logged out**
The scheduled task runs in Chrome on your computer. Make sure you're logged in to both in Chrome before the 9 AM run.

**Inventory is out of date**
Pull the latest from GitHub before running: `git pull`
