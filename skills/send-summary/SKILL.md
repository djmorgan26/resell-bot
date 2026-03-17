---
name: send-listing-summary
description: "Send a formatted Telegram summary after a manage-listings run. Call this as the final step of every scheduled listing check. Formats all findings into a clean two-section message: an IMPORTANT block at the top (urgent items needing the user's action with numbered reply options) and a table of all active listings at the bottom. Also writes pending_actions.json for the follow-up run to consume."
---

# Send Listing Summary via Telegram

Call this skill as the **last step** of every manage-listings run. It sends one consolidated Telegram message summarizing everything that happened and the current state of all active listings.

The user can reply directly in Telegram (e.g. "Carter 1") to trigger actions in the follow-up run. Always format IMPORTANT items with numbered options so they can respond from their phone.

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

**Important:** Always navigate to `https://example.com` (or any neutral page) before running the JS fetch. Facebook and eBay pages have CSP headers that block outbound fetch calls to `api.telegram.org`.

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

This section is only included if there are **urgent items requiring the user's attention**. If nothing is urgent, omit it entirely and start directly with the listings table.

Urgent items include:
- A sale that completed (needs shipping)
- An offer received (needs accept/decline decision)
- A buyer question you couldn't answer from the listing
- Anything else where David must act before you can proceed

**Format — use numbered reply options so David can respond from Telegram on his phone:**

```
🔔 IMPORTANT — reply needed:

[KEY] [Short listing name]
[Platform] · [Buyer name] · [time ago]
Q: "[exact buyer message or situation]"

Reply:
  "[KEY] 1" → [Recommended response — mark with ✓]
  "[KEY] 2" → [Alternative response]
  "[KEY] 3" → hold — decide later
```

**KEY rules:**
- Use the buyer's first name (e.g. `Carter`, `Mike`)
- If no buyer name, use a short item code (e.g. `Tarkay`, `Feather`)
- Single word, no spaces, will be matched case-insensitively
- Must be unique within the message

**Option guidelines:**
- Option 1 is always the recommended default (add ✓)
- Always include a "hold — decide later" as the last option
- For SOLD items, no reply options needed — just state what sold and what David needs to do (ship by when, etc.)

**Example — buyer question:**
```
🔔 IMPORTANT — reply needed:

[Carter] Complete Home Theater Bundle
Facebook · Carter · 1h ago
Q: "Only selling as a bundle or would you just sell the floor speakers?"

Reply:
  "Carter 1" → "Hi Carter! Selling as a bundle for now, but happy to revisit if it doesn't move. Interested in the full set?" ✓
  "Carter 2" → "Hi Carter! I can sell the floor speakers separately — $325 for the pair. Want to proceed?"
  "Carter 3" → hold — decide later
```

**Example — sold item (no reply options):**
```
🔔 SOLD — action needed:

Singer Featherweight 221 sold for $365 on eBay.
Buyer: memcg_75. Ship by: Tue Mar 17 (3 business days).
→ Print label and drop off before deadline.
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

─────────────────────────────────────
Active Listings — [DATE]
─────────────────────────────────────
Item                    | Platform | Listed | Floor | Notes
[row per active listing]
─────────────────────────────────────
```

Keep the total message under ~4000 characters (Telegram's limit). If it would exceed that, truncate the Notes column first.

---

## Writing pending_actions.json (REQUIRED after every run)

After composing the Telegram message, write `[WORKSPACE]/notifications/pending_actions.json`.
This file is consumed by the follow-up scheduled run 1 hour later.

**If there ARE pending items** — write each IMPORTANT item as a structured entry:

```bash
source [WORKSPACE]/.venv/bin/activate
python3 - << 'EOF'
import json
from pathlib import Path

pending = {
  "run_date": "YYYY-MM-DD",
  "pending": [
    {
      "key": "Carter",
      "platform": "facebook",
      "listing_name": "Complete Home Theater System",
      "buyer_name": "Carter",
      "question": "Only selling as a bundle or would you just sell the floor speakers?",
      "thread_url": "https://www.facebook.com/messages/t/3025287857861969",
      "options": {
        "1": "Hi Carter! Selling as a bundle for now, but happy to revisit if it doesn't move. Interested in the full set?",
        "2": "Hi Carter! I can sell the floor speakers separately — $325 for the pair. Want to proceed?",
        "3": "__HOLD__"
      }
    }
  ]
}

path = Path("[WORKSPACE]/notifications/pending_actions.json")
path.write_text(json.dumps(pending, indent=2))
print("pending_actions.json written:", len(pending["pending"]), "item(s)")
EOF
```

Option `"3"` should always be `"__HOLD__"` — the follow-up run skips it (no message sent, item stays pending for the next morning run).

**If there are NO pending items** — still write the file with an empty list:

```bash
python3 -c "
import json
from pathlib import Path
Path('[WORKSPACE]/notifications/pending_actions.json').write_text(
    json.dumps({'run_date': 'YYYY-MM-DD', 'pending': []}, indent=2)
)
print('pending_actions.json cleared')
"
```

---

## Two-Way Reply Flow (how it all connects)

```
Morning run   →  sends Telegram with 🔔 IMPORTANT + numbered reply options
              →  writes pending_actions.json

David (phone) →  replies in Telegram: "Carter 1"

Follow-up run →  reads pending_actions.json (if empty: exits quietly)
(1hr later)   →  reads Telegram for David's recent messages (if none: exits quietly)
              →  matches "Carter 1" → reply text for option 1
              →  opens Chrome, navigates to FB thread, sends the reply
              →  resolves Carter from pending_actions.json
              →  sends Telegram confirmation: "✓ Sent reply to Carter on Facebook"

Next morning  →  any unresolved items re-appear in IMPORTANT with same format
```
