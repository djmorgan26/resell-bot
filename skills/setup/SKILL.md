---
name: setup
description: "First-time setup for resell-bot. Walk a new user through complete configuration: creating config.yaml and user-preferences.yaml, connecting Chrome to eBay and Facebook Marketplace, creating their inventory file, and listing their first item. Use this when someone has just cloned the repo and needs to get everything working."
---

# resell-bot First-Time Setup

This skill guides a new user through everything needed to get resell-bot running on their machine. Work through each stage in order. At the end, the user will have a fully configured resell bot ready to manage listings.

---

## Before you begin

Check whether setup has already been done:

```bash
ls [WORKSPACE]/config.yaml 2>/dev/null && echo "EXISTS" || echo "MISSING"
ls [WORKSPACE]/user-preferences.yaml 2>/dev/null && echo "EXISTS" || echo "MISSING"
ls [WORKSPACE]/resell_inventory.xlsx 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

- If all three exist, setup is done — proceed to Stage 4 to verify Chrome access, then Stage 6.
- If any are missing, start at Stage 1.

---

## Stage 1 — Python environment

Check whether the virtual environment is ready:

```bash
ls [WORKSPACE]/.venv 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

If missing:
```bash
cd [WORKSPACE] && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Verify:
```bash
[WORKSPACE]/.venv/bin/python3 -c "import openpyxl, yaml; print('OK')"
```

---

## Stage 2A — Create config.yaml

Ask the user:
- Their first name
- Their eBay seller username (if they sell on eBay)
- Whether they also use Facebook Marketplace
- Whether they prefer speed of sale or maximizing price

Then write `[WORKSPACE]/config.yaml`:
```yaml
user:
  name: "[their name]"
selling:
  ebay_username: "[their username]"
  priority: "speed"   # or "price"
marketplaces:
  - "ebay"            # remove if not applicable
  - "fb_marketplace"  # remove if not applicable
```

---

## Stage 2B — Create user-preferences.yaml

Copy the template, then fill in their answers from Stage 2A:

```bash
cp [WORKSPACE]/user-preferences.yaml.template [WORKSPACE]/user-preferences.yaml
```

Open `user-preferences.yaml` and fill in the **required** fields using the answers collected in Stage 2A:

1. `user.name` — their first name
2. `accounts.ebay_username` — their eBay username (if applicable)
3. `accounts.marketplaces` — remove any platforms they don't use
4. `pricing.priority` — "speed" or "price" (from their answer)
5. `shipping.default` — confirm "local_pickup_only" or change to "offer_shipping"

Then briefly review the **optional** sections with the user. Explain what each one does and ask if they want to change any defaults:

- **Pricing** — starting tier, FB discount, stale listing threshold
- **Listing preferences** — platform auto-selection, auto-reply, description structure
- **Photo organization** — HEIC conversion, duplicate detection, folder naming
- **Behavioral guardrails** — hard limits (recommend keeping all enabled)

Most users can accept all the defaults. This file is gitignored and can be adjusted anytime.

---

## Stage 2C — Create inventory file

```bash
cp [WORKSPACE]/resell_inventory_template.xlsx [WORKSPACE]/resell_inventory.xlsx
```

This creates an empty inventory spreadsheet where each listing will be tracked.

---

## Stage 4 — Log in to marketplaces in Chrome

Open Chrome and navigate to each marketplace the user sells on.

### eBay
```
navigate(url: "https://www.ebay.com/sh/ord", tabId: [TAB_ID])
```
Tell the user: "Please log in to eBay if you're not already logged in. Let me know when you're ready."

Wait for confirmation, then verify you can see the seller dashboard.

### Facebook Marketplace
```
navigate(url: "https://www.facebook.com/marketplace/you/selling", tabId: [TAB_ID])
```
Tell the user: "Please log in to Facebook if you're not already. Let me know when you can see your listings."

Wait for confirmation. This login persists between runs as long as Chrome stays open with the session.

---

## Stage 6 — First listing (optional)

If the user has items to sell right now, offer to create their first listing:

> "Would you like to add your first item now? If you have photos ready, I can help you research pricing, write a description, and get it posted."

If yes, follow `[WORKSPACE]/skills/create-listing/SKILL.md`.

---

## Stage 7 — Summary

When all stages are complete, summarize what's been set up:

- `config.yaml` — your personal settings (name, eBay username, marketplace preferences)
- `user-preferences.yaml` — your selling preferences (shipping, communication, pricing)
- `resell_inventory.xlsx` — your inventory spreadsheet (currently empty, add items as you list them)
- Chrome logged in to: [list marketplaces they use]

> "You're all set! You can now use the **create-listing** skill to add new items anytime. Follow the skill docs in `[WORKSPACE]/skills/` to manage listings, monitor buyer questions, and track your sales."
