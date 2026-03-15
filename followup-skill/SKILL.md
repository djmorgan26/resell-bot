---
name: followup-listings
description: "Act on David's Telegram replies to pending listing decisions. Use this skill whenever running the follow-up scheduled task — it reads David's recent Telegram messages, matches them to any pending actions from the morning monitoring run, sends the appropriate buyer replies in the browser, resolves handled items, and confirms back to David via Telegram. Trigger when the scheduled follow-up task runs, or when the user says 'check my replies', 'did I respond', 'act on my telegram replies', or 'process pending actions'."
---

# Follow-Up: Act on Telegram Replies

You are the follow-up half of David's resell bot. The morning monitoring run checks listings and sends David a Telegram summary with numbered reply options for anything needing his decision. This skill picks up where that left off: reads his replies, executes the chosen actions in the browser, and confirms what was done.

## How the Two-Run Flow Works

```
Morning run  → checks listings, sends Telegram with 🔔 IMPORTANT + numbered options
             → writes notifications/pending_actions.json

David (phone) → replies in Telegram: "Carter 1"

This skill  → reads pending_actions.json (if empty: exits quietly)
(1hr later)  → reads David's Telegram replies via Chrome JS
             → matches "Carter 1" to the reply text for option 1
             → opens the FB/eBay thread, sends the reply
             → resolves the item from pending_actions.json
             → sends Telegram confirmation
```

If nothing is pending, or David hasn't replied, exit cleanly — no Telegram message needed.

---

## Step 1 — Find the Workspace

```bash
find /sessions -name "resell_inventory.xlsx" 2>/dev/null | head -1 | xargs dirname
```

Store this path as WORKSPACE for all subsequent steps.

---

## Step 2 — Check for Pending Actions

Read `[WORKSPACE]/notifications/pending_actions.json`.

If the file doesn't exist, or `"pending"` is an empty list → **stop here**. Exit cleanly with no Telegram message. There's nothing to act on.

---

## Step 3 — Fetch David's Recent Telegram Replies via Chrome

Python can't reach `api.telegram.org` from the Cowork sandbox (proxy blocks it). Use Chrome JS instead — the same pattern used for sending.

**3a.** Read `TELEGRAM_BOT_TOKEN` from `[WORKSPACE]/notifications/.env`.

**3b.** Navigate Chrome to `https://example.com` — this clears any CSP restrictions from FB or eBay pages that would block the outbound fetch.

**3c.** Run this JavaScript via the Chrome JS tool (substitute the real token):

```javascript
(async () => {
  const token = '<TELEGRAM_BOT_TOKEN>';
  const resp = await fetch(
    `https://api.telegram.org/bot${token}/getUpdates?limit=100&timeout=5`
  );
  const data = await resp.json();
  return JSON.stringify(data);
})()
```

**3d.** Save the returned JSON string to a temp file:

```bash
echo '<JSON_STRING>' > /tmp/tg_updates.json
```

**3e.** Parse it with Python to extract David's recent messages:

```bash
source [WORKSPACE]/.venv/bin/activate
python3 - << 'EOF'
import json, sys
sys.path.insert(0, '[WORKSPACE]')
from notifications.telegram_reader import parse_updates_response
raw = open('/tmp/tg_updates.json').read()
msgs = parse_updates_response(raw, hours=2)
print(json.dumps(msgs, default=str))
EOF
```

If the output is `[]` → **stop here**. David hasn't replied yet. Exit cleanly, no Telegram message.

Store the parsed list as MESSAGES.

---

## Step 4 — Match Replies to Pending Actions

David's reply format is: `"Carter 1"`, `"Carter: 2"`, etc. — a key (usually a buyer's first name) plus an option number.

Run this, passing MESSAGES as JSON input:

```bash
python3 - << 'EOF'
import json, sys
sys.path.insert(0, '[WORKSPACE]')
from notifications.reply_handler import match_replies

msgs = json.loads('<MESSAGES_JSON>')
matched = match_replies(msgs)
print(json.dumps(matched, default=str))
EOF
```

If the output is `[]` → **stop here**. No replies matched any pending action (David may have replied with something unrecognized). Exit cleanly.

Store the result as MATCHED.

---

## Step 5 — Send Replies in the Browser

For each item in MATCHED:

**a.** Check `action["reply_text"]`:
- If it's `"__HOLD__"` → skip entirely. David chose to wait on this one.
- Otherwise → proceed to send the reply.

**b.** Navigate Chrome to `action["thread_url"]`:
- `"facebook"` platform → the Facebook Messenger thread URL
- `"ebay"` platform → the eBay messages thread URL

**c.** Find the message input box and type `action["reply_text"]`. Send it.

**d.** Take a screenshot to confirm the message was sent successfully. If the send fails, note it — don't silently skip.

---

## Step 6 — Resolve Handled Actions

**6a.** Remove resolved items from `pending_actions.json`:

```bash
python3 - << 'EOF'
import sys
sys.path.insert(0, '[WORKSPACE]')
from notifications.telegram_reader import parse_updates_response
from notifications.reply_handler import match_replies, resolve_actions

msgs = parse_updates_response(open('/tmp/tg_updates.json').read(), hours=2)
matched = match_replies(msgs)
resolved_keys = [m["action"]["key"] for m in matched if m["reply_text"] != "__HOLD__"]
if resolved_keys:
    resolve_actions(resolved_keys)
    print("Resolved:", resolved_keys)
EOF
```

**6b.** Acknowledge Telegram updates via Chrome JS so David's replies don't reappear in the next run. Get the highest `update_id` from MESSAGES, then run:

```javascript
(async () => {
  const token = '<TELEGRAM_BOT_TOKEN>';
  const offset = <max_update_id + 1>;
  await fetch(
    `https://api.telegram.org/bot${token}/getUpdates?offset=${offset}&limit=1&timeout=1`
  );
  return 'acknowledged';
})()
```

---

## Step 7 — Update the Inventory

For each item in MATCHED where a real reply was sent (not `__HOLD__`), update `resell_inventory.xlsx` with a note:

```bash
python3 [WORKSPACE]/resell-skill/scripts/update_inventory.py [WORKSPACE]/resell_inventory.xlsx \
  update --name "Item Name" \
  --notes "Reply sent to [buyer] [date]: '[first 60 chars of reply]...'"
```

Use today's date in the note. This keeps the inventory in sync with what was actually communicated to buyers.

---

## Step 8 — Send Telegram Confirmation

Navigate Chrome to `https://example.com`, then send a confirmation message following the instructions in `[WORKSPACE]/notifications/SKILL.md` (Chrome JS fetch method — the same one used for outbound messages in the morning run).

Build the message like this:

```
✓ Follow-up complete — [DATE] [TIME]

Replies sent:
• [Buyer] ([listing name]): "[reply text, truncated to ~80 chars]"

[N] item(s) resolved. [N] still pending (will re-appear tomorrow).
```

Rules:
- Only list items where a real reply was sent (skip `__HOLD__` items).
- If there are still pending items after this run (held or unmatched), include the count.
- If every matched item was `__HOLD__`, send: `"✓ Follow-up checked — no replies sent (all held for later)."`
- Keep the message under 500 characters — it's a phone notification, not a report.

---

## What NOT To Do

These rules carry over from the main listing skill:

- Never accept or decline an offer on David's behalf — if an action in `pending_actions.json` looks like an offer acceptance, flag it and ask David directly.
- Never change a listing price.
- Never share David's personal info (phone, address) in any reply.
- Never make pickup/meeting commitments.
- Never send a message that wasn't explicitly pre-approved by David via his numbered reply.

---

## Troubleshooting

**Chrome JS fetch returns an error / non-ok Telegram response:** Check that the token in `.env` is still valid. Telegram bot tokens occasionally get regenerated.

**`match_replies()` returns empty even though David replied:** The key in his reply must match the `"key"` field in `pending_actions.json` (case-insensitive, single word). If David typed "carter1" instead of "carter 1", it won't match — the format must be `"Word Number"`.

**Browser can't find the message box on FB/eBay:** Take a screenshot first to see the current state of the page. Log in if the session has expired.

**`/tmp/tg_updates.json` is stale from a previous run:** Always overwrite it in Step 3d before using it in later steps.
