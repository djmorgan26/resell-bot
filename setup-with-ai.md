# Set up resell-bot with an AI assistant

If you'd rather be guided through setup conversationally than run the terminal wizard, paste this entire document into any AI assistant (Claude, ChatGPT, Gemini, etc.) and say: **"Please walk me through this setup guide step by step."**

The AI will ask you questions one at a time and tell you exactly what to do at each step.

---

## Instructions for the AI assistant

You are helping a user set up resell-bot on their computer. This is an automated reselling tool that monitors eBay and Facebook Marketplace listings and sends Telegram notifications.

Walk through each stage below **one at a time**. After each step, wait for the user to confirm before moving on. Use plain language — assume the user is not technical. If something fails, help them troubleshoot before continuing.

By the end, the user should have:
- `config.yaml` — their personal settings
- `notifications/.env` — their Telegram bot credentials
- `resell_inventory.xlsx` — their inventory spreadsheet
- A verified Telegram connection (test message received)

---

## Stage 1 — Collect user info

Ask the user these questions (one at a time, not all at once):

1. "What's your first name? This is just used in notifications."
2. "Do you sell on eBay? If yes, what's your eBay seller username?"
3. "Do you also sell on Facebook Marketplace?"
4. "When you sell something, is your main goal to sell it quickly, or to get the highest possible price?"

Once you have their answers, create the file `config.yaml` in the resell-bot folder:

```yaml
user:
  name: "[their name]"

selling:
  ebay_username: "[their eBay username, or leave blank]"
  priority: "speed"   # change to "price" if they want to maximize profit

marketplaces:
  - "ebay"            # remove this line if they don't use eBay
  - "fb_marketplace"  # remove this line if they don't use Facebook Marketplace
```

Tell the user: "I've created your config.yaml. Let me know when you're ready to set up Telegram."

---

## Stage 2 — Create a Telegram bot

Tell the user:

> "We need to create a Telegram bot. This is what will send you notifications and receive your replies. It only takes about 2 minutes."

Walk through these steps with them:

**Step A — Create the bot:**
> "Open Telegram on your phone or computer. Search for a contact called **@BotFather** — it has a blue checkmark. Start a chat with it.
>
> Send BotFather this message: `/newbot`
>
> It will ask you for a name (this is the display name, like 'My Resell Bot') and then a username (this must end in the word 'bot', like 'myresellbot'). Pick whatever you like.
>
> After you set the username, BotFather will send you a **token** — a long string of letters and numbers that looks like: `1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk`
>
> Copy that token and paste it here."

Wait for the token. Validate it looks right (should contain a colon, be ~46 characters total).

**Step B — Get the chat ID:**
> "Now open a chat with the bot you just created (search for its username in Telegram) and send it any message — just type 'hello' and send it.
>
> Then open this link in your browser. Replace the word TOKEN with your actual token:
> `https://api.telegram.org/botTOKEN/getUpdates`
>
> You'll see some JSON text. Look for the part that says `'chat':{'id':` — the number right after that is your chat ID. It might be a positive number like `123456789` or a negative number like `-100123456789`. Either is normal.
>
> Paste your chat ID here."

Wait for the chat ID.

**Step C — Write the credentials file:**

Create the file `notifications/.env` in the resell-bot folder:

```
TELEGRAM_BOT_TOKEN=[their token]
TELEGRAM_CHAT_ID=[their chat id]
```

Tell the user: "I've saved your Telegram credentials. Now let's verify they work."

---

## Stage 3 — Verify Telegram is working

Ask the user to run this command in their terminal (from the resell-bot folder):

```bash
source .venv/bin/activate
python3 -c "from notifications.notifier import notify; notify('resell-bot test — setup is working!')"
```

Tell them: "Check your Telegram app — you should receive a message from your bot within a few seconds."

**If it works:** "Great! Telegram is connected."

**If it fails:** Help them troubleshoot:
- Check that `notifications/.env` exists and the token/chat ID are correct (no extra spaces)
- Make sure they sent a message to the bot before running getUpdates (Telegram won't show a chat ID until the user has messaged the bot first)
- Try opening `https://api.telegram.org/botTOKEN/getMe` — if it returns the bot's info, the token is valid

---

## Stage 4 — Set up the inventory spreadsheet

Ask the user to run this command:

```bash
cp resell_inventory_template.xlsx resell_inventory.xlsx
```

Tell them: "This creates your inventory spreadsheet. You'll add items to it as you list them — either by running the daily listing check or using the add command."

If they want to add their first item manually right now, they can:

```bash
source .venv/bin/activate
python3 scripts/update_inventory.py resell_inventory.xlsx add \
  --name "Item Name" --category "Electronics" --price-mid 75 \
  --status listed --marketplace "FB Marketplace" \
  --listing-url "https://..."
```

---

## Stage 5 — What's next

Tell the user:

> "You're all set! Here's a summary of what we configured:
>
> - **config.yaml** — your name, eBay username, and selling preferences
> - **notifications/.env** — your Telegram bot credentials
> - **resell_inventory.xlsx** — your inventory spreadsheet
>
> **Next steps:**
> 1. Open Chrome and log in to eBay and/or Facebook Marketplace
> 2. Open Claude (Cowork) and select the resell-bot folder as your workspace
> 3. To start the daily automation, follow `skills/scheduled-runs/morning-run.md`
> 4. To create your first listing, follow `skills/create-listing/SKILL.md`
>
> Every morning your bot will check your listings, handle routine buyer messages, and send you a Telegram summary. Anything that needs your decision — offers, sales, hard questions — will come through as a notification with reply options."
