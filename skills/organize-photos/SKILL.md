---
name: organize-photos
description: "Organize item photos into the resell-bot workspace. Use this skill when the user provides photos (uploaded, on their machine, or already in photo-inbox/), or when they want to audit/clean up existing photo folders. Handles: ingesting photos from any source, converting HEIC to JPEG, naming folders per convention, detecting duplicates, fixing misnamed or misplaced folders, and staging photos for listing creation. Trigger when the user mentions: organize photos, add photos, sort photos, fix photo folders, check for duplicates, or clean up items/photo-inbox."
---

# Organize Photos: Intake, Naming, Dedup & Cleanup

You help the user get item photos into the workspace in a clean, consistent state — ready for listing creation.

## Before You Start

1. Read `user-preferences.yaml` — check the `photos` section for naming, HEIC conversion, duplicate detection, and folder preferences.
2. Read `resell_inventory.xlsx` — know what items already exist so you can match incoming photos to existing items.

---

## What This Skill Does

| Task | When |
|------|------|
| **Ingest photos** | User uploads photos, points to a folder on their machine, or photos land in `photo-inbox/` |
| **Convert HEIC → JPEG** | iPhone photos arrive as .heic files |
| **Name folders** | Create properly named folders following the convention |
| **Detect duplicates** | Flag photos that look identical or near-identical within or across items |
| **Fix misnamed folders** | Find folders that don't follow naming convention and rename them |
| **Match to existing items** | If photos match an item already in inventory, add them to that item's folder instead of creating a new one |
| **Stage for listing** | Move organized photos from `photo-inbox/` to `items/` when ready |

---

## Photo Sources

The user can provide photos in several ways. Handle all of them:

### 1. Uploaded directly in conversation
- Save to `photo-inbox/<item-folder>/`
- If the user says what the item is, use that for the folder name
- If not, examine the photos and name the folder based on what you see

### 2. Path on the user's machine
- The user says "photos are at ~/Desktop/rug-pics" or similar
- Read the files from the provided path
- Copy them into `photo-inbox/<item-folder>/`

### 3. Already in photo-inbox/
- Check `photo-inbox/` for folders that haven't been processed yet
- Cross-reference against `resell_inventory.xlsx` — any folder not in the inventory is unprocessed

### 4. Already in items/
- The user asks to audit or clean up existing item folders

---

## Folder Naming Convention

Format: `[item-type]-[key-descriptor]-[size-or-id]`

**Rules:**
- All lowercase, words separated by hyphens
- Max ~30 characters — short enough to read at a glance
- Lead with **item type** (rug, bag, vase, table, speakers, etc.)
- Add 1-2 **key descriptors** (brand, style, origin, material)
- End with **dimensions or unique ID** if helpful

**Good examples:**
```
oriental-khorjin-bag-25x20
persian-pile-rug-29x35
marantz-av-receiver
stone-top-coffee-table-set
chinese-flambe-vase-27in
```

**Bad — avoid these patterns:**
```
oriental-rug-saddle-bag-each-side-is-25-x-20    ← too long
oriental-bag-27-x-29                              ← too vague
rug-30-12-x-57                                    ← no descriptor
IMG_4521                                          ← raw camera name
```

**Litmus test:** "If I saw this folder name a month from now, would I know which item it is?"

---

## HEIC Conversion

If `user-preferences.yaml → photos.convert_heic` is true (default):

```bash
source [WORKSPACE]/.venv/bin/activate
python3 [WORKSPACE]/scripts/convert_heic.py <input_dir> <output_dir>
```

The script converts all .heic to .jpeg, preserves EXIF orientation, and outputs web-ready images. After conversion, you can remove the .heic originals from the workspace (keep only .jpeg).

---

## Duplicate Detection

If `user-preferences.yaml → photos.detect_duplicates` is true (default):

### Within a single item folder
- Compare file sizes and dimensions
- Read each photo visually — flag any that show the exact same angle/framing
- If duplicates found, tell the user which ones look redundant and ask which to keep

### Across item folders
- When ingesting new photos, visually compare against existing items in `items/`
- If the new photos look like they belong to an existing item (same object, similar angles), flag it:
  > "These photos look like they might be additional shots of [existing-item]. Should I add them to that folder instead of creating a new item?"

### Photos that are clearly different items bundled together
- If a batch of photos contains multiple distinct items, split them into separate folders
- Ask the user to confirm the grouping if ambiguous

---

## Fixing Misnamed or Misplaced Folders

If `user-preferences.yaml → photos.fix_misnamed_folders` is true (default):

### On every run, scan for:

1. **Folders that don't follow naming convention:**
   - Too long (>30 chars)
   - Raw camera names (IMG_, DSC_, etc.)
   - No item type prefix
   - Spaces or underscores instead of hyphens
   - Suggest a corrected name and ask before renaming

2. **Photos in the wrong location:**
   - Loose photos in the repo root or unexpected directories
   - Photos in `items/` that aren't in any subfolder
   - Move them to `photo-inbox/unsorted/` and flag for the user

3. **Empty folders:**
   - Folders in `photo-inbox/` or `items/` with no photos
   - Flag for the user — may be leftovers from a deleted item

---

## Matching to Existing Inventory

Before creating a new item folder:

1. Read `resell_inventory.xlsx` — get all item names, categories, dimensions, and photo folder paths
2. Compare the new item against existing entries:
   - Dimensions match?
   - Description/caption similar?
   - Photos look like the same item?
3. If a match is found → add photos to the existing `items/<folder>/` directory
4. If no match → create a new folder in `photo-inbox/`

---

## Staging Workflow

```
User provides photos
        ↓
photo-inbox/<item-folder>/    ← temporary staging
        ↓
    [organize, name, dedup]
        ↓
items/<item-folder>/          ← permanent home (after listing created)
```

Photos stay in `photo-inbox/` until the create-listing skill processes them. After a listing is created, they move to `items/`.

---

## Issue Logging

If anything goes wrong or seems off during photo organization, log it:

```bash
source [WORKSPACE]/.venv/bin/activate
python3 - << 'EOF'
import json
from pathlib import Path
from datetime import datetime

log_path = Path("[WORKSPACE]/logs/issues/organize-photos.json")
existing = json.loads(log_path.read_text()) if log_path.exists() else []
existing.append({
    "timestamp": datetime.now().isoformat(),
    "type": "[naming|duplicate|conversion|misplaced|other]",
    "description": "[what happened]",
    "resolution": "[what was done, or 'unresolved']",
    "item": "[item folder name if applicable]"
})
log_path.write_text(json.dumps(existing, indent=2))
EOF
```

---

## What NOT To Do

- Don't delete photos without asking the user first
- Don't rename folders without confirming with the user
- Don't assume photos are for a new item if they match an existing one — ask
- Don't skip HEIC conversion — marketplace sites need JPEG/PNG
