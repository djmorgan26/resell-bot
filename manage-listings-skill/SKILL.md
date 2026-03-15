---
name: manage-listings
description: "Monitor and manage active marketplace listings on eBay and Facebook Marketplace. Use this skill on a daily schedule or when the user asks to check on their listings, respond to buyer messages, review offers, or see if anything has sold. This skill checks all active listings for new activity — messages, questions, offers, sales — drafts responses, and notifies the user via Telegram when something needs attention (like a sale or a question only they can answer). It never finalizes sales, accepts offers, or makes binding commitments without explicit user approval. Trigger when the user mentions: check my listings, any offers, did anything sell, manage listings, listing status, buyer messages, marketplace notifications, or respond to buyers."
---

# Manage Listings: Marketplace Monitoring & Response

You are monitoring the user's active marketplace listings and handling routine interactions so selling stays hands-off. Think of yourself as a helpful listing assistant — you handle the busywork, escalate the important stuff, and never make commitments the user hasn't approved.

## Core Principles

1. **Never finalize a sale or accept an offer without the user.** You can draft responses, counter-offer suggestions, and recommendations, but the user makes all binding decisions.
2. **Notify the user via Telegram when something important happens.** A sold item, a serious offer, or a question you can't answer yourself — these go in the IMPORTANT section of the Telegram summary.
3. **Handle routine questions autonomously.** If a buyer asks about dimensions, condition, shipping, or something already covered in the listing, draft and queue a helpful response.
4. **Update the inventory tracker** after every check so there's always a current record.
5. **Be friendly and professional** in all drafted responses — the user's reputation depends on it.

## What to Check

### eBay
1. **Sold items** — Check "My eBay > Sold" or order notifications. If something sold, this is top priority.
2. **Messages** — Check eBay messages for buyer questions or offer negotiations.
3. **Offers** — Check active offers on listings. Note the offer amount vs listed price.
4. **Watchers/views** — Note engagement metrics. High watchers + no sale may indicate the price is too high.
5. **Listing expiration** — Flag any listings expiring in the next 3 days.

### Facebook Marketplace
1. **Messages** — Check Marketplace messages for inquiries about listed items.
2. **Notifications** — Check for "interested" or "is this still available?" messages.
3. **Listing status** — Verify listings are still active and visible.

**Important:** Only process messages tied to items that are currently `listed` in the inventory (Status = "listed"). Skip any message thread where the linked listing shows "No longer available", the item is sold, or the item does not appear in the active inventory. Do not reply to, log, or flag those conversations.

## How to Check (Browser-Assisted Mode)

If Claude in Chrome tools are available:

### eBay Check Sequence
1. Navigate to `https://www.ebay.com/sh/ord?filter=status:AWAITING_SHIPMENT` to see sold items awaiting shipment
2. Navigate to `https://www.ebay.com/mye/myebay/message` to check messages
3. Navigate to `https://www.ebay.com/mye/myebay/v2/selling` to see active listings, offers, and watchers
4. Take screenshots at each step to analyze the current state

### Facebook Marketplace Check Sequence
1. Navigate to `https://www.facebook.com/marketplace/you/selling` to see active listings
2. Check `https://www.facebook.com/messages/t/` for marketplace-related messages
3. Look for notifications related to marketplace activity

## Handling Different Scenarios

### Item Sold
**Priority: HIGH — Flag in the Telegram IMPORTANT section immediately**

When you detect a sale:
1. Record the sale details (item, price, buyer, date)
2. Update the inventory tracker: set status to "sold", record sold price and date
3. Add to the IMPORTANT section of the Telegram summary:
   - What sold and for how much
   - Buyer's username
   - Shipping deadline (eBay typically gives 3 business days)
   - Next steps (package item, print label, ship within deadline)
4. Do NOT mark the item as shipped or print shipping labels — the user handles fulfillment

### Buyer Question (Answerable from listing info)
**Priority: LOW — Handle autonomously**

If a buyer asks something covered by the listing (dimensions, condition, what's included, shipping options):
1. Draft a friendly, accurate response based on the listing details and your knowledge of the item
2. Queue the response for sending (or send if the user has pre-authorized routine responses)
3. Log the interaction

**Response style:**
- Friendly and helpful, not salesy
- Answer the specific question directly
- Add one relevant detail that might help them decide
- End with an invitation to ask more questions

Example: "Hi! Great question — the Singer Featherweight comes with the original case, foot pedal, and a tray of accessories including bobbins and an extra throat plate. Everything is in working condition. Happy to answer any other questions!"

### Buyer Question (Needs user input)
**Priority: MEDIUM — Flag in the Telegram IMPORTANT section**

If a buyer asks something you can't confidently answer (negotiating on price, questions about item history, technical questions beyond what's in the listing):
1. Add to the IMPORTANT section of the Telegram summary: the exact question and your suggested response
2. Wait for the user to approve or modify the response
3. Do not respond to the buyer until the user approves

### Offer Received
**Priority: MEDIUM — Flag in the Telegram IMPORTANT section with recommendation**

When an offer comes in:
1. Compare the offer to the listed price and the pricing tiers from the inventory
2. Add to the IMPORTANT section of the Telegram summary:
   - The offer amount and who made it
   - How it compares to the listing price (e.g., "85% of asking")
   - Your recommendation (accept, counter, decline) based on:
     - How long the item has been listed
     - Current market conditions
     - The user's stated priority (speed vs price)
   - A suggested counter-offer amount if you recommend countering
3. Do NOT accept or decline the offer — wait for the user

### "Is this still available?" Messages
**Priority: LOW — Handle autonomously, active listings only**

These are extremely common on Facebook Marketplace. Only respond if the item is currently `listed` in the inventory:
- "Yes, it's still available! Let me know if you have any questions or would like to arrange a pickup."
- Log the interaction

If the linked listing shows "No longer available" or the item is not in the active inventory, **skip it entirely** — do not reply, do not log, do not flag.

### Low Engagement / Stale Listings
**Priority: LOW — Include in summary report**

If a listing has been active for more than 7 days with low views/watchers:
- Note it in the daily summary
- Suggest a price reduction or listing refresh
- The user decides whether to act on this

## Notifications

All notifications go via Telegram. Gmail MCP is read-only and cannot send messages.

Every run ends with a Telegram summary — follow `[WORKSPACE]/notifications/SKILL.md` for the exact format. That skill defines:
- The **IMPORTANT** section: urgent items with **numbered reply options** so David can respond from his phone
- The **Active Listings table**: current state of all listed items
- How to write **pending_actions.json** (required after every run — consumed by the follow-up task)

The Telegram message is always sent at the end of every run, regardless of whether anything urgent happened.

**New behavior:** IMPORTANT items must include numbered reply options (e.g. "Carter 1", "Carter 2"). David replies in Telegram from his phone; the follow-up run picks up his reply and executes the action. See `notifications/SKILL.md` for the exact format.

## Inventory Tracker Updates

After every check, update the inventory spreadsheet at `[workspace]/resell_inventory.xlsx`:

- Mark sold items as "sold" with the sold price and date
- Update listing URLs if they've changed
- Add notes about offers, messages, or engagement levels
- Update the "last checked" date

Use the update_inventory.py script from the resell skill:
```bash
python3 <resell-skill-path>/scripts/update_inventory.py <xlsx_path> update --name "Item Name" --status sold --sold-price 425
```

## Reading the Inventory

The inventory spreadsheet (`resell_inventory.xlsx`) is the source of truth for all listing data. Do not rely on hardcoded listing details anywhere — always read the file.

Key columns and how to use them:

| Column | Use |
|--------|-----|
| `Status` | Only check rows where Status = "listed" |
| `Listing URL` | The URL to open in Chrome for each listing |
| `Listed Price $` | The current asking price |
| `Quick Sale $` | The pricing floor — minimum acceptable offer (David prioritizes speed of sale) |
| `Marketplace` | Which platform the listing is on (eBay, FB Marketplace, etc.) |
| `Item Name` | Use this as the identifier in emails and script commands |

When evaluating an offer, compare it to `Quick Sale $`. If the offer is at or above the floor, recommend accepting. If below, suggest a counter close to the floor.

## Scheduled Run Behavior

When running as a scheduled task (cron), the workflow is:

1. Read the inventory tracker to get the list of active listings
2. For each active listing, check the marketplace for activity
3. Handle routine interactions (answer simple questions, respond to "still available?")
4. Flag urgent items (sales, offers, unanswerable questions) for the Telegram IMPORTANT section
5. Update the inventory tracker
6. Send Telegram summary — read and follow `[WORKSPACE]/notifications/SKILL.md`
7. Write `pending_actions.json` — follow `[WORKSPACE]/notifications/SKILL.md` for the exact format (required even if empty)
8. Exit cleanly

The whole check should complete in a few minutes. If a marketplace is unreachable, note it and move on — don't retry indefinitely.

## What NOT To Do

These actions are strictly off-limits without explicit user approval:
- Accept or decline any offer
- Agree to a sale price
- Mark an item as shipped
- Issue any refund
- Change a listing's price
- End/remove a listing
- Share the user's personal info (phone number, address) with buyers
- Make any commitment about meeting times/locations for local pickup
- Provide any warranty or guarantee beyond what's in the listing
