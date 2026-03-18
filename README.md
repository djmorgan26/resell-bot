# resell-bot

An automated reselling assistant that runs on a daily schedule. It monitors your eBay and Facebook Marketplace listings, handles routine buyer questions automatically, and sends you a Telegram notification when something important needs your attention — a sale, a real offer, or a question it can't answer.

You never accept offers, finalize sales, or make commitments from your phone. The bot handles the busywork; you handle the decisions.

**New here?** Start with setup below. Already set up? See the **[User Guide](USER-GUIDE.md)** for how to use Telegram, Cowork, and Claude Code day-to-day.

---

## What it does

Every morning, Claude:

- Checks all your active eBay and Facebook Marketplace listings
- Replies automatically to "is this available?" and basic buyer questions
- Sends a Telegram notification for anything that needs your attention (sale, offer, complex question)
- Updates `resell_inventory.xlsx` with any changes
- Sends a Telegram summary of all active listings and any urgent items

You can also send photos of new items to the Telegram bot from your phone — the bot will research pricing, write the description, and create the listing for you.

---

## Repo contents

```
resell-bot/
├── CLAUDE.md                          # Project instructions loaded automatically by Claude
├── config.yaml                        # Your settings (gitignored — created by setup.py)
├── config.example.yaml                # Template showing what config.yaml should contain
├── setup.py                           # Interactive setup wizard — run this first
├── resell_inventory.xlsx              # Your live inventory (gitignored — created by setup.py)
├── resell_inventory_template.xlsx     # Blank inventory template
├── requirements.txt                   # Python dependencies
├── skills/                            # Skill docs — Claude reads and follows these
│   ├── setup/SKILL.md                 # AI-guided first-time setup
│   ├── photo-inbox/SKILL.md           # Check Telegram for photos you sent
│   ├── manage-listings/SKILL.md       # Daily listing monitoring
│   ├── create-listing/SKILL.md        # Create a new listing from photos
│   ├── followup/SKILL.md              # Act on your Telegram replies
│   ├── send-summary/SKILL.md          # Format and send the Telegram summary
│   └── scheduled-runs/
│       ├── morning-run.md             # Daily run orchestration
│       └── followup-run.md            # Follow-up run orchestration
├── scripts/
│   ├── update_inventory.py            # CLI tool for the inventory spreadsheet
│   └── convert_heic.py               # Convert iPhone HEIC photos to JPEG
├── notifications/                     # Telegram API modules
│   ├── .env                           # Your credentials (gitignored)
│   ├── .env.example                   # Template
│   └── ...
└── schedule-prompts/                  # Prompts for Cowork scheduled tasks
    ├── morning.txt
    └── followup.txt
```

---

## Getting started

### What you need

| Requirement | Notes |
|---|---|
| **Git** | Clone and sync the repo |
| **Python 3.8+** | Run scripts and the setup wizard |
| **Claude (Cowork)** | Runs the scheduled tasks |
| **Chrome** | Must be logged into eBay and Facebook — Claude uses it for marketplace checks |
| **Telegram** | Where you receive notifications and send replies |

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/djmorgan26/resell-bot.git
cd resell-bot
```

---

### Step 2 — Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Step 3 — Configure resell-bot

Pick whichever approach works best for you:

**Option A — Terminal wizard** (fastest)
```bash
python3 setup.py
```
Asks you questions and handles everything automatically. Takes about 5 minutes.

**Option B — AI-guided setup** (if you prefer a conversational walkthrough)
Open `setup-with-ai.md` and paste it into any AI assistant (Claude, ChatGPT, Gemini, etc.). The AI will walk you through each step one at a time.

Either way, you'll end up with:
- `config.yaml` — your personal settings
- `notifications/.env` — your Telegram bot credentials
- `resell_inventory.xlsx` — your inventory spreadsheet
- A verified Telegram connection

---

### Step 4 — Log in to Chrome

Open Chrome and make sure you're logged into:
- **eBay** — your seller account
- **Facebook** — the account linked to your Marketplace listings

Claude uses Chrome directly for marketplace checks. If you're logged out when it runs, the check will fail.

---

### Step 5 — Open Cowork and select this folder

1. Open the Claude desktop app
2. Start a new Cowork session
3. When prompted to select a folder, choose the `resell-bot` folder
4. Cowork will mount it as your workspace

For a fully guided setup experience (including scheduling), tell Claude:
> "Follow the setup skill at `skills/setup/SKILL.md`"

---

### Step 6 — Set up the scheduled tasks

Two scheduled tasks power the daily automation:

| Task | Schedule | Prompt file |
|------|----------|-------------|
| Morning run | Daily at 9:00 AM | `schedule-prompts/morning.txt` |
| Follow-up run | Daily at 10:00 AM | `schedule-prompts/followup.txt` |

In Cowork, open the **Schedule** feature, create each task, and paste the contents of the prompt file.

---

## Adding a listing manually

```bash
source .venv/bin/activate
python3 scripts/update_inventory.py resell_inventory.xlsx add \
  --name "My Item" --category "Electronics" --price-mid 75 \
  --status listed --marketplace "FB Marketplace" \
  --listing-url "https://www.facebook.com/marketplace/item/XXXXX"
```

Then sync:
```bash
git add resell_inventory.xlsx
git commit -m "add My Item listing"
git push
```

## Marking an item sold

```bash
python3 scripts/update_inventory.py resell_inventory.xlsx update \
  --name "My Item" --status sold --sold-price 65
git add resell_inventory.xlsx && git commit -m "inventory update $(date +%Y-%m-%d)" && git push
```

---

## Creating new listings (photos → published)

Send photos of items to your Telegram bot from your phone — each with a caption naming the item. You can send multiple items at once (batch mode). When you're done, reply "go" and the bot researches, prices, and drafts listings for all of them in a single session.

See the **[User Guide](USER-GUIDE.md)** for the full workflow, including batch mode and pricing details.

---

## Troubleshooting

**"Looks like setup isn't complete yet"**
Run `python3 setup.py` — it will walk you through what's missing.

**No Telegram messages arriving**
Check that `notifications/.env` exists with valid credentials. Test with:
```bash
source .venv/bin/activate
python3 -c "from notifications.notifier import notify; notify('test')"
```

**eBay or Facebook shows as logged out**
Log in to both in Chrome before the scheduled run.

**Chrome times out**
Follow the Chrome timeout fix in `CLAUDE.md` — it's a two-step reconnect procedure.

**Inventory is out of date on a second machine**
Run `git pull` before starting any session.
