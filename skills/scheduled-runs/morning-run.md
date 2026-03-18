# Morning Run — Daily Listing Check + Photo Inbox

This is the master orchestration doc for the daily scheduled run. Follow these steps in order.

---

## Step 1 — Find the workspace

```bash
find /sessions -name "resell_inventory.xlsx" 2>/dev/null | head -1 | xargs dirname
```

Store the result as WORKSPACE. All `[WORKSPACE]` references below use this path.

---

## Step 2 — Fix Chrome if needed

If Chrome tools are timing out, follow the "Fixing Chrome timeouts" instructions in `[WORKSPACE]/CLAUDE.md`.

---

## Step 3 — Check the photo inbox

Read and follow `[WORKSPACE]/skills/photo-inbox/SKILL.md`.

This checks Telegram for new photos David sent from his phone. If new item photos are found, hand each off to `[WORKSPACE]/skills/create-listing/SKILL.md` to create and publish listings before proceeding to listing monitoring.

If no new photos, continue to Step 4.

---

## Step 4 — Check for instructions from David

Navigate Chrome to `https://example.com`, then fetch recent Telegram messages (last 24 hours) using the Chrome JS method from `[WORKSPACE]/skills/followup/SKILL.md` (Step 2).

Read `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from `[WORKSPACE]/notifications/.env`.

Filter for messages from David (non-bot) that are NOT in "Key Number" reply format (those are handled by the followup run).

If any are found, treat them as standing instructions for this run — keep them in mind throughout Steps 5 and 6 (e.g. "don't respond to Carter", "hold off on the Singer listing"). Note any applied instructions in the Telegram summary at the end.

If none found, continue normally.

---

## Step 4b — Publish any items marked "ready"

Read `[WORKSPACE]/resell_inventory.xlsx` and check for rows where Status = "ready". These are items that the poll bot has fully researched and documented but not yet posted.

For each "ready" item:
1. Find its photos in `[WORKSPACE]/items/<item-folder>/`
2. Read and follow `[WORKSPACE]/skills/create-listing/SKILL.md` Stage 6 ONLY (Publish)
3. Use Chrome browser tools to post the listing on the target marketplace(s)
4. After publishing, update the inventory: set status to "listed", add the listing URL
5. Note the published item in the Telegram summary

If Chrome is unavailable, skip publishing and note it in the summary.

---

## Step 5 — Read the inventory

```bash
# Read the inventory spreadsheet
cat [WORKSPACE]/resell_inventory.xlsx
```

Only check rows where Status = "listed". These are your active listings — get their URLs, listed prices, and pricing floors from the spreadsheet. Do not rely on hardcoded data.

---

## Step 6 — Run the listing check

Read and follow `[WORKSPACE]/skills/manage-listings/SKILL.md`.

Use Chrome to visit each listing URL and check for activity:
- **eBay:** sold items, messages, offers, watchers, expiring listings
- **Facebook Marketplace:** messages, "is this still available?" inquiries, listing status

Handle routine interactions per the skill. Flag anything needing David's attention for the Telegram IMPORTANT section.

Apply any instructions found in Step 4 when deciding how to handle each listing.

---

## Step 7 — Update the inventory

Update `resell_inventory.xlsx` to reflect anything that changed (status, notes, last checked date).

```bash
python3 [WORKSPACE]/scripts/update_inventory.py [WORKSPACE]/resell_inventory.xlsx update \
  --name "Item Name" --status sold --sold-price 425
```

---

## Step 8 — Send the Telegram summary

Read and follow `[WORKSPACE]/skills/send-summary/SKILL.md`.

This skill defines exactly how to format and send the post-run Telegram message to David, including:
- The IMPORTANT section with numbered reply options
- The active listings table
- Writing `pending_actions.json` (required after every run)

If instructions from Step 4 were applied, include a short "📌 Instructions applied" note at the bottom of the summary.
