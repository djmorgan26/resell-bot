---
name: resell
description: "AI-assisted workflow for selling personal items on online marketplaces like eBay and Facebook Marketplace. Use this skill whenever the user wants to sell items, create marketplace listings, price items for resale, research comparable sold prices, or manage their resale inventory. Also trigger when the user mentions 'list this', 'how much is this worth', 'sell this', 'marketplace listing', 'eBay listing', 'Facebook Marketplace', reselling, flipping, or shows photos of items they want to sell. This skill handles the full pipeline: photo analysis, item identification, market research, pricing, listing generation, and publishing assistance."
---

# Resell: AI-Assisted Marketplace Selling

You are helping the user sell personal items on online marketplaces. The goal is to make selling feel frictionless — from photo to published listing in minutes.

## Before You Start

Read `user-preferences.yaml` to check:
- **Pricing strategy** (speed vs. price optimization)
- **Shipping preferences** (local pickup only, or willing to ship)
- **Marketplace preferences** (which platforms to list on)
- **Category preferences** (any item types the user prefers or avoids)

If any **REQUIRED** preferences are missing (pricing strategy, shipping, marketplace), stop and ask the user to update `user-preferences.yaml` using the setup wizard before continuing.

## Overview

The workflow has 6 stages. You can start at any stage depending on what the user provides:

1. **Ingest photos** — Convert HEIC if needed, analyze images to identify the item
2. **Identify the item** — Determine brand, model, category, condition, and notable attributes
3. **Research the market** — Search for comparable listings and recently sold items
4. **Price the item** — Compute quick-sale, market, and optimistic price points
5. **Generate a listing** — Create optimized title, description, bullet points, and tags
6. **Publish** — Help post the listing via browser or provide pre-filled content

## Stage 1: Ingest Photos

If photos need organization, conversion (HEIC → JPEG), or deduplication, run `skills/organize-photos/SKILL.md` first.

Once photos are ready, use Claude's vision to look at every photo. Read each image file to examine it visually. Take note of:
- What the item is (broad category first, then specifics)
- Any visible brand names, logos, labels, model numbers, or serial numbers
- Condition indicators (scratches, wear, stains, missing parts)
- Size/scale clues (relative to other objects in frame)
- Any accessories, packaging, or extras included
- Distinguishing features that affect value (color, edition, material)

## Stage 2: Identify the Item

Based on the photos, build an item profile:

```
Item: [specific name]
Brand: [if identifiable]
Model: [if identifiable]
Category: [e.g., Musical Instruments > Guitars > Electric]
Condition: [New / Like New / Very Good / Good / Acceptable]
Notable attributes: [color, size, material, edition, included accessories]
Confidence: [High / Medium / Low — how sure are you about the identification]
```

If identification confidence is Low, tell the user what you see and ask them to confirm or provide more details. If Medium or High, proceed but note any uncertainty.

Use web search to verify your identification. Search for the brand + model to confirm specs and find the exact product page if possible.

## Stage 3: Research the Market

This is the most critical stage for setting accurate prices. Use multiple approaches:

### 3a. Search eBay sold listings
Use WebSearch to search for recently sold comparable items:
- Query: `[item name] [brand] [model] sold site:ebay.com`
- Also try: `[item name] [brand] [model] "sold" OR "ended" site:ebay.com`
- Look at the actual sold prices, not just asking prices

### 3b. Search active listings
- Query: `[item name] [brand] [model] site:ebay.com`
- Also check Facebook Marketplace if relevant: `[item name] [brand] [model] site:facebook.com/marketplace`

### 3c. Check price guides
- Query: `[item name] [brand] [model] price guide OR value OR worth`
- For vintage/collectible items, search for specific collector resources

### 3d. Use Claude in Chrome (if available)
If browser tools are available, navigate directly to:
- eBay Advanced Search → filter by "Sold Items" → sort by recent
- This gives the most accurate real-market data

Extract at minimum 5 comparable data points. For each, note:
- Sold price (or asking price if still active)
- Condition
- Date sold
- Any differences from the user's item
- Listing URL

## Stage 4: Price the Item

Using the comparable data, compute three price points:

| Tier | Description | How to calculate |
|------|-------------|------------------|
| **Quick sale** | Sell within 1-3 days | 10th-25th percentile of sold comps, adjusted for condition |
| **Market price** | Sell within 1-2 weeks | Median of sold comps, adjusted for condition |
| **Optimistic** | Might take weeks, or might not sell | 75th-90th percentile of sold comps |

Present the pricing like this:

```
Pricing recommendation for [item]:

  Quick sale:     $XX — sells fast, priced to move
  Market price:   $XX — fair market value, typical timeframe
  Optimistic:     $XX — top of market, may take longer

Based on [N] comparable sold listings ($XX - $XX range)
Condition adjustment: [explain if you adjusted for condition differences]
```

Always recommend which tier makes sense based on context (if the user wants to clear stuff out quickly vs maximize profit).

## Stage 5: Generate the Listing

Create listing drafts for the target marketplace(s). Check `config.yaml` → `marketplaces` to see which platforms the user sells on. **If both eBay and FB Marketplace are enabled, generate drafts for both** unless the item clearly doesn't fit one platform.

### Which items go where

| Item type | eBay | FB Marketplace | Why |
|---|---|---|---|
| Rugs, antiques, collectibles | Yes | Yes | eBay has national reach for niche buyers; FB gets local no-shipping sales |
| Furniture (large/heavy) | Maybe | Yes | Shipping cost kills eBay margins; FB is local pickup |
| Electronics, brand-name goods | Yes | Yes | Both work well |
| Cheap/bulky items (< $30) | No | Yes | eBay fees + shipping don't make sense |
| Rare/specialty items | Yes | Maybe | eBay's search brings niche collectors; FB is more casual |

When listing on both, note that **prices can differ** — FB Marketplace is typically 10-20% lower (no fees, local pickup, buyers expect deals). Set the eBay price at Market Price and the FB price slightly below.

### Shipping vs. Local Pickup

**Default to local pickup only** on all listings unless the user explicitly says otherwise. This applies to both eBay and FB Marketplace.

If an item would benefit from offering shipping (e.g. small, lightweight, rare/niche item that has few local buyers), **mention this to the user in conversation** explaining why before enabling shipping. Don't just add shipping on your own.

On eBay, set listings to "Local Pickup Only." On FB Marketplace, local pickup is already the default.

### Title (max 80 chars for eBay)
- Lead with brand/model
- Include key attributes (size, color, condition)
- Use searchable keywords buyers would actually type
- No ALL CAPS, no excessive punctuation

### Description
Write in this structure:

```
[Opening line — what it is and why it's desirable]

Key Details:
• Brand: [brand]
• Model: [model]
• Condition: [condition with specifics]
• [Other relevant attributes as bullet points]

[1-2 sentences about the item's history, features, or appeal]

[Shipping/packaging note]

[Any flaws or honest disclosures — being upfront builds trust and reduces returns]
```

### Metadata
- Suggested category path
- Suggested tags/item specifics
- Recommended shipping method and estimated cost
- Suggested listing duration (auction vs buy-it-now)

### Photos
Recommend which photos to use and in what order (lead with the best overall shot, then details, then any flaws).

## Item Folder Naming Convention

When saving photos to `items/` (or `photo-inbox/` before the listing is created), use this naming pattern:

```
[item-type]-[key-descriptor]-[size-or-id]
```

**Rules:**
- All lowercase, words separated by hyphens
- Max ~30 characters total — short enough to read at a glance
- Lead with the **item type** (rug, bag, vase, table, chair, lamp, etc.)
- Add 1-2 **key descriptors** that distinguish it (brand, style, origin, material)
- End with **dimensions or a unique ID** if it helps distinguish similar items

**Good examples:**
```
oriental-khorjin-saddle-bag-25x20    ← type: bag, descriptor: khorjin, size: 25x20
baluchi-flat-bag-27x29               ← type: bag, descriptor: baluchi flat, size
persian-pile-rug-medallion-29x35     ← type: rug, descriptor: persian pile medallion, size
ahmady-persian-rug-29x37             ← type: rug, descriptor: brand + origin, size
turkish-kilim-28x44                  ← type: rug, descriptor: kilim style, size
mashad-persian-rug-11x16             ← type: rug, descriptor: city + origin, size
chinese-flambe-glaze-vase-27in       ← type: vase, descriptor: style + glaze, height
stone-top-coffee-table-set           ← type: table, descriptor: material + form
paradigm-monitor-9-speakers          ← type: speakers, descriptor: brand + model
```

**Bad examples (avoid):**
```
oriental-rug-saddle-bag-each-side-is-25-x-20-12-there-are-po   ← too long, truncated
oriental-bag-27-x-29                                             ← "oriental" is too vague
oriental-37-12-x-56-12                                          ← no item type or descriptor
rug-30-12-x-57                                                   ← no descriptor at all
```

**When in doubt:** ask yourself "if I saw this folder name a month from now, would I know which item it is?" If yes, it's good.

---

## Stage 6: Publish

If the item should go on multiple marketplaces (see Stage 5 guidance), publish to **each one**. Create separate inventory entries or update the same entry with multiple listing URLs.

### Mode A: Browser-assisted (Claude in Chrome)
If browser tools are available:
1. Navigate to the first marketplace (eBay sell page or Facebook Marketplace create listing)
2. Fill in the listing form fields
3. Upload photos
4. Set the price (use marketplace-appropriate price — FB can be slightly lower)
5. Pause before final submission so the user can review
6. **Repeat for the second marketplace** if listing on both
7. Report results directly to the user: which marketplaces were posted to, and the listing URLs

**If Chrome issues occur:** Stop, describe the problem to the user in conversation, and ask for help before proceeding further.

### Mode B: Guided manual posting
If no browser access:
1. Provide all listing content formatted and ready to copy-paste
2. If listing on both platforms, provide **separate drafts** for each (titles/prices may differ)
3. List the photos to upload in order
4. Remind the user of any marketplace-specific settings (shipping, returns, etc.)
5. After the user confirms posting is complete, update the inventory tracker

## Inventory Management

Track all items in an inventory spreadsheet. After generating a listing, update the tracker with:
- Item name and description
- Photos location
- Price (recommended and actual listed price)
- Marketplace(s) listed on (e.g. "eBay, FB Marketplace" if both)
- Date listed
- Status (draft / listed / sold / expired)
- Listing URL(s) — if listed on both platforms, include both URLs

The inventory tracker lives at: `[workspace]/resell_inventory.xlsx`

Use the `scripts/update_inventory.py` script to add/update entries programmatically.

## Batch Processing

When the user has multiple items (like folders of photos for different items), process them efficiently:

1. Convert all photos first (batch HEIC conversion)
2. Analyze each item category
3. Research all items (can do web searches in parallel via subagents)
4. Present all pricing at once for the user to review
5. Generate all listings
6. Help publish one at a time (needs user approval for each)

## Issue Logging

If you encounter any problems during the listing creation process, log them to `logs/issues/create-listing.json` for tracking and review.

**Format:**
```json
{
  "timestamp": "2026-03-30T14:45:00Z",
  "type": "[research|pricing|description|publish|chrome|inventory|other]",
  "description": "what happened",
  "resolution": "what was done, or 'unresolved'",
  "item": "item folder name if applicable"
}
```

**Python snippet (use at any point in the skill):**
```python
import json
from datetime import datetime
from pathlib import Path

issues_file = Path("logs/issues/create-listing.json")
issues_file.parent.mkdir(parents=True, exist_ok=True)

# Read existing issues (or start with empty list)
try:
    with open(issues_file, "r") as f:
        issues = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    issues = []

# Append new issue
issues.append({
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "type": "chrome",
    "description": "eBay form fields not loading",
    "resolution": "unresolved",
    "item": "persian-pile-rug-29x35"
})

# Write back
with open(issues_file, "w") as f:
    json.dump(issues, f, indent=2)
```

---

## Tips for Different Item Types

**Electronics / Music Equipment**: Model number is everything. Search exact model numbers for best comps. Note if it powers on, includes original accessories, cables, etc.

**Art / Paintings**: Describe medium, dimensions, subject, frame condition. Note any signatures. Research the artist if signed. Art pricing is highly variable — provide wider ranges.

**Vintage / Antique items (Tiffany, etc.)**: Authentication matters enormously. Note any markings, stamps, or signatures. Search specialist auction houses (Sotheby's, Christie's) for high-end comps. Be transparent about inability to guarantee authenticity unless user has documentation.

**Sewing Machines**: Brand and model critical. Note if it's mechanical vs computerized, included feet/accessories, and whether it works. Vintage machines can be valuable to collectors.

**Clothing / Accessories**: Brand, size, material, condition, and era all matter. Include measurements for clothing.
