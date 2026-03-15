---
name: send-listing-summary
description: "Send a formatted Telegram summary after a manage-listings run. Call this as the final step of every scheduled listing check. Formats all findings into a clean two-section message: an IMPORTANT block at the top (urgent items needing David's action) and a table of all active listings at the bottom."
---

# Send Listing Summary via Telegram

Call this skill as the **last step** of every manage-listings run. It sends one consolidated Telegram message summarizing everything that happened and the current state of all active listings.

---

## How to Send

### In the Cowork VM (scheduled runs) — use Chrome JavaScript

The Cowork sandbox proxy blocks `api.telegram.org` from Python. Use the Chrome browser tool to send instead. Read the token and chat ID from `notifications/.env`, then call:

```javascript
// Run via mcp__Claude_in_Chrome__javascript_tool
(async () => {
  const token = '<TELEGRAM_BOT_TOKEN from .env>';
  const chatId = '<TELEGRAM_CHAT_ID from .env>';
  const resp = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text: message })
  });
  const data = await resp.json();
  return data.ok ? 'SENT OK' : 'ERROR: ' + JSON.stringify(data);
})()
```

To get the credentials, read `notifications/.env` from the workspace using the Bash or Read tool, then substitute the values into the JavaScript above.

### Outside the Cowork VM — use Python

```python
import sys
sys.path.insert(0, 'notifications')
from notifications.notifier import notify

notify(message)
```

Or via shell:

```bash
.venv/bin/python3 -c "
import sys
sys.path.insert(0, 'notifications')
from notifications.notifier import notify
notify('''<message here>''')
"
```

---

## Message Format

Build the message as two sections, separated by a divider.

---

### Section 1 — IMPORTANT

This section is only included if there are **urgent items requiring David's attention**. If nothing is urgent, write `No urgent items.` as the only line under the header.

Urgent items include:
- A sale that completed (needs shipping)
- An offer received (needs accept/decline decision)
- A buyer question you couldn't answer from the listing
- Anything else where David must act before you can proceed

**Format:**
```
IMPORTANT:
• [Item Name] — SOLD for $[price] on [platform]. Buyer: [username]. Ship by [date].
• [Item Name] — Offer received: $[amount] (floor: $[quick_sale_price], listed: $[listed_price]). Recommend: [accept / counter at $X / decline]. Awaiting your decision.
• [Item Name] — Buyer question needs your input: "[exact question]". Suggested reply ready — awaiting approval.
```

Or if nothing urgent:
```
IMPORTANT:
No urgent items.
```

---

### Section 2 — Active Listings Table

A plain-text table of every row in the inventory where `Status = "listed"`. Use fixed-width spacing so it renders cleanly in Telegram (monospace font).

**Columns:** Item | Platform | Listed $ | Floor $ | Notes

- **Item** — short name (truncate at ~22 chars if needed)
- **Platform** — `eBay` or `FB Mkt`
- **Listed $** — current asking price
- **Floor $** — Quick Sale $ from inventory (minimum acceptable)
- **Notes** — one short note if relevant (e.g. "3 watchers", "offer pending", "msg replied"); otherwise `—`

**Example:**
```
─────────────────────────────────────────────────────
Active Listings — 2026-03-15
─────────────────────────────────────────────────────
Item                    | Platform | Listed | Floor | Notes
Singer Featherweight 221| eBay     |   $550 |  $400 | 3 watchers
Tarkay Lithograph       | eBay     |   $350 |  $250 | —
Paradigm Monitor 9 Spkrs| FB Mkt   |   $375 |  $275 | —
Paradigm CC-370 Center  | FB Mkt   |   $150 |  $100 | —
Paradigm PS-1000 Sub    | FB Mkt   |   $200 |  $150 | —
Marantz AV Receiver     | FB Mkt   |   $150 |  $100 | —
Asian Shadow Box Cabinet| FB Mkt   |    $80 |   $60 | —
Tapestry Club Chair     | FB Mkt   |   $125 |   $90 | —
Geometric Recliner      | FB Mkt   |   $150 |  $110 | —
─────────────────────────────────────────────────────
```

---

## Full Message Template

```
IMPORTANT:
[urgent items, or "No urgent items."]

─────────────────────────────────────────
Active Listings — [DATE]
─────────────────────────────────────────
Item                    | Platform | Listed | Floor | Notes
[row per active listing]
─────────────────────────────────────────
```

Keep the total message under ~4000 characters (Telegram's limit). If it would exceed that, truncate the Notes column first.
