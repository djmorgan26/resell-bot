# resell-bot — Project Instructions for Claude

## What this project is

An AI-assisted reselling tool. The user gives Claude photos of items (or points to photos on their machine), and Claude handles everything: identification, market research, pricing, listing creation, and publishing to eBay and/or Facebook Marketplace via Chrome. Claude can also monitor active listings, auto-reply to routine buyer questions, and flag offers/sales for the user's attention.

All interaction happens in conversation — no scheduled tasks, no Telegram, no background processes.

---

## Configuration

Two config files control behavior:

### config.yaml
Basic identity and account info. Read at the start of any session.

```yaml
user:
  name: ""              # the user's first name
selling:
  ebay_username: ""     # their eBay seller username
  priority: "speed"     # "speed" = quick sale, "price" = maximize profit
marketplaces:
  - "ebay"
  - "fb_marketplace"
```

### user-preferences.yaml
Detailed selling preferences — pricing, shipping, listing style, photo organization, behavioral guardrails, and offer evaluation rules. **Skills must read this file before acting.** Each preference is marked as required or optional:

- **required: true** — Claude MUST have an answer before proceeding. If missing, stop and ask the user.
- **required: false** — Claude uses the default if the user hasn't set one.

If `config.yaml` does not exist, direct the user to run `python3 setup.py` before doing anything else.

---

## First-run check

Before starting any skill, verify the environment is configured:

1. `config.yaml` exists → read it for user settings
2. `user-preferences.yaml` exists → read it for selling preferences
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
├── user-preferences.yaml              ← selling preferences (gitignored)
├── setup.py                           ← interactive setup wizard
├── resell_inventory.xlsx              ← live inventory tracker (gitignored)
├── resell_inventory_template.xlsx     ← blank template for new users
├── requirements.txt                   ← Python deps
├── skills/                            ← all skill docs live here
│   ├── setup/SKILL.md                 ← AI-guided first-time setup
│   ├── organize-photos/SKILL.md       ← photo intake, naming, dedup, cleanup
│   ├── create-listing/SKILL.md        ← new listing creation (photos → published)
│   ├── manage-listings/SKILL.md       ← on-demand listing monitoring
│   └── review-issues/SKILL.md         ← review and fix skill issues
├── scripts/
│   ├── update_inventory.py            ← CLI tool for the spreadsheet
│   └── convert_heic.py               ← converts iPhone HEIC photos → JPEG
├── logs/issues/                       ← per-skill issue logs (gitignored)
├── photo-inbox/                       ← incoming photos (staging area)
└── items/                             ← archived photos after listing created
```

---

## Skills — when to use each

| Skill | When to use | How to invoke |
|-------|-------------|---------------|
| `skills/setup/SKILL.md` | First-time setup — walk a new user through full configuration | Read and follow the SKILL.md |
| `skills/organize-photos/SKILL.md` | User provides photos, or audit/clean up existing photo folders | Read and follow the SKILL.md |
| `skills/create-listing/SKILL.md` | Create a new listing — photos, pricing research, description, posting | Read and follow the SKILL.md |
| `skills/manage-listings/SKILL.md` | Check listings for activity, respond to buyers, review offers | Read and follow the SKILL.md |
| `skills/review-issues/SKILL.md` | Review problems logged by other skills, identify patterns, suggest fixes | Read and follow the SKILL.md |

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
| **Browser / Chrome** | Navigate eBay and Facebook Marketplace | All skills — listing checks, publishing |

Confirm Chrome is active before any marketplace interaction.

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

---

## Issue Logging

Every skill logs problems to `logs/issues/<skill-name>.json`. Each entry:

```json
{
  "timestamp": "ISO 8601",
  "type": "category",
  "description": "what happened",
  "resolution": "what was done, or 'unresolved'",
  "item": "item folder name if applicable"
}
```

Use `skills/review-issues/SKILL.md` to review, identify patterns, and fix recurring problems.

---

## Behavioral rules — always enforced

These are hard limits. Never override without explicit user approval:

- **Never accept or decline an offer** — present a recommendation and wait for the user to decide
- **Never finalize a sale** — tell the user and let them handle shipping/fulfillment
- **Never change a listing price** — suggest it, don't do it
- **Never end or remove a listing**
- **Never share the user's personal info** (phone, address) with buyers
- **Never make pickup/meeting commitments**

Routine actions that are fine autonomously:
- Answer "is this still available?" messages (active listings only)
- Reply to questions covered by the listing (dimensions, condition, shipping)
- Update `resell_inventory.xlsx`

---

## Pricing strategy

**Default to Market Price** when creating a new listing. The strategy is:
1. List at the **Market Price** tier (median of comparable sold listings)
2. If no interest after 1-2 weeks, lower toward the **Quick Sale** tier
3. Never go below the Quick Sale price — that's the floor

Check `user-preferences.yaml → pricing` for the user's specific settings.

---

## Active listings and pricing floors

`resell_inventory.xlsx` is the starting reference for all listing data — read it at the start of every run.

**However, the live marketplace is the ultimate source of truth for current status and price.** The user may update listings directly on eBay or Facebook Marketplace (changing price, marking sold, ending a listing) without going through Claude. When checking listings, always compare what the marketplace shows against the spreadsheet and sync any differences back. See `skills/manage-listings/SKILL.md` → "Syncing Marketplace Reality to Inventory" for the full reconciliation process.

The eBay seller username is in `config.yaml` under `selling.ebay_username`.

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

---

## Photo pipeline

Photos flow through two directories:

| Directory | Purpose |
|-----------|---------|
| `photo-inbox/` | Staging area — new photos land here for organization |
| `items/` | Permanent home — photos move here after a listing is created |

The `organize-photos` skill handles intake, HEIC conversion, folder naming, duplicate detection, and cleanup. The `create-listing` skill picks up from organized photos.

### Folder naming convention
```
[item-type]-[key-descriptor]-[size-or-id]
```
All lowercase, hyphens, max ~30 chars. See `skills/organize-photos/SKILL.md` for full rules and examples.

# currentDate
Today's date is 2026-03-30.
