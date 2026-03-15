# resell-bot

Automated daily monitoring of eBay and Facebook Marketplace listings using Claude (Cowork). Checks for messages, offers, and sales — auto-responds to routine questions, emails you when something important happens, and sends a Telegram summary after every run.

---

## What it does

Every morning, Claude:

- Checks all active eBay and Facebook Marketplace listings
- Replies automatically to "is this available?" and basic buyer questions
- Sends you a Telegram notification if something sold, an offer came in, or a buyer asked something it can't answer
- Updates `resell_inventory.xlsx` with any changes
- Sends a Telegram message summarizing urgent items and a table of all active listings
- Stays quiet via email if nothing happened (no spam)

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
├── notifications/
│   ├── SKILL.md                  # Telegram summary skill — format and send end-of-run message
│   ├── notifier.py               # Main interface: notify(message) sends via Telegram
│   ├── telegram.py               # Raw Telegram Bot API call
│   ├── .env                      # Azure SP credentials (gitignored — copy manually)
│   └── .env.example              # Template showing required keys
├── resell_inventory.xlsx         # Your live inventory tracker (source of truth)
├── requirements.txt              # Python dependencies
├── scheduled-task-prompt.txt     # The prompt used by the Cowork scheduled task
└── README.md
```

---

## Setup on a new machine

### What you need

| Requirement | Notes |
|---|---|
| **Git** | Clone and sync the repo |
| **Python 3** | Run inventory scripts; `.venv` built from `requirements.txt` |
| **Claude Cowork** | Runs the scheduled task |
| **Chrome** | Must be logged into eBay and Facebook — Cowork uses it for marketplace checks |
| **`notifications/.env`** | Gitignored — must be copied manually from another machine |

**Not required:** Azure CLI, Telegram app (receiving only), any other CLI tools.

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/djmorgan26/resell-bot.git
cd resell-bot
```

---

### Step 2 — Set up the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Activate the venv (`source .venv/bin/activate`) whenever you run scripts manually.

---

### Step 3 — Copy the Telegram credentials

The `.env` file is gitignored and must be copied manually between machines:

```bash
cp /path/to/old-machine/notifications/.env notifications/.env
```

See `notifications/.env.example` for the required keys. This file holds the Azure Service Principal credentials used to fetch the Telegram bot token and chat ID from Key Vault.

---

### Step 4 — Log in to Chrome

Open Chrome and make sure you're logged into:
- **eBay** — seller account `davimorga-30`
- **Facebook** — the account linked to your Marketplace listings

The scheduled task uses Chrome directly — if you're logged out when it runs, the marketplace check will fail.

---

### Step 5 — Open Cowork and select the folder

1. Open the Claude desktop app
2. Start a new Cowork session
3. When prompted to select a folder, choose the `resell-bot` folder
4. Cowork will mount it as your workspace

---

### Step 6 — Set up the scheduled task

1. Open `scheduled-task-prompt.txt` from your workspace — this is the full prompt for the daily job
2. In Cowork, open the **Schedule** feature
3. Use these settings:
   - **Task name:** `daily-listing-check`
   - **Schedule:** `0 9 * * *` (every day at 9:00 AM)
   - **Prompt:** paste the full contents of `scheduled-task-prompt.txt`
4. Save the task

---

### Step 7 — Confirm Telegram is working

Test that the Telegram notifier can reach Key Vault and send a message:

```bash
source .venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, 'notifications')
from notifications.notifier import notify
notify('resell-bot test — setup complete')
"
```

If it fails, check that `notifications/.env` has valid Azure SP credentials.

**Note:** Gmail MCP is read-only — it cannot send messages. All notifications go through Telegram.

---

## Adding or removing listings

The daily check reads directly from `resell_inventory.xlsx` — no hardcoded listing data anywhere. To add a listing:

```bash
source .venv/bin/activate
python3 resell-skill/scripts/update_inventory.py resell_inventory.xlsx add \
  --name "My New Item" \
  --category "Furniture" \
  --price-mid 75 \
  --status listed \
  --marketplace "FB Marketplace" \
  --listing-url "https://www.facebook.com/marketplace/item/XXXXX"
```

Then commit and push:

```bash
git add resell_inventory.xlsx
git commit -m "add My New Item listing"
git push
```

To mark an item sold:

```bash
python3 resell-skill/scripts/update_inventory.py resell_inventory.xlsx update \
  --name "My New Item" --status sold --sold-price 65
```

---

## Creating new listings (resell-skill)

The `resell-skill/SKILL.md` is for when you want Claude to help create a new listing from scratch — researching comps, pricing, writing descriptions, organizing photos, and posting. Use it in a regular Cowork session (not the scheduled task):

> "Use the resell skill at `resell-skill/SKILL.md` to help me list this item."

The `convert_heic.py` script converts iPhone photos to JPEG before uploading:

```bash
python3 resell-skill/scripts/convert_heic.py /path/to/photos/
```

---

## Keeping inventory in sync

`resell_inventory.xlsx` is the source of truth. After Claude updates it during a daily check, commit and push:

```bash
git add resell_inventory.xlsx
git commit -m "inventory update $(date +%Y-%m-%d)"
git push
```

Pull before running on a new machine:

```bash
git pull
```

---

## Notifications

All notifications go via **Telegram**. Gmail MCP is connected as read-only only — it cannot send messages.

After every run you'll get a Telegram message with:
- **IMPORTANT** — urgent items needing your action (sales, offers, unanswerable buyer questions)
- **Active Listings table** — all current listings with platform, listed price, floor price, and any notes

The format is defined in `notifications/SKILL.md`.

---

## Troubleshooting

**Claude can't find the inventory file**
Make sure you selected the `resell-bot` folder (not a parent folder) as your Cowork workspace.

**No Telegram messages arriving**
Check that `notifications/.env` exists with valid Azure SP credentials and run the test command from Step 7.

**eBay or Facebook shows as logged out**
Make sure you're logged into both in Chrome before the scheduled run.

**No Telegram message**
Check that `notifications/.env` exists and has valid Azure SP credentials. Test with:
```bash
source .venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, 'notifications')
from notifications.notifier import notify
notify('test message')
"
```

**Inventory is out of date**
Pull the latest before running: `git pull`
