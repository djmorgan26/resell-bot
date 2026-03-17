---
name: setup
description: "First-time setup for resell-bot. Walk a new user through complete configuration: creating config.yaml, setting up a Telegram bot, connecting Chrome to eBay and Facebook Marketplace, creating their inventory file, and scheduling the daily runs. Use this when someone has just cloned the repo and needs to get everything working."
---

# resell-bot First-Time Setup

This skill guides a new user through everything needed to get resell-bot running on their machine. Work through each stage in order. At the end, the user will have a fully configured, scheduled resell bot.

---

## Before you begin

Check whether setup has already been done:

```bash
ls [WORKSPACE]/config.yaml 2>/dev/null && echo "EXISTS" || echo "MISSING"
ls [WORKSPACE]/notifications/.env 2>/dev/null && echo "EXISTS" || echo "MISSING"
ls [WORKSPACE]/resell_inventory.xlsx 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

- If all three exist, setup is done — verify with a test notification (Stage 4) and skip to Stage 5.
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
[WORKSPACE]/.venv/bin/python3 -c "import openpyxl, yaml, dotenv; print('OK')"
```

---

## Stage 2 — Run the setup wizard

```bash
cd [WORKSPACE] && source .venv/bin/activate && python3 setup.py
```

The wizard handles everything interactively:
1. Asks the user's name, eBay username, marketplace preferences
2. Guides them through creating a Telegram bot via @BotFather
3. Helps them find their Telegram chat ID
4. Writes `config.yaml` and `notifications/.env`
5. Creates `resell_inventory.xlsx` from the template
6. Sends a test Telegram message to verify everything works

**If the user is running this in Cowork (not a terminal):** Walk through each step yourself instead of running the script, since Cowork may not support interactive terminal input. Follow the same steps manually:

### Manual Stage 2A — Create config.yaml

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

### Manual Stage 2B — Create Telegram bot

Tell the user:

> "We need to create a Telegram bot that will send you notifications and receive your replies.
>
> 1. Open Telegram on your phone
> 2. Search for @BotFather and tap Start
> 3. Send: /newbot
> 4. Follow the prompts — pick any name and username (username must end in 'bot')
> 5. BotFather will give you a token like: 1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk
> 6. Paste that token here."

Once you have the token, help them find their chat ID:

> "Now open a chat with your new bot in Telegram and send it any message (like 'hello').
> Then open this URL in your browser (replace TOKEN with your actual token):
> https://api.telegram.org/botTOKEN/getUpdates
> Look for 'chat':{'id': — that number is your chat ID. Paste it here."

Write `[WORKSPACE]/notifications/.env`:
```
TELEGRAM_BOT_TOKEN=[their token]
TELEGRAM_CHAT_ID=[their chat id]
```

### Manual Stage 2C — Create inventory file

```bash
cp [WORKSPACE]/resell_inventory_template.xlsx [WORKSPACE]/resell_inventory.xlsx
```

---

## Stage 3 — Verify Telegram

Send a test message via Chrome JS (works in Cowork sandbox):

```javascript
// Navigate to example.com first (avoids CSP issues), then run:
(async () => {
  const token = '[TELEGRAM_BOT_TOKEN from .env]';
  const chatId = '[TELEGRAM_CHAT_ID from .env]';
  const resp = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text: '🤖 resell-bot setup complete! Your bot is connected.' })
  });
  const data = await resp.json();
  return data.ok ? 'SENT OK' : 'ERROR: ' + JSON.stringify(data);
})()
```

If this fails:
- Double-check the token (copy-paste carefully — no extra spaces)
- Make sure the user sent at least one message to the bot before trying getUpdates
- Try the token at: https://api.telegram.org/botTOKEN/getMe — should return the bot's info

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

## Stage 5 — Set up scheduled tasks

Two tasks power the daily automation. In Cowork's Schedule feature:

**Task 1: Morning run**
- Name: `morning-run`
- Schedule: `0 9 * * *` (9:00 AM daily)
- Prompt: paste the full contents of `[WORKSPACE]/schedule-prompts/morning.txt`

**Task 2: Follow-up run**
- Name: `followup-run`
- Schedule: `0 10 * * *` (10:00 AM daily)
- Prompt: paste the full contents of `[WORKSPACE]/schedule-prompts/followup.txt`

Adjust the times to whatever works for the user's timezone and routine.

---

## Stage 6 — First listing (optional)

If the user has items to sell right now, offer to create their first listing:

> "Would you like to add your first item now? If you have photos ready, I can help you research pricing, write a description, and get it posted."

If yes, follow `[WORKSPACE]/skills/create-listing/SKILL.md`.

---

## Stage 7 — Summary

When all stages are complete, summarize what's been set up:

- `config.yaml` — your personal settings
- `notifications/.env` — your Telegram bot credentials
- `resell_inventory.xlsx` — your inventory spreadsheet (currently empty, add items as you list them)
- Chrome logged in to: [list marketplaces they use]
- Scheduled tasks: morning run at [time], follow-up at [time]

> "You're all set! Every morning at [time], I'll check your listings, reply to routine buyer messages, and send you a Telegram summary. If you want to list a new item, send me photos on Telegram from your phone or just ask me to start the create-listing skill."
