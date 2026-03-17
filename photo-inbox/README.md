# photo-inbox/

**Staging area for new items waiting to be listed.**

Photos land here before a listing has been created. They get here two ways:
- **Automatically** — the user sends photos to the Telegram bot from their phone; the photo-inbox skill downloads them
- **Manually** — the user drops photos directly into a subfolder here

## Structure

One subfolder per item, named after the item:

```
photo-inbox/
├── kitchenaid-mixer/
│   ├── photo-1.jpg
│   └── photo-2.jpg
└── vintage-desk-lamp/
    ├── photo-1.jpg
    ├── photo-2.jpg
    └── photo-3.jpg
```

## If dropping photos in manually

Create a folder named after the item (lowercase, hyphens), drop the photos in, then tell Claude "there are new photos in the inbox."

## What happens next

Once a listing is created, photos move to `items/<item-name>/` for long-term storage and this folder is cleared.

`processed.json` tracks which Telegram photos have already been downloaded — don't delete it.
