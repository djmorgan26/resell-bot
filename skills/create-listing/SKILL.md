---
name: resell
description: "AI-assisted workflow for selling personal items on online marketplaces like eBay and Facebook Marketplace. Use this skill whenever the user wants to sell items, create marketplace listings, price items for resale, research comparable sold prices, or manage their resale inventory. Also trigger when the user mentions 'list this', 'how much is this worth', 'sell this', 'marketplace listing', 'eBay listing', 'Facebook Marketplace', reselling, flipping, or shows photos of items they want to sell. This skill handles the full pipeline: photo analysis, item identification, market research, pricing, listing generation, and publishing assistance."
---

# Resell: AI-Assisted Marketplace Selling

You are helping the user sell personal items on online marketplaces. The goal is to make selling feel frictionless — from photo to published listing in minutes.

## Overview

The workflow has 6 stages. You can start at any stage depending on what the user provides:

1. **Ingest photos** — Convert HEIC if needed, analyze images to identify the item
2. **Identify the item** — Determine brand, model, category, condition, and notable attributes
3. **Research the market** — Search for comparable listings and recently sold items
4. **Price the item** — Compute quick-sale, market, and optimistic price points
5. **Generate a listing** — Create optimized title, description, bullet points, and tags
6. **Publish** — Help post the listing via browser or provide pre-filled content

## Stage 1: Ingest Photos

If photos are HEIC format, convert them to JPEG first:

```bash
python3 [WORKSPACE]/scripts/convert_heic.py <input_dir> <output_dir>
```

The script converts all .heic files to .jpeg while preserving quality. The output directory will contain web-ready images.

Then use Claude's vision to look at every photo. Read each image file to examine it visually. Take note of:
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

If an item would benefit from offering shipping (e.g. small, lightweight, rare/niche item that has few local buyers), **notify the user via Telegram first** explaining why before enabling shipping. Don't just add shipping on your own.

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

## Stage 6: Publish

If the item should go on multiple marketplaces (see Stage 5 guidance), publish to **each one**. Create separate inventory entries or update the same entry with multiple listing URLs.

Two modes depending on what's available:

### Mode A: Browser-assisted (Claude in Chrome)
If browser tools are available:
1. Navigate to the first marketplace (eBay sell page or Facebook Marketplace create listing)
2. Fill in the listing form fields
3. Upload photos
4. Set the price (use marketplace-appropriate price — FB can be slightly lower)
5. Pause before final submission so the user can review
6. **Repeat for the second marketplace** if listing on both

### Mode B: Guided manual posting
If no browser access:
1. Provide all listing content formatted and ready to copy-paste
2. If listing on both platforms, provide **separate drafts** for each (titles/prices may differ)
3. List the photos to upload in order
4. Remind the user of any marketplace-specific settings (shipping, returns, etc.)

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

## Tips for Different Item Types

**Electronics / Music Equipment**: Model number is everything. Search exact model numbers for best comps. Note if it powers on, includes original accessories, cables, etc.

**Art / Paintings**: Describe medium, dimensions, subject, frame condition. Note any signatures. Research the artist if signed. Art pricing is highly variable — provide wider ranges.

**Vintage / Antique items (Tiffany, etc.)**: Authentication matters enormously. Note any markings, stamps, or signatures. Search specialist auction houses (Sotheby's, Christie's) for high-end comps. Be transparent about inability to guarantee authenticity unless user has documentation.

**Sewing Machines**: Brand and model critical. Note if it's mechanical vs computerized, included feet/accessories, and whether it works. Vintage machines can be valuable to collectors.

**Clothing / Accessories**: Brand, size, material, condition, and era all matter. Include measurements for clothing.
