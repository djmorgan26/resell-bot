---
name: manage-listings
description: "Monitor and manage active marketplace listings on eBay and Facebook Marketplace. Use this skill when the user asks to check on their listings, respond to buyer messages, review offers, or see if anything has sold. This skill checks all active listings for new activity — messages, questions, offers, sales — and presents findings directly in conversation. It never finalizes sales, accepts offers, or makes binding commitments without explicit user approval. Trigger when the user mentions: check my listings, any offers, did anything sell, manage listings, listing status, buyer messages, marketplace notifications, or respond to buyers."
---

# Manage Listings: Marketplace Monitoring & Response

You are monitoring the user's active marketplace listings and handling routine interactions so selling stays hands-off. Think of yourself as a helpful listing assistant — you handle the busywork, escalate the important stuff, and never make commitments the user hasn't approved.

## Before You Start

1. **Read `user-preferences.yaml`** for:
   - Auto-reply settings (which buyer questions can you answer without approval?)
   - Offer evaluation preferences (auto-accept above X? counter below Y?)
   - Stale listing threshold (how many days before flagging?)
   - If any **REQUIRED** preferences are missing, stop and ask the user before proceeding.

2. **Read `resell_inventory.xlsx`** as the starting point for:
   - Which items are currently `listed`
   - Listing prices and Quick Sale floors
   - Marketplace platform for each item
   - Listing URLs

   **Note:** The spreadsheet may be out of date — the user sometimes updates listings directly on eBay or Facebook Marketplace (changing price, marking sold, ending a listing) without going through Claude. Always treat the **live marketplace** as the ultimate source of truth when there's a conflict. See "Syncing Marketplace Reality to Inventory" below.

## Core Principles

1. **Never finalize a sale or accept an offer without the user.** Present your recommendation in conversation and wait for their decision right here.
2. **Present all important findings directly in conversation.** Sales, offers, and unanswerable questions go at the top of your findings, formatted clearly.
3. **Handle routine questions autonomously.** If a buyer asks about dimensions, condition, shipping, or something already covered in the listing, draft and (with user approval) send the response immediately via Chrome.
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
**Priority: HIGH — Present immediately at the top of findings**

When you detect a sale:
1. Record the sale details (item, price, buyer, date)
2. Update the inventory tracker: set status to "sold", record sold price and date
3. Present in conversation:
   - What sold and for how much
   - Buyer's username
   - Shipping deadline (eBay typically gives 3 business days)
   - Next steps (package item, print label, ship within deadline)
4. Do NOT mark the item as shipped or print shipping labels — the user handles fulfillment

### Buyer Question (Answerable from listing info)
**Priority: LOW — Handle with user approval**

If a buyer asks something covered by the listing (dimensions, condition, what's included, shipping options):
1. Draft a friendly, accurate response based on the listing details and your knowledge of the item
2. Show the draft to the user and ask for approval to send
3. Upon approval, use Chrome to send the response immediately to the buyer
4. Log the interaction

**Response style:**
- Friendly and helpful, not salesy
- Answer the specific question directly
- Add one relevant detail that might help them decide
- End with an invitation to ask more questions

Example: "Hi! Great question — the Singer Featherweight comes with the original case, foot pedal, and a tray of accessories including bobbins and an extra throat plate. Everything is in working condition. Happy to answer any other questions!"

### Buyer Question (Needs user input)
**Priority: MEDIUM — Present in conversation for decision**

If a buyer asks something you can't confidently answer (negotiating on price, questions about item history, technical questions beyond what's in the listing):
1. Present in conversation: the exact question and your suggested response
2. Wait for the user to approve, modify, or decline the response
3. Upon approval, use Chrome to send the response immediately
4. Do not respond to the buyer without user approval

### Offer Received
**Priority: MEDIUM — Present in conversation with recommendation**

When an offer comes in:
1. Compare the offer to the listed price and the pricing tiers from the inventory
2. Present in conversation:
   - The offer amount and who made it
   - How it compares to the listing price (e.g., "85% of asking")
   - Whether it meets the Quick Sale floor
   - Your recommendation (accept, counter, decline) based on:
     - How long the item has been listed
     - Current market conditions
     - The user's stated priority (speed vs price)
   - A suggested counter-offer amount if you recommend countering
3. Wait for the user to decide (accept, counter, decline) in the conversation
4. Upon decision, use Chrome to send the acceptance or counter immediately
5. Do NOT accept or decline the offer yourself

### "Is this still available?" Messages
**Priority: LOW — Handle with user approval, active listings only**

These are extremely common on Facebook Marketplace. Only respond if the item is currently `listed` in the inventory:
1. Draft the response: "Yes, it's still available! Let me know if you have any questions or would like to arrange a pickup."
2. Show the draft to the user for approval
3. Upon approval, use Chrome to send immediately
4. Log the interaction

If the linked listing shows "No longer available" or the item is not in the active inventory, **skip it entirely** — do not reply, do not log, do not flag.

### Low Engagement / Stale Listings
**Priority: LOW — Present in conversation**

If a listing has been active for longer than the threshold in `user-preferences.yaml` with low views/watchers:
- Note it in your findings presentation
- Suggest a price reduction or listing refresh
- The user decides whether to act on this

## Presenting Your Findings

Present all findings directly to the user in conversation, organized by priority:

1. **Urgent items first** (at the top):
   - Sales: item name, amount, buyer, shipping deadline
   - Offers: amount, comparison to asking price, your recommendation
   - Unanswerable questions: exact question, your suggested response

2. **Routine items next**:
   - Answerable questions with drafted responses (awaiting approval to send)
   - "Is this still available?" responses (awaiting approval to send)

3. **Status table**:
   - A table of all active listings with: item name, marketplace, listed price, watchers/views, last activity, days listed

4. **Stale listings** (if any):
   - Items to consider refreshing or repricing

## Syncing Marketplace Reality to Inventory

**The user may update listings directly on eBay or Facebook Marketplace without going through Claude.** This means the spreadsheet can be stale. During every listing check, compare what you see on the marketplace against what the spreadsheet says, and fix any discrepancies.

### What to look for

| Marketplace shows | Spreadsheet says | Action |
|---|---|---|
| Item sold | Status = "listed" | Update to "sold", record sold price and date, flag to user |
| Listing ended/expired | Status = "listed" | Update to "expired", note in findings |
| Price changed | Different `Listed Price $` | Update the spreadsheet price to match marketplace |
| Listing not found / removed | Status = "listed" | Update to "expired" or "removed", ask user what happened |
| New listing not in spreadsheet | No row exists | Add a new row with what you can see (name, price, URL, marketplace), flag to user for confirmation |
| Item marked sold in spreadsheet | Still active on marketplace | Note the conflict — ask the user which is correct |

### How to handle conflicts

1. **Always trust the marketplace over the spreadsheet** for current status — if eBay says it sold, it sold.
2. **Always trust the spreadsheet for pricing floors** — Quick Sale $ and Market Price $ don't change just because the user adjusted the listing price on the marketplace.
3. After syncing, note what changed in your findings presentation so the user knows the spreadsheet was updated.
4. Log any sync corrections as issue type `"inventory"` so patterns can be reviewed.

---

## Inventory Tracker Updates

After every check, update the inventory spreadsheet at `[workspace]/resell_inventory.xlsx`:

- Sync any marketplace changes back to the spreadsheet (see above)
- Mark sold items as "sold" with the sold price and date
- Update listing URLs if they've changed
- Update listed prices if the user changed them on the marketplace
- Add notes about offers, messages, or engagement levels
- Update the "last checked" date

Use the update_inventory.py script:
```bash
python3 [WORKSPACE]/scripts/update_inventory.py <xlsx_path> update --name "Item Name" --status sold --sold-price 425
```

## Reading the Inventory

The inventory spreadsheet (`resell_inventory.xlsx`) is the starting reference for listing data — but the live marketplace is the ultimate source of truth for current status and price. Always read the spreadsheet first, then verify against what you see in Chrome.

Key columns and how to use them:

| Column | Use |
|--------|-----|
| `Status` | Start by checking rows where Status = "listed" — but verify each is still active on the marketplace |
| `Listing URL` | The URL to open in Chrome for each listing |
| `Listed Price $` | The price we expect — compare against what the marketplace actually shows |
| `Quick Sale $` | The pricing floor — minimum acceptable offer. This does NOT change when the user adjusts the marketplace price. |
| `Marketplace` | Which platform the listing is on (eBay, FB Marketplace, etc.) |
| `Item Name` | Use this as the identifier in emails and script commands |

When evaluating an offer, compare it to `Quick Sale $`. If the offer is at or above the floor, recommend accepting. If below, suggest a counter close to the floor.

## Sending Buyer Responses via Chrome

When the user approves a drafted response (for a buyer question, "still available?" message, or offer acceptance/counter):

1. Use Chrome to navigate to the appropriate marketplace messaging interface
2. Find the conversation thread
3. Type and send the approved message
4. Log the action to `logs/issues/manage-listings.json`
5. Report success back to the user

For eBay: Navigate to the messages page and find the conversation. For Facebook Marketplace: Navigate to messages and find the chat thread.

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

## Issue Logging

After every run, log findings and actions to `logs/issues/manage-listings.json` in this format:

```json
{
  "timestamp": "ISO 8601 timestamp",
  "type": "[chrome|auto-reply|offer-eval|inventory|stale-listing|other]",
  "description": "what happened",
  "resolution": "what was done, or 'unresolved'",
  "item": "item folder name if applicable"
}
```

Example:
```json
{
  "timestamp": "2026-03-30T14:32:00Z",
  "type": "offer-eval",
  "description": "Offer of $280 received for Singer Featherweight (listed at $350)",
  "resolution": "unresolved — awaiting user decision",
  "item": "singer-featherweight"
}
```

Keep this log updated with all activities — successful sends, unanswered questions, pricing recommendations, and any Chrome errors.
