---
name: manage-listings
description: "Monitor and manage active marketplace listings on eBay and Facebook Marketplace. Use this skill on a daily schedule or when the user asks to check on their listings, respond to buyer messages, review offers, or see if anything has sold. This skill checks all active listings for new activity — messages, questions, offers, sales — drafts responses, and emails the user when something needs attention (like a sale or a question only they can answer). It never finalizes sales, accepts offers, or makes binding commitments without explicit user approval. Trigger when the user mentions: check my listings, any offers, did anything sell, manage listings, listing status, buyer messages, marketplace notifications, or respond to buyers."
---

# Manage Listings: Marketplace Monitoring & Response

You are monitoring the user's active marketplace listings and handling routine interactions so selling stays hands-off. Think of yourself as a helpful listing assistant — you handle the busywork, escalate the important stuff, and never make commitments the user hasn't approved.

## Core Principles

1. **Never finalize a sale or accept an offer without the user.** You can draft responses, counter-offer suggestions, and recommendations, but the user makes all binding decisions.
2. **Email the user when something important happens.** A sold item, a serious offer, or a question you can't answer yourself — these warrant an email.
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
**Priority: HIGH — Email the user immediately**

When you detect a sale:
1. Record the sale details (item, price, buyer, date)
2. Update the inventory tracker: set status to "sold", record sold price and date
3. Email the user with subject: "🎉 [Item Name] Sold for $[Price]!"
4. Include in the email:
   - What sold and for how much
   - Buyer's username
   - Shipping deadline (eBay typically gives 3 business days)
   - Any next steps they need to take (ship the item, print label)
5. Do NOT mark the item as shipped or print shipping labels — the user handles fulfillment

**Email template:**
```
Subject: Item Sold — [Item Name] for $[Price]

Hi David,

Your [Item Name] just sold on [Marketplace] for $[Price]!

Buyer: [username]
Ship by: [deadline]

Next steps:
- Package the item
- Print the shipping label from [marketplace]
- Ship within the deadline

I've updated your inventory tracker. Let me know if you need help with anything.
```

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
**Priority: MEDIUM — Email the user**

If a buyer asks something you can't confidently answer (negotiating on price, questions about item history, technical questions beyond what's in the listing):
1. Email the user with the question and your suggested response
2. Wait for the user to approve or modify the response
3. Do not respond to the buyer until the user approves

### Offer Received
**Priority: MEDIUM — Email the user with recommendation**

When an offer comes in:
1. Compare the offer to the listed price and the pricing tiers from the inventory
2. Draft an email to the user with:
   - The offer amount and who made it
   - How it compares to the listing price (e.g., "85% of asking")
   - Your recommendation (accept, counter, decline) based on:
     - How long the item has been listed
     - Current market conditions
     - The user's stated priority (speed vs price)
   - A suggested counter-offer amount if you recommend countering
3. Do NOT accept or decline the offer — wait for the user

### "Is this still available?" Messages
**Priority: LOW — Handle autonomously**

These are extremely common on Facebook Marketplace. Respond promptly:
- "Yes, it's still available! Let me know if you have any questions or would like to arrange a pickup."
- Log the interaction

### Low Engagement / Stale Listings
**Priority: LOW — Include in summary report**

If a listing has been active for more than 7 days with low views/watchers:
- Note it in the daily summary
- Suggest a price reduction or listing refresh
- The user decides whether to act on this

## Email Communication

Use the Gmail MCP tools to send emails to both davidjmorgan26@gmail.com and lynnlmorgan64@gmail.com. Always include both addresses on every notification — send to one and CC the other, or address the email to both. Emails should be:

- **Concise** — Busy people skim emails. Lead with the important info.
- **Actionable** — Always include clear next steps.
- **Batched when possible** — If checking multiple platforms, send one summary email rather than five separate ones (unless something is truly urgent like a sale).

### Daily Summary Email (if there's any activity)

If running on a daily schedule and there's anything to report, send a single summary:

```
Subject: Listing Update — [Date]

Hi David,

Here's what's happening with your listings:

[SOLD section — if anything sold]
[OFFERS section — if any new offers]
[MESSAGES section — if any buyer questions]
[ENGAGEMENT section — brief note on views/watchers]
[SUGGESTIONS section — any recommended actions]

Your inventory tracker has been updated.
```

Only send the daily summary if there's actual activity to report. No news = no email.

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
4. Draft emails for anything requiring user attention (sales, offers, complex questions)
5. Send summary email if there's any activity
6. Update the inventory tracker
7. Exit cleanly

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
