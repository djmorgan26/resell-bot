---
name: followup-listings
description: "Act on the user's Telegram replies to pending listing decisions. Use this skill whenever running the follow-up scheduled task — it reads the user's recent Telegram messages, matches them to any pending actions from the morning monitoring run, sends the appropriate buyer replies in the browser, resolves handled items, and confirms back to the user via Telegram. Trigger when the scheduled follow-up task runs, or when the user says 'check my replies', 'did I respond', 'act on my telegram replies', or 'process pending actions'."
---

# Follow-Up: Act on Telegram Replies

You are the follow-up half of the user's resell bot. The morning monitoring run checks listings and sends the user a Telegram summary with numbered reply options for anything needing theirdecision. This skill picks up where that left off: reads theirreplies, executes the chosen actions in the browser, and confirms what was done.

## How the Two-Run Flow Works

```
Morning run  → checks listings, sends Telegram with 🔔 IMPORTANT + numbered options
             → writes notifications/pending_actions.json

the user (phone) → replies in Telegram: "Carter 1"

This skill  → reads the user's Telegram replies via Chrome JS (EXIT if none)
(1hr later)  → reads pending_actions.json to find what each reply maps to
             → if pending is empty but the user replied → alert the user (don't silently exit)
             → matches "Carter 1" to the reply text for option 1
             → opens the FB/eBay thread, sends the reply
             → resolves the item from pending_actions.json
             → acknowledges Telegram (ONLY after acting — never before)
             → sends Telegram confirmation
```

**Critical rule:** Never acknowledge Telegram updates until after the replies have been sent in the browser. If something fails mid-run, the user's messages stay in the Telegram queue and will be picked up on the next run.

---

## Step 1 — Find the Workspace

```bash
find /sessions -name "resell_inventory.xlsx" 2>/dev/null | head -1 | xargs dirname
```

Store this path as WORKSPACE for all subsequent steps.

---

## Step 2 — Fetch the user's Recent Telegram Replies

**Do this first — before checking pending_actions.json.** the user's replies must be read before anything else.

The Telegram poll bot (`scripts/telegram_poll_bot.py`) runs as a background service and is the **single consumer** of all Telegram updates. It saves every update it receives to `notifications/consumed_updates.json`. Read replies from that file — do NOT call `getUpdates` directly (the poll bot has already consumed those updates).

**2a.** Read the user's recent messages from the consumed updates file:

```bash
source [WORKSPACE]/.venv/bin/activate
python3 - << 'EOF'
import json, sys, os
from dotenv import load_dotenv
sys.path.insert(0, '[WORKSPACE]')
load_dotenv('[WORKSPACE]/notifications/.env')
from notifications.telegram_reader import get_consumed_messages
msgs = get_consumed_messages(hours=6)
print(json.dumps(msgs, default=str))
EOF
```

**2b.** If the consumed_updates.json file doesn't exist or the output is `[]`, fall back to Chrome JS as a backup (the poll bot may not be running):

Read `TELEGRAM_BOT_TOKEN` from `[WORKSPACE]/notifications/.env`, navigate Chrome to `https://example.com`, then run:

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

Then parse with:

```bash
source [WORKSPACE]/.venv/bin/activate
python3 - << 'EOF'
import json, sys, os
from dotenv import load_dotenv
sys.path.insert(0, '[WORKSPACE]')
load_dotenv('[WORKSPACE]/notifications/.env')
from notifications.telegram_reader import parse_updates_response
raw = '<JSON_STRING>'
chat_id = os.getenv('TELEGRAM_CHAT_ID')
msgs = parse_updates_response(raw, hours=6, chat_id=chat_id)
print(json.dumps(msgs, default=str))
EOF
```

If the output is `[]` → **stop here**. the user hasn't replied yet. Exit cleanly with no Telegram message.

Store the parsed list as MESSAGES.

---

## Step 3 — Check Pending Actions

Now read `[WORKSPACE]/notifications/pending_actions.json`.

- If `"pending"` has items → proceed to Step 4 (matching).
- If `"pending"` is **empty but MESSAGES is non-empty** → the user replied to something but `pending_actions.json` has no context. **Do not silently exit.** Send the user a Telegram message: `"⚠️ Got your reply but no pending actions on file — the morning run may not have completed. Running a fresh check now."` Then trigger the manage-listings skill to re-run.
- If both are empty → exit cleanly with no Telegram message.

---

## Step 4 — Match Replies to Pending Actions

the user's reply format is: `"Carter 1"`, `"Carter: 2"`, etc. — a key (usually a buyer's first name) plus an option number.

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

If the output is `[]` → the user replied but the format didn't match any pending key (e.g. typo). Send the user a Telegram message: `"⚠️ Couldn't match your reply to any pending action. Pending keys: [list keys from pending_actions.json]. Reply format: 'Key Number' (e.g. 'Carter 1')."` Then exit.

Store the result as MATCHED.

---

## Step 5 — Send Replies in the Browser

For each item in MATCHED:

**a.** Check `action["reply_text"]`:
- If it's `"__HOLD__"` → skip entirely. the user chose to wait on this one.
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
source [WORKSPACE]/.venv/bin/activate
python3 - << 'EOF'
import sys, os
from dotenv import load_dotenv
sys.path.insert(0, '[WORKSPACE]')
load_dotenv('[WORKSPACE]/notifications/.env')
from notifications.telegram_reader import parse_updates_response
from notifications.reply_handler import match_replies, resolve_actions

chat_id = os.getenv('TELEGRAM_CHAT_ID')
msgs = parse_updates_response(open('/tmp/tg_updates.json').read(), hours=6, chat_id=chat_id)
matched = match_replies(msgs)
resolved_keys = [m["action"]["key"] for m in matched if m["reply_text"] != "__HOLD__"]
if resolved_keys:
    resolve_actions(resolved_keys)
    print("Resolved:", resolved_keys)
EOF
```

**6b.** Telegram acknowledgment is handled automatically by the poll bot — no manual acknowledgment step needed. The consumed_updates.json file retains messages for 24 hours, so failed runs can retry on the next cycle.

---

## Step 7 — Update the Inventory

For each item in MATCHED where a real reply was sent (not `__HOLD__`), update `resell_inventory.xlsx` with a note:

```bash
python3 [WORKSPACE]/scripts/update_inventory.py [WORKSPACE]/resell_inventory.xlsx \
  update --name "Item Name" \
  --notes "Reply sent to [buyer] [date]: '[first 60 chars of reply]...'"
```

Use today's date in the note. This keeps the inventory in sync with what was actually communicated to buyers.

---

## Step 8 — Send Telegram Confirmation

Navigate Chrome to `https://example.com`, then send a confirmation message following the instructions in `[WORKSPACE]/skills/send-summary/SKILL.md` (Chrome JS fetch method — the same one used for outbound messages in the morning run).

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

- Never accept or decline an offer on the user's behalf — if an action in `pending_actions.json` looks like an offer acceptance, flag it and ask the user directly.
- Never change a listing price.
- Never share the user's personal info (phone, address) in any reply.
- Never make pickup/meeting commitments.
- Never send a message that wasn't explicitly pre-approved by the user via theirnumbered reply.

---

## Troubleshooting

**Bot can't see the user's messages in the group chat:** The bot's Privacy Mode must be OFF. Check with the `getMe` API — `can_read_all_group_messages` must be `true`. If it's `false`, go to @BotFather → `/mybots` → select the bot → Bot Settings → Group Privacy → Turn off. **The bot must also be removed and re-added to the group after changing this setting** for it to take effect.

**Chrome JS fetch returns an error / non-ok Telegram response:** Check that the token in `.env` is still valid. Telegram bot tokens occasionally get regenerated.

**`match_replies()` returns empty even though the user replied:** The key in theirreply must match the `"key"` field in `pending_actions.json` (case-insensitive, single word). If the user typed "carter1" instead of "carter 1", it won't match — the format must be `"Word Number"`.

**Browser can't find the message box on FB/eBay:** Take a screenshot first to see the current state of the page. Log in if the session has expired.

**`/tmp/tg_updates.json` is stale from a previous run:** Always overwrite it in Step 2d before using it in later steps.

**Messages showing up from personal chat instead of group:** The `parse_updates_response` function accepts a `chat_id` parameter — always pass `TELEGRAM_CHAT_ID` from `.env` to filter to the group chat only. Without this, the bot reads messages from ALL chats including DMs.
