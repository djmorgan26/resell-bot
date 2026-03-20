---
name: photo-inbox
description: "Check Telegram for photos the user sent from their phone and download them into photo-inbox/. The poll bot (scripts/telegram_poll_bot.py) handles this automatically in real-time. This skill is a FALLBACK for when the poll bot isn't running. For scheduled runs, just check the filesystem for unprocessed photos instead."
---

# Photo Inbox — Telegram Photo Retrieval

> **NOTE:** The background poll bot (`scripts/telegram_poll_bot.py`) now handles real-time photo intake automatically. It downloads photos to `photo-inbox/<item>/`, groups them by caption, supports batch mode (multiple items → say "go" once), and spawns Claude research sessions. **For scheduled runs, do NOT use this skill** — just check the filesystem for unprocessed photo folders (see `skills/scheduled-runs/morning-run.md` Step 3).
>
> Use this skill only as a **manual fallback** when the poll bot isn't running.

The user sends photos of items they want to sell directly to the Telegram bot from their phone. Each message has one or more photos and a caption naming the item (e.g. "Kitchen mixer" or "Vintage lamp").

This skill checks for new photo messages, downloads them, and organizes them into `photo-inbox/<item-name>/` folders ready for the resell skill.

---

## When to Run

- **Only if the poll bot is NOT running** — check with `launchctl list | grep resellbot`
- **When the user says they sent photos** and the poll bot didn't pick them up
- **NOT during scheduled runs** — use filesystem check instead (morning-run.md Step 3)

---

## Prerequisites

1. Chrome must be active and connected (see CLAUDE.md "Fixing Chrome timeouts")
2. `notifications/.env` must have `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
3. The `photo-inbox/` directory must exist at the workspace root

---

## Step-by-Step Workflow (Cowork Sandbox)

All Telegram API calls go through Chrome JS because the sandbox proxy blocks Python HTTP to api.telegram.org.

### Step 0 — Read credentials

```bash
# Read the .env file to get TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
cat [WORKSPACE]/notifications/.env
```

Store the token and chat_id values for use in all Chrome JS calls below.

### Step 1 — Navigate to a neutral page

Before making fetch calls, navigate Chrome to a page without restrictive CSP headers:

```
navigate(url: "https://example.com", tabId: <TAB_ID>)
```

### Step 2 — Fetch getUpdates (find photo messages)

```javascript
// Run via mcp__Claude_in_Chrome__javascript_tool
(async () => {
  const token = '<TELEGRAM_BOT_TOKEN>';
  const chatId = '<TELEGRAM_CHAT_ID>';
  const resp = await fetch(`https://api.telegram.org/bot${token}/getUpdates?limit=100&timeout=5`);
  const data = await resp.json();
  if (!data.ok) return 'ERROR: ' + JSON.stringify(data);

  // Find messages with photos from the target chat
  const photos = data.result
    .map(u => u.message)
    .filter(m => m && m.photo && String(m.chat.id) === chatId && !(m.from || {}).is_bot)
    .map(m => ({
      caption: m.caption || '',
      file_id: m.photo[m.photo.length - 1].file_id,  // highest res
      file_unique_id: m.photo[m.photo.length - 1].file_unique_id,
      date: m.date,
      message_id: m.message_id,
      media_group_id: m.media_group_id || null,
    }));

  return JSON.stringify({ count: photos.length, photos });
})()
```

If `count` is 0, there are no new photos — you're done. Skip to the end.

### Step 3 — Filter out already-processed photos

Read `photo-inbox/processed.json` (if it exists) and remove any photos whose `file_unique_id` is already in the processed list.

```bash
cat [WORKSPACE]/photo-inbox/processed.json 2>/dev/null || echo '{"processed_ids":[]}'
```

Compare the `file_unique_id` values. Only proceed with photos not in the processed set.

### Step 4 — Get file paths for each new photo

For each new photo, call `getFile` to get the download URL:

```javascript
// Run via mcp__Claude_in_Chrome__javascript_tool
(async () => {
  const token = '<TELEGRAM_BOT_TOKEN>';
  const fileId = '<FILE_ID>';
  const resp = await fetch(`https://api.telegram.org/bot${token}/getFile?file_id=${fileId}`);
  const data = await resp.json();
  if (!data.ok) return 'ERROR: ' + JSON.stringify(data);
  return data.result.file_path;  // e.g. "photos/file_123.jpg"
})()
```

### Step 5 — Download each photo as base64

```javascript
// Run via mcp__Claude_in_Chrome__javascript_tool
(async () => {
  const token = '<TELEGRAM_BOT_TOKEN>';
  const filePath = '<FILE_PATH_FROM_STEP_4>';
  const resp = await fetch(`https://api.telegram.org/file/bot${token}/${filePath}`);
  const blob = await resp.blob();
  return new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.readAsDataURL(blob);
  });
})()
```

This returns a data URL like `data:image/jpeg;base64,/9j/4AAQ...`. Save the result.

### Step 6 — Save photos to disk

Use Python to decode and save:

```bash
source [WORKSPACE]/.venv/bin/activate
python3 - << 'PYEOF'
from notifications.photo_inbox import save_photo_from_base64, _sanitize_folder_name

# For each photo — repeat for all photos in the batch
base64_data = """<DATA_URL_FROM_STEP_5>"""
caption = "<CAPTION>"
item_folder = _sanitize_folder_name(caption) if caption else "item-YYYYMMDD-HHMM"

save_photo_from_base64(
    base64_data=base64_data,
    inbox_dir="[WORKSPACE]/photo-inbox",
    item_folder=item_folder,
    filename="photo-1.jpg",  # increment for multiple photos: photo-2.jpg, etc.
)
print(f"Saved to photo-inbox/{item_folder}/photo-1.jpg")
PYEOF
```

For albums (multiple photos with the same `media_group_id`), use the same `item_folder` and increment the filename number.

### Step 7 — Mark photos as processed

```bash
source [WORKSPACE]/.venv/bin/activate
python3 - << 'PYEOF'
from notifications.photo_inbox import mark_processed

items = [
    {"file_unique_id": "<ID_1>"},
    {"file_unique_id": "<ID_2>"},
    # ... all photos downloaded in this run
]

mark_processed("[WORKSPACE]/photo-inbox", items)
print("Marked", len(items), "photos as processed")
PYEOF
```

### Step 8 — Acknowledge updates (optional, prevents re-fetching)

```javascript
// Run via mcp__Claude_in_Chrome__javascript_tool
(async () => {
  const token = '<TELEGRAM_BOT_TOKEN>';
  const maxUpdateId = <HIGHEST_UPDATE_ID>;
  const resp = await fetch(`https://api.telegram.org/bot${token}/getUpdates?offset=${maxUpdateId + 1}&limit=1&timeout=1`);
  const data = await resp.json();
  return data.ok ? 'ACK OK' : 'ERROR: ' + JSON.stringify(data);
})()
```

---

## After Downloading — Hand Off to Resell Skill

Once photos are saved, for each new item folder in `photo-inbox/`:

1. Read and visually inspect all photos in the folder
2. Follow `skills/create-listing/SKILL.md` starting from **Stage 1: Ingest Photos**
3. The caption becomes the initial item name (refine during identification)
4. After listing is created, move the photos to `items/<item-name>/` for archival

---

## What to Do on Your Phone

Your workflow is just:

1. Take photos of the item
2. Open Telegram → the resell bot chat
3. Send photos with a caption like "Vintage desk lamp" or "KitchenAid mixer"
4. Done — Claude handles the rest on the next run

**Tips:**
- Send multiple photos as an album (select multiple in Telegram) — they'll be grouped automatically
- Put the item name in the caption of the FIRST photo — the rest can be blank
- Include detail shots, labels, any flaws
- If sending items separately, use a different caption for each item

---

## Folder Structure

```
photo-inbox/
├── processed.json              ← tracks which photos have been downloaded
├── persian-pile-rug-29x35/     ← one folder per item — see naming convention below
│   ├── photo-1.jpg
│   ├── photo-2.jpg
│   └── photo-3.jpg
├── baluchi-flat-bag-27x29/
│   ├── photo-1.jpg
│   └── photo-2.jpg
└── .gitkeep
```

Photos stay in `photo-inbox/` until the listing is created, then get moved to `items/<item-name>/`.

## Folder Naming Convention

Use the same naming pattern as `items/` — short, human-readable, no truncation:

```
[item-type]-[key-descriptor]-[size-or-id]
```

- All lowercase, hyphens between words, max ~30 characters
- Lead with item type, add 1-2 descriptors, end with dimensions or a unique ID
- The Telegram caption is the **starting point** — condense it into this format, don't use it verbatim

For example, if the caption is "Oriental Khorjin Saddle Bag Tribal Handwoven Wool Pair 25 x 20.5":
→ folder name: `oriental-khorjin-saddle-bag-25x20`

See `skills/create-listing/SKILL.md` → "Item Folder Naming Convention" for full examples and rules.
