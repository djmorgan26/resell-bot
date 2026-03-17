#!/usr/bin/env python3
"""
photo_inbox.py — polls Telegram for photos sent by the user and downloads them.

The user sends photos to the Telegram bot from their phone with a caption describing
the item (e.g. "Kitchen mixer" or "Vintage lamp"). This module finds those photo
messages, downloads the highest-resolution version, and saves them into per-item
folders under photo-inbox/.

COWORK SANDBOX NOTE:
  Python cannot reach api.telegram.org in the Cowork VM. All three API calls
  (getUpdates, getFile, file download) must be made via Chrome JS and the results
  passed to the parsing/saving functions here.

  See photo-inbox-skill/SKILL.md for the full Chrome JS workflow.

Outside the sandbox (local dev), use fetch_and_save_photos() directly.

Usage (Cowork — Chrome JS orchestration):
    from notifications.photo_inbox import (
        parse_photo_updates,
        save_photo_from_base64,
        load_processed,
        mark_processed,
    )

    # 1. Fetch getUpdates via Chrome JS, pass raw JSON here
    items = parse_photo_updates(raw_json, hours=48)

    # 2. For each photo, fetch via Chrome JS, save the base64 result
    for item in items:
        save_photo_from_base64(base64_data, inbox_dir, item)

    # 3. Mark as processed so we don't re-download next run
    mark_processed(inbox_dir, items)

Usage (local/non-sandbox):
    from notifications.photo_inbox import fetch_and_save_photos
    new_items = fetch_and_save_photos("./photo-inbox", hours=48)
"""

import base64
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)

# ─── Processed-photo tracking ───────────────────────────────────────────────

PROCESSED_FILE = "processed.json"


def load_processed(inbox_dir: str | Path) -> set[str]:
    """Load the set of already-processed file_unique_ids."""
    path = Path(inbox_dir) / PROCESSED_FILE
    if path.exists():
        data = json.loads(path.read_text())
        return set(data.get("processed_ids", []))
    return set()


def mark_processed(inbox_dir: str | Path, items: list[dict]) -> None:
    """Add items to the processed set so they aren't re-downloaded."""
    path = Path(inbox_dir) / PROCESSED_FILE
    existing = load_processed(inbox_dir)
    for item in items:
        existing.add(item["file_unique_id"])
    data = {
        "processed_ids": sorted(existing),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2))


# ─── Parse photo messages from getUpdates response ──────────────────────────

def parse_photo_updates(
    raw_json: str | dict,
    hours: float = 48.0,
    chat_id: str | int | None = None,
) -> list[dict]:
    """
    Extract photo messages from a Telegram getUpdates response.

    Args:
        raw_json: Raw JSON string (or dict) from Telegram getUpdates API.
        hours: Only return photos from the last N hours.
        chat_id: If provided, only return photos from this chat.

    Returns list of dicts:
        - caption (str): message caption (item name), or "" if none
        - file_id (str): Telegram file_id for the highest-res photo
        - file_unique_id (str): stable ID for deduplication
        - timestamp (datetime): when the message was sent
        - update_id (int): for acknowledgement
        - message_id (int): Telegram message ID
        - media_group_id (str|None): groups multiple photos from one message
    """
    data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json

    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    target_chat_id = str(chat_id) if chat_id is not None else None
    photos = []

    for update in data.get("result", []):
        msg = update.get("message") or update.get("channel_post")
        if not msg:
            continue

        # Must have a photo
        if "photo" not in msg:
            continue

        # Filter by chat
        msg_chat_id = str(msg.get("chat", {}).get("id", ""))
        if target_chat_id and msg_chat_id != target_chat_id:
            continue

        # Skip bot messages
        from_info = msg.get("from") or {}
        if from_info.get("is_bot"):
            continue

        # Filter by recency
        ts = datetime.fromtimestamp(msg["date"], tz=timezone.utc)
        if ts < cutoff:
            continue

        # Pick highest resolution (last element in photo array)
        best_photo = msg["photo"][-1]

        photos.append({
            "caption": (msg.get("caption") or "").strip(),
            "file_id": best_photo["file_id"],
            "file_unique_id": best_photo["file_unique_id"],
            "width": best_photo.get("width"),
            "height": best_photo.get("height"),
            "timestamp": ts,
            "update_id": update["update_id"],
            "message_id": msg["message_id"],
            "media_group_id": msg.get("media_group_id"),
        })

    return photos


# ─── Group photos by item (caption or media_group_id) ───────────────────────

def group_photos_by_item(photos: list[dict]) -> dict[str, list[dict]]:
    """
    Group photos into items. Photos with the same media_group_id (sent as an
    album) belong together. Otherwise, group by caption text.

    Returns: {item_name: [photo_dicts]}
    """
    groups: dict[str, list[dict]] = {}
    media_group_names: dict[str, str] = {}

    for photo in photos:
        mg_id = photo.get("media_group_id")

        if mg_id:
            # Album — use the first caption we find for the group name
            if mg_id not in media_group_names:
                name = photo["caption"] or f"item-{photo['timestamp'].strftime('%Y%m%d-%H%M')}"
                media_group_names[mg_id] = _sanitize_folder_name(name)
            folder = media_group_names[mg_id]
        else:
            # Single photo
            name = photo["caption"] or f"item-{photo['timestamp'].strftime('%Y%m%d-%H%M')}"
            folder = _sanitize_folder_name(name)

        groups.setdefault(folder, []).append(photo)

    return groups


def _sanitize_folder_name(name: str) -> str:
    """Turn a caption into a safe folder name."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "-", name)
    return name[:60] or "unnamed-item"


# ─── Save a photo from base64 data ──────────────────────────────────────────

def save_photo_from_base64(
    base64_data: str,
    inbox_dir: str | Path,
    item_folder: str,
    filename: str,
) -> Path:
    """
    Decode base64 photo data and save to inbox_dir/item_folder/filename.

    Args:
        base64_data: Base64-encoded image data (with or without data: URL prefix).
        inbox_dir: Root photo-inbox directory.
        item_folder: Subfolder name for this item.
        filename: Output filename (e.g. "photo-1.jpg").

    Returns: Path to the saved file.
    """
    inbox = Path(inbox_dir)
    folder = inbox / item_folder
    folder.mkdir(parents=True, exist_ok=True)

    # Strip data URL prefix if present (e.g. "data:image/jpeg;base64,...")
    if "," in base64_data[:100]:
        base64_data = base64_data.split(",", 1)[1]

    img_bytes = base64.b64decode(base64_data)
    out_path = folder / filename
    out_path.write_bytes(img_bytes)
    return out_path


# ─── Direct Python fetch (non-sandbox only) ─────────────────────────────────

def fetch_and_save_photos(
    inbox_dir: str | Path,
    hours: float = 48.0,
) -> dict[str, list[Path]]:
    """
    Poll Telegram for new photos and save them to inbox_dir.

    NOTE: This will fail in the Cowork sandbox VM.
    Use the Chrome JS workflow for scheduled runs instead.

    Returns: {item_folder_name: [saved_file_paths]}
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in notifications/.env")

    session = requests.Session()
    session.trust_env = False

    # 1. Get updates
    resp = session.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params={"limit": 100, "timeout": 5},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    # 2. Parse photo messages
    photos = parse_photo_updates(data, hours=hours, chat_id=chat_id)
    if not photos:
        return {}

    # 3. Filter out already-processed
    processed = load_processed(inbox_dir)
    new_photos = [p for p in photos if p["file_unique_id"] not in processed]
    if not new_photos:
        return {}

    # 4. Group by item
    groups = group_photos_by_item(new_photos)

    # 5. Download each photo
    saved: dict[str, list[Path]] = {}
    for item_folder, item_photos in groups.items():
        saved[item_folder] = []
        for i, photo in enumerate(item_photos, 1):
            # Get file path from Telegram
            file_resp = session.get(
                f"https://api.telegram.org/bot{token}/getFile",
                params={"file_id": photo["file_id"]},
                timeout=30,
            )
            file_resp.raise_for_status()
            file_data = file_resp.json()
            file_path = file_data["result"]["file_path"]

            # Download the actual image
            img_resp = session.get(
                f"https://api.telegram.org/file/bot{token}/{file_path}",
                timeout=60,
            )
            img_resp.raise_for_status()

            # Determine extension from file_path
            ext = Path(file_path).suffix or ".jpg"
            filename = f"photo-{i}{ext}"

            folder = Path(inbox_dir) / item_folder
            folder.mkdir(parents=True, exist_ok=True)
            out_path = folder / filename
            out_path.write_bytes(img_resp.content)

            saved[item_folder].append(out_path)

    # 6. Mark all as processed
    mark_processed(inbox_dir, new_photos)

    return saved
