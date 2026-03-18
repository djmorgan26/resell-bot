#!/usr/bin/env python3
"""
telegram_poll_bot.py — Watches Telegram for new photos and triggers Claude to research them.

Runs as a background service (launchd). Polls Telegram via long polling.
When the user sends photos, it asks for confirmation, then spawns a `claude` CLI
session to research, price, and document the item in the inventory spreadsheet.

Flow:
  1. User sends photo(s) with caption to the Telegram bot
  2. Bot replies: "I see [caption]! Send more photos/details, or reply 'go'."
  3. User replies 'go' (or 'yes', 'list', etc.)
  4. Bot downloads photos to photo-inbox/<item>/
  5. Bot spawns: claude -p "research and document this item..."
  6. Claude researches comps, prices it, writes listing draft, updates inventory
  7. Claude sends Telegram summary with item details and next steps

Usage:
  python3 scripts/telegram_poll_bot.py          # run in foreground
  python3 scripts/telegram_poll_bot.py --once   # check once and exit (for testing)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add repo root to path so we can import notifications modules
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from notifications.photo_inbox import (
    group_photos_by_item,
    load_processed,
    mark_processed,
    parse_photo_updates,
    save_photo_from_base64,
)

# ─── Config ──────────────────────────────────────────────────────────────────

ENV_PATH = REPO_ROOT / "notifications" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
INBOX_DIR = REPO_ROOT / "photo-inbox"
POLL_INTERVAL = 3  # seconds between polls
SESSION_TIMEOUT = 1800  # 30 min — expire pending sessions
OFFSET_FILE = REPO_ROOT / "photo-inbox" / ".listener_offset"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("poll-bot")

# ─── Telegram API helpers ────────────────────────────────────────────────────

import requests

_session = requests.Session()
_session.trust_env = False


def tg_api(method: str, **params) -> dict:
    """Call a Telegram Bot API method."""
    resp = _session.post(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        json=params,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data


def send_reply(text: str, reply_to: int | None = None) -> None:
    """Send a message to the user's chat."""
    params = {"chat_id": CHAT_ID, "text": text}
    if reply_to:
        params["reply_to_message_id"] = reply_to
    tg_api("sendMessage", **params)


def get_updates(offset: int | None = None, timeout: int = 30) -> dict:
    """Long-poll for new updates."""
    params = {"timeout": timeout, "limit": 100}
    if offset is not None:
        params["offset"] = offset
    return tg_api("getUpdates", **params)


def download_photo(file_id: str) -> bytes:
    """Download a photo by file_id and return raw bytes."""
    file_info = tg_api("getFile", file_id=file_id)
    file_path = file_info["result"]["file_path"]
    resp = _session.get(
        f"https://api.telegram.org/file/bot{TOKEN}/{file_path}",
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


# ─── Offset persistence ─────────────────────────────────────────────────────

def load_offset() -> int | None:
    """Load the last processed update_id."""
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except (ValueError, OSError):
            pass
    return None


def save_offset(offset: int) -> None:
    """Persist the latest update_id so we don't re-process on restart."""
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(offset))


# ─── Pending session tracking ───────────────────────────────────────────────
# A "session" accumulates photos + context until the user says "go".

class PendingSession:
    """Tracks photos and context for an item before the user confirms."""

    def __init__(self, caption: str, first_message_id: int):
        self.caption = caption
        self.photos: list[dict] = []  # [{file_id, file_unique_id, ...}]
        self.extra_context: list[str] = []
        self.first_message_id = first_message_id
        self.last_activity = time.time()

    @property
    def folder_name(self) -> str:
        import re
        name = self.caption.lower().strip()
        name = re.sub(r"[^\w\s-]", "", name)
        name = re.sub(r"\s+", "-", name)
        return (name[:60] or "unnamed-item")

    def add_photo(self, photo_info: dict) -> None:
        self.photos.append(photo_info)
        self.last_activity = time.time()

    def add_context(self, text: str) -> None:
        self.extra_context.append(text)
        self.last_activity = time.time()

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_activity) > SESSION_TIMEOUT

    @property
    def summary(self) -> str:
        parts = [f'"{self.caption}"']
        parts.append(f"{len(self.photos)} photo(s)")
        if self.extra_context:
            parts.append(f"{len(self.extra_context)} extra note(s)")
        return ", ".join(parts)


# Active sessions: one per chat (simple — user lists one item at a time)
_pending: PendingSession | None = None

# Trigger words that mean "go ahead and research it"
GO_WORDS = {"go", "yes", "list", "list it", "do it", "start", "sell", "sell it", "post", "post it"}


# ─── Core logic ──────────────────────────────────────────────────────────────

def handle_update(update: dict) -> None:
    """Process a single Telegram update."""
    global _pending

    msg = update.get("message")
    if not msg:
        return

    # Only process messages from our chat
    msg_chat_id = str(msg.get("chat", {}).get("id", ""))
    if msg_chat_id != str(CHAT_ID):
        return

    # Skip bot messages
    from_info = msg.get("from") or {}
    if from_info.get("is_bot"):
        return

    message_id = msg["message_id"]
    text = (msg.get("text") or "").strip()
    caption = (msg.get("caption") or "").strip()
    has_photo = "photo" in msg

    # Expire stale session
    if _pending and _pending.is_expired:
        log.info(f"Session expired for '{_pending.caption}'")
        _pending = None

    if has_photo:
        # Pick highest resolution
        best = msg["photo"][-1]
        photo_info = {
            "file_id": best["file_id"],
            "file_unique_id": best["file_unique_id"],
            "width": best.get("width"),
            "height": best.get("height"),
            "media_group_id": msg.get("media_group_id"),
        }

        if _pending is None:
            # Start a new session
            item_name = caption or f"item-{datetime.now().strftime('%Y%m%d-%H%M')}"
            _pending = PendingSession(item_name, message_id)
            _pending.add_photo(photo_info)
            log.info(f"New session started: '{item_name}' (1 photo)")

            # Don't reply to album photos individually — wait a beat
            # (Telegram sends album photos as separate updates with same media_group_id)
            # We'll send the prompt after a brief collection window
            if not msg.get("media_group_id"):
                send_reply(
                    f"I see an item: \"{item_name}\"\n\n"
                    f"Send more photos or details if you have them.\n"
                    f"When you're ready, reply \"go\" and I'll research it.",
                    reply_to=message_id,
                )
        else:
            # Add to existing session
            _pending.add_photo(photo_info)
            # Update caption if this photo has one and the session doesn't have a good one
            if caption and _pending.caption.startswith("item-"):
                _pending.caption = caption
            log.info(f"Photo added to session '{_pending.caption}' ({len(_pending.photos)} total)")

    elif text:
        text_lower = text.lower().strip()

        if _pending and text_lower in GO_WORDS:
            # User confirmed — trigger research
            log.info(f"User confirmed research for '{_pending.caption}' — triggering workflow")
            send_reply(
                f"On it! Researching \"{_pending.caption}\" "
                f"({len(_pending.photos)} photos).\n\n"
                f"I'll look up comps, price it, and write a listing draft. "
                f"You'll get updates along the way.",
                reply_to=message_id,
            )
            trigger_research(_pending)
            _pending = None

        elif _pending and text_lower in {"cancel", "stop", "nevermind", "nvm", "no"}:
            log.info(f"User cancelled session for '{_pending.caption}'")
            send_reply("Got it, cancelled.", reply_to=message_id)
            _pending = None

        elif _pending:
            # Treat as extra context
            _pending.add_context(text)
            log.info(f"Added context to session '{_pending.caption}': {text[:50]}")
            send_reply(
                f"Noted. Reply \"go\" when you're ready, or keep adding details.",
                reply_to=message_id,
            )

        # If no pending session and it's just text, ignore


def check_album_prompt() -> None:
    """After processing a batch of updates, send the album prompt if needed."""
    global _pending
    if _pending and len(_pending.photos) > 1 and not _pending.extra_context:
        # If we got multiple photos (album) and haven't prompted yet,
        # check if the last photo was part of a media group
        all_mg = {p.get("media_group_id") for p in _pending.photos}
        if all_mg != {None}:
            # This was an album — send a single prompt
            send_reply(
                f"I see an item: \"{_pending.caption}\" ({len(_pending.photos)} photos)\n\n"
                f"Send more photos or details if you have them.\n"
                f"When you're ready, reply \"go\" and I'll research it.",
            )
            # Mark that we've prompted by adding empty context
            _pending.extra_context.append("__prompted__")


def trigger_research(session: PendingSession) -> None:
    """Download photos and spawn a Claude session to research and document the item."""
    item_folder = INBOX_DIR / session.folder_name
    item_folder.mkdir(parents=True, exist_ok=True)

    # Download all photos
    log.info(f"Downloading {len(session.photos)} photos to {item_folder}")
    for i, photo in enumerate(session.photos, 1):
        try:
            img_bytes = download_photo(photo["file_id"])
            out_path = item_folder / f"photo-{i}.jpg"
            out_path.write_bytes(img_bytes)
            log.info(f"  Saved {out_path.name} ({len(img_bytes)} bytes)")
        except Exception as e:
            log.error(f"  Failed to download photo {i}: {e}")

    # Build the prompt for Claude
    context_str = ""
    real_context = [c for c in session.extra_context if c != "__prompted__"]
    if real_context:
        context_str = "\n\nAdditional context from the user:\n" + "\n".join(f"- {c}" for c in real_context)

    prompt = (
        f"Read CLAUDE.md first for project rules and layout.\n\n"
        f"A new item has arrived for research. The user sent photos via Telegram.\n\n"
        f"Item name/caption: \"{session.caption}\"\n"
        f"Photos location: {item_folder}\n"
        f"Number of photos: {len(session.photos)}\n"
        f"{context_str}\n\n"
        f"Read and follow skills/create-listing/SKILL.md for stages 1-5 ONLY.\n"
        f"Do NOT attempt to publish or use Chrome browser tools.\n\n"
        f"IMPORTANT — Send Telegram progress updates at these milestones using\n"
        f"  from notifications.notifier import notify\n\n"
        f"  1. After identifying the item (stage 2): tell the user what you think it is\n"
        f"  2. After pricing (stage 4): send the 3 price tiers and your recommendation\n\n"
        f"PRICING RULE: Default to Market Price for the listed price. The strategy is to\n"
        f"start at market price and lower over time if there's no interest.\n\n"
        f"After completing stages 1-5:\n"
        f"  1. Update resell_inventory.xlsx with status 'ready' using scripts/update_inventory.py\n"
        f"     Set the listed price to the Market Price tier.\n"
        f"  2. Move photos from {item_folder} to items/{session.folder_name}/\n"
        f"  3. Send a final Telegram summary with:\n"
        f"     - Item identification and key details\n"
        f"     - The 3 price tiers (quick / market / optimistic)\n"
        f"     - The listing title and description draft\n"
        f"     - End with: \"Ready to list! Tell Claude Cowork to publish it, or it will\n"
        f"       be posted on the next scheduled run.\"\n"
    )

    _spawn_claude(
        prompt,
        log_name=f"research-{session.folder_name}",
        label=session.caption,
    )


def _spawn_claude(prompt: str, log_name: str, label: str) -> None:
    """Spawn a Claude CLI session in the background.

    Uses -p (print) mode which is non-interactive. No Chrome — uses WebSearch
    for market research. Publishing is handled separately by Cowork or the
    morning scheduled run.
    """
    cmd = [
        "claude",
        "-p",
        "--permission-mode", "auto",
        "--model", "sonnet",
        "--allowedTools",
        "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch",
        prompt,
    ]

    log.info(f"Spawning Claude session for '{label}'")
    try:
        log_path = REPO_ROOT / "logs" / f"{log_name}.log"
        subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=open(log_path, "w"),
            stderr=subprocess.STDOUT,
        )
        log.info(f"Claude session started — log: {log_path}")
    except Exception as e:
        log.error(f"Failed to start Claude session: {e}")
        send_reply(f"Something went wrong starting the process: {e}")


# ─── Main loop ───────────────────────────────────────────────────────────────

def run_once() -> None:
    """Check for updates once and process them."""
    offset = load_offset()
    data = get_updates(offset=offset, timeout=0)

    results = data.get("result", [])
    if not results:
        log.info("No new updates")
        return

    max_id = offset or 0
    for update in results:
        handle_update(update)
        uid = update.get("update_id", 0)
        if uid > max_id:
            max_id = uid

    check_album_prompt()

    # Save offset so we don't re-process these updates
    save_offset(max_id + 1)
    log.info(f"Processed {len(results)} updates, offset now {max_id + 1}")


def run_loop() -> None:
    """Main polling loop — runs forever."""
    log.info("Telegram poll bot started. Waiting for photos...")
    offset = load_offset()

    while True:
        try:
            data = get_updates(offset=offset, timeout=30)
            results = data.get("result", [])

            if results:
                max_id = offset or 0
                for update in results:
                    handle_update(update)
                    uid = update.get("update_id", 0)
                    if uid > max_id:
                        max_id = uid

                check_album_prompt()
                offset = max_id + 1
                save_offset(offset)
                log.info(f"Processed {len(results)} updates")

        except KeyboardInterrupt:
            log.info("Shutting down")
            break
        except requests.exceptions.Timeout:
            # Normal for long polling — just retry
            continue
        except Exception as e:
            log.error(f"Error in poll loop: {e}")
            time.sleep(POLL_INTERVAL)


def main():
    if not TOKEN or not CHAT_ID:
        print("ERROR: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in notifications/.env")
        print("Run `python3 setup.py` to configure.")
        sys.exit(1)

    # Ensure logs directory exists
    (REPO_ROOT / "logs").mkdir(exist_ok=True)

    parser = argparse.ArgumentParser(description="Watch Telegram for items to research")
    parser.add_argument("--once", action="store_true", help="Check once and exit")
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_loop()


if __name__ == "__main__":
    main()
