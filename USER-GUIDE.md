# User Guide — How to Use resell-bot

This guide covers how to interact with the system day-to-day. For initial setup, see the [README](README.md).

---

## The Three Interfaces

You interact with resell-bot through three channels, each for different things:

| Interface | When to use it | Examples |
|---|---|---|
| **Telegram** (your phone) | Sending photos, quick instructions, replying to bot decisions | "Lower the vase price", "Carter 1", sending item photos |
| **Cowork** (Claude desktop app) | Scheduled runs, publishing listings, browser-based tasks | Morning run, followup run, posting to eBay/FB |
| **Claude Code** (terminal) | Changing how the bot works, debugging, manual scripts | Editing skills, fixing bugs, running `update_inventory.py` |

**Rule of thumb:** Use Telegram for anything you'd do from your phone. Use Cowork for anything that needs a browser. Use Claude Code for anything under the hood.

---

## Telegram — Your Daily Driver

The Telegram bot is your main touchpoint. A background service (`telegram_poll_bot.py`) watches for your messages 24/7 and routes them to the right place.

### Sending items to sell (batch mode)

You can send multiple items at once. Each distinct caption = one item.

1. Open the Telegram bot chat
2. Send photos of **Item A** with a caption (e.g. "Vintage desk lamp")
   - Send as an album (select multiple photos) — they'll group automatically
   - Only the first photo in an album needs the caption
3. Send photos of **Item B** with a different caption (e.g. "Nike Air Max 90")
4. Keep going — send as many items as you want
5. The bot shows you a running queue: *"I have 3 item(s) queued..."*
6. When you're done, reply **"go"**
7. One Claude session processes all items — researches comps, prices them, writes listing drafts, updates the inventory
8. You'll get Telegram updates as each item is priced

**Tips:**
- Include detail shots, labels, brand names, and any flaws
- If you send more photos of the **same item** later (before saying "go"), reply to the bot's queue message so it knows they're photo context, not a general instruction
- The bot is smart enough to merge items if it sees that separate batches are actually the same thing

### Sending instructions or notes

You can text the bot at any time — no photos needed.

```
"Lower the price on the vase to $50"
"Don't respond to Carter"
"Hold off on the Singer listing"
```

The bot replies: *"Got it — I'll pass that along to your next scheduled run."*

Your message is saved and the morning run picks it up as a standing instruction. It won't get lost.

### Replying to bot decisions

After the morning run, the bot sends you a summary with numbered options:

```
IMPORTANT — Carter asked about shipping on the Coffee Table
  1. "Shipping is $45 via FedEx Ground, delivery in 3-5 business days."
  2. "Local pickup only — I'm in the Portland area."
  3. Hold for now

Reply: Carter 1
```

Reply with the **key + number** (e.g. `Carter 1`). The followup run picks this up ~1 hour later and sends the reply to the buyer.

### Telegram command reference

| You send | What happens |
|---|---|
| Photos with caption | Queues a new item for research |
| Photos without caption | Added to the most recent item in the queue |
| `go` / `yes` / `list` / `do it` / `sell` / `post` | Triggers research for ALL queued items |
| `cancel` / `stop` / `no` | Cancels all queued items |
| `Carter 1` (key + number) | Replies to a pending buyer decision |
| Any other text | Saved as an instruction for the next scheduled run |

---

## Cowork — Scheduled Automation

Cowork runs two daily tasks automatically. You don't need to do anything — just make sure Chrome is open and logged into eBay/Facebook.

### Morning run (daily, e.g. 9:00 AM)

1. Checks for unprocessed photos in `photo-inbox/` (downloaded by the poll bot)
2. Reads your Telegram instructions from the last 24 hours
3. Publishes any items marked "ready" in the inventory
4. Checks all active eBay and Facebook listings for activity
5. Auto-replies to routine buyer questions ("Is this available?", dimensions, etc.)
6. Sends you a Telegram summary with anything needing your decision

### Followup run (daily, e.g. 10:00 AM)

1. Reads your Telegram replies (e.g. "Carter 1")
2. Matches them to pending actions from the morning run
3. Sends the chosen reply to the buyer in the browser
4. Confirms what was done via Telegram

### Running things manually in Cowork

You can trigger any skill on demand:

- **"Check my listings"** → runs the manage-listings skill
- **"Follow the create-listing skill"** → creates a listing from photos you've already sent
- **"Check my replies"** or **"Process pending actions"** → runs the followup skill
- **"Publish ready items"** → posts items marked "ready" in the inventory

---

## Claude Code — Under the Hood

Use Claude Code (the terminal CLI) for:

- **Editing bot behavior** — modifying skills, tweaking the poll bot, changing prompts
- **Debugging** — reading logs, checking why something failed
- **Manual inventory updates** — when you need precise control

### Common commands

```bash
# Check poll bot status
launchctl list | grep resellbot

# Restart the poll bot after code changes
launchctl stop com.resellbot.telegram-poll-bot
launchctl start com.resellbot.telegram-poll-bot

# Check poll bot logs
tail -f logs/poll-bot-stderr.log

# View research session logs
ls logs/research-*.log

# Manually add an item to inventory
source .venv/bin/activate
python3 scripts/update_inventory.py resell_inventory.xlsx add \
  --name "Item Name" --category "Category" --price-mid 75 \
  --status listed --marketplace "eBay"

# Mark an item sold
python3 scripts/update_inventory.py resell_inventory.xlsx update \
  --name "Item Name" --status sold --sold-price 350

# List active items
python3 scripts/update_inventory.py resell_inventory.xlsx list --status listed

# Test Telegram connection
python3 -c "from notifications.notifier import notify; notify('test')"
```

---

## Item Lifecycle

Here's how an item flows through the system:

```
You take photos on your phone
        ↓
Send to Telegram bot with caption (e.g. "Vintage lamp")
        ↓
Poll bot queues it — send more items or say "go"
        ↓
Claude researches comps, prices it, writes listing draft
        ↓
Item added to inventory as "ready"
        ↓
Morning run publishes it to eBay / FB Marketplace → status: "listed"
        ↓
Daily monitoring handles buyer questions automatically
        ↓
Important decisions sent to you via Telegram
        ↓
You reply (e.g. "Carter 1") → followup run sends the reply
        ↓
Item sells → status: "sold"
```

---

## What the Bot Will and Won't Do

**Handles automatically (no input needed):**
- "Is this still available?" replies
- Questions covered by the listing (dimensions, condition, shipping info)
- Inventory updates and status tracking

**Notifies you and waits for your decision:**
- Real offers (with a recommendation)
- Complex buyer questions
- Price change suggestions
- Anything involving money or commitments

**Never does (hard limits):**
- Accept or decline an offer
- Finalize a sale
- Change a listing price
- End or remove a listing
- Share your personal info (phone, address)
- Make pickup or meeting commitments

---

## Pricing Strategy

All items start at **Market Price** (median of comparable sold listings). If there's no interest after 1-2 weeks, the bot suggests lowering toward **Quick Sale** price. It never goes below the Quick Sale floor.

You can override this anytime via Telegram:
```
"Lower the lamp to $40"
"Price the shoes at $120"
```

The morning run picks up your instruction and applies it.

---

## Troubleshooting

**Photos not being picked up?**
Check if the poll bot is running: `launchctl list | grep resellbot`. If it's not running, restart it.

**Bot not responding to "go"?**
Make sure you have items queued (you should see the bot's queue summary). If the session expired (30 min timeout), resend your photos.

**Followup didn't send my reply?**
Check that `notifications/pending_actions.json` has pending items. Your reply format must be "Key Number" (e.g. "Carter 1") — no extra text.

**Morning run didn't apply my instruction?**
Instructions are read from `notifications/consumed_updates.json`. Check that the poll bot was running when you sent the message.

**"Got it — I'll pass that along" but nothing happened?**
Instructions are applied on the next **morning run**, not immediately. If you need something done now, use Cowork.
