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
python3 /path/to/resell-skill/scripts/convert_heic.py <input_dir> <output_dir>
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

Create a complete listing draft optimized for the target marketplace. The listing should follow these best practices:

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

Two modes depending on what's available:

### Mode A: Browser-assisted (Claude in Chrome)
If browser tools are available:
1. Navigate to the marketplace (eBay sell page, Facebook Marketplace create listing)
2. Fill in the listing form fields
3. Upload photos
4. Set the price
5. Pause before final submission so the user can review

### Mode B: Guided manual posting
If no browser access:
1. Provide all listing content formatted and ready to copy-paste
2. Give step-by-step instructions for the specific marketplace
3. List the photos to upload in order
4. Remind the user of any marketplace-specific settings (shipping, returns, etc.)

## Inventory Management

Track all items in an inventory spreadsheet. After generating a listing, update the tracker with:
- Item name and description
- Photos location
- Price (recommended and actual listed price)
- Marketplace(s) listed on
- Date listed
- Status (draft / listed / sold / expired)
- Listing URL

The inventory tracker lives at: `[workspace]/resell_inventory.xlsx`

Use the `resell-skill/scripts/update_inventory.py` script to add/update entries programmatically.

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
