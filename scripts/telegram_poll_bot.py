#!/usr/bin/env python3
"""
telegram_poll_bot.py — Watches Telegram for new photos and triggers Claude to research them.

Runs as a background service (launchd). Polls Telegram via long polling.
When the user sends photos, it asks for confirmation, then spawns a `claude` CLI
session to research, price, and document the item in the inventory spreadsheet.

Supports BATCH MODE: send photos for multiple items (each with a distinct caption),
then say "go" once to research all of them in a single session.

Flow:
  1. User sends photo(s) with captions to the Telegram bot (one caption per item)
  2. Bot groups photos by caption — each distinct caption = one item
  3. Bot replies with a summary of all queued items
  4. User replies 'go' (or 'yes', 'list', etc.)
  5. Bot downloads photos and spawns ONE Claude session to handle all items
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
CONSUMED_UPDATES_FILE = REPO_ROOT / "notifications" / "consumed_updates.json"
CONSUMED_UPDATES_TTL = 86400  # 24 hours — prune older updates

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


# ─── Consumed updates persistence ──────────────────────────────────────────
# Every update the poll bot receives is saved here so that OTHER systems
# (followup skill, telegram_reader) can read messages the bot consumed.
# Format mirrors Telegram's getUpdates response: {"ok": true, "result": [...]}

def _load_consumed_updates() -> list[dict]:
    """Load previously consumed updates from disk."""
    if CONSUMED_UPDATES_FILE.exists():
        try:
            data = json.loads(CONSUMED_UPDATES_FILE.read_text())
            return data.get("result", [])
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_consumed_updates(updates: list[dict]) -> None:
    """Save consumed updates, pruning anything older than TTL."""
    now = time.time()
    pruned = []
    for u in updates:
        msg = u.get("message") or u.get("channel_post") or {}
        msg_date = msg.get("date", 0)
        if now - msg_date < CONSUMED_UPDATES_TTL:
            pruned.append(u)

    CONSUMED_UPDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONSUMED_UPDATES_FILE.write_text(json.dumps({"ok": True, "result": pruned}, indent=2))


def append_consumed_updates(new_updates: list[dict]) -> None:
    """Append new updates to the consumed file (deduplicating by update_id)."""
    existing = _load_consumed_updates()
    seen_ids = {u.get("update_id") for u in existing}
    for u in new_updates:
        if u.get("update_id") not in seen_ids:
            existing.append(u)
            seen_ids.add(u.get("update_id"))
    _save_consumed_updates(existing)


# ─── Pending session tracking ───────────────────────────────────────────────
# Sessions accumulate photos + context until the user says "go".
# Multiple sessions can be pending at once (batch mode).

class PendingSession:
    """Tracks photos and context for an item before the user confirms."""

    def __init__(self, caption: str, first_message_id: int):
        self.caption = caption
        self.photos: list[dict] = []  # [{file_id, file_unique_id, ...}]
        self.extra_context: list[str] = []
        self.first_message_id = first_message_id
        self.last_activity = time.time()
        self.prompted = False  # whether we've sent the album acknowledgment

    @property
    def folder_name(self) -> str:
        """Convert caption to a short, human-readable folder name.

        Convention: [item-type]-[key-descriptor]-[size-or-id]
        - All lowercase, hyphens between words, max ~35 characters
        - Strip filler words that add no meaning
        - Normalize dimensions (e.g. "27 x 29" → "27x29", "27.5 in" → "27in")

        Examples:
          "Oriental Khorjin Saddle Bag Tribal Handwoven Wool Pair 25 x 20.5"
          → "oriental-khorjin-saddle-bag-25x20"

          "Handwoven Striped Flatweave Rug Runner Brown Cream 30.5 x 57"
          → "handwoven-striped-rug-30x57"
        """
        import re
        name = self.caption.lower().strip()

        # Normalize dimensions: "27.5 x 56.5" → "27x56", "30.5in" → "30in"
        # Pattern: number (optional decimal) x number  OR  number (optional decimal) in/inch
        name = re.sub(r"(\d+)\.5\s*x\s*(\d+)\.5", r"\1x\2", name)   # 27.5 x 56.5 → 27x56
        name = re.sub(r"(\d+)\.5\s*x\s*(\d+)", r"\1x\2", name)       # 27.5 x 56 → 27x56
        name = re.sub(r"(\d+)\s*x\s*(\d+)\.5", r"\1x\2", name)       # 27 x 56.5 → 27x56
        name = re.sub(r"(\d+)\s*x\s*(\d+)", r"\1x\2", name)           # 27 x 56 → 27x56
        name = re.sub(r"(\d+)\.5\s*(in|inch|\")", r"\1in", name)      # 27.5in → 27in
        name = re.sub(r"(\d+)\s*(in|inch|\")", r"\1in", name)          # 27 in → 27in
        name = re.sub(r"(\d+)\.5\s*(ft|feet|')", r"\1ft", name)       # 11.5ft → 11ft

        # Remove filler words that add no meaning to a folder name
        fillers = [
            r"\beach\b", r"\bside\b", r"\bthere\bare\b", r"\bphotos?\b",
            r"\bhandwoven\b", r"\bhandmade\b", r"\bhand[-\s]?knotted\b",
            r"\bhand[-\s]?woven\b", r"\btribal\b", r"\bwool\b", r"\bpair\b",
            r"\bvintage\b", r"\bfloral\b(?!\s+mat)", r"\bgeometric\b",
            r"\bflatweave\b", r"\brunner\b", r"\bpile\b(?!\s+rug)",
            r"\bdesign\b", r"\bpattern\b", r"\bdecorative\b",
            r"\bbeautiful\b", r"\bnice\b", r"\bgreat\b", r"\bexcellent\b",
            r"\bcondition\b", r"\bitem\b", r"\blisting\b",
            r"\bthe\b", r"\band\b", r"\bwith\b", r"\bfor\b", r"\bof\b",
        ]
        for filler in fillers:
            name = re.sub(filler, " ", name)

        # Strip non-alphanumeric chars except hyphens and spaces
        name = re.sub(r"[^\w\s\-]", "", name)
        # Collapse whitespace and replace with hyphens
        name = re.sub(r"[\s_]+", "-", name.strip())
        # Collapse multiple hyphens
        name = re.sub(r"-+", "-", name)
        # Strip leading/trailing hyphens
        name = name.strip("-")

        # Trim to max 35 chars, breaking only at a hyphen
        if len(name) > 35:
            trimmed = name[:35]
            last_hyphen = trimmed.rfind("-")
            if last_hyphen > 15:  # only break at hyphen if we keep a reasonable chunk
                name = trimmed[:last_hyphen]
            else:
                name = trimmed

        return name or "unnamed-item"

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
        real_ctx = [c for c in self.extra_context if c != "__prompted__"]
        if real_ctx:
            parts.append(f"{len(real_ctx)} note(s)")
        return ", ".join(parts)


# Batch mode: multiple pending sessions, keyed by folder_name
_pending_sessions: Dict[str, PendingSession] = {}
# Map media_group_id → session folder_name so album photos route correctly
_media_group_map: Dict[str, str] = {}
# Track the most recently created session key (for captionless non-album photos)
_last_session_key: Optional[str] = None

# Trigger words that mean "go ahead and research it"
GO_WORDS = {"go", "yes", "list", "list it", "do it", "start", "sell", "sell it", "post", "post it"}
# Words that cancel everything
CANCEL_WORDS = {"cancel", "stop", "nevermind", "nvm", "no", "cancel all"}


# ─── Core logic ──────────────────────────────────────────────────────────────

def _queue_summary() -> str:
    """Build a summary of all pending sessions."""
    if not _pending_sessions:
        return "No items queued."
    lines = []
    for i, session in enumerate(_pending_sessions.values(), 1):
        lines.append(f"  {i}. {session.summary}")
    return "\n".join(lines)


def _find_session_for_media_group(media_group_id: str) -> Optional[str]:
    """Find which session a media_group_id belongs to."""
    return _media_group_map.get(media_group_id)


def handle_update(update: dict) -> None:
    """Process a single Telegram update."""
    global _last_session_key

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
    media_group_id = msg.get("media_group_id")

    # Expire stale sessions
    expired = [k for k, s in _pending_sessions.items() if s.is_expired]
    for k in expired:
        log.info(f"Session expired for '{_pending_sessions[k].caption}'")
        del _pending_sessions[k]

    if has_photo:
        # Pick highest resolution
        best = msg["photo"][-1]
        photo_info = {
            "file_id": best["file_id"],
            "file_unique_id": best["file_unique_id"],
            "width": best.get("width"),
            "height": best.get("height"),
            "media_group_id": media_group_id,
        }

        # Determine which session this photo belongs to
        target_key = None

        if media_group_id:
            # Check if this media group already maps to a session
            target_key = _find_session_for_media_group(media_group_id)

        if target_key is None and caption:
            # New caption = new item. Create a session for it.
            item_name = caption
            session = PendingSession(item_name, message_id)
            target_key = session.folder_name
            _pending_sessions[target_key] = session
            if media_group_id:
                _media_group_map[media_group_id] = target_key
            _last_session_key = target_key
            log.info(f"New session started: '{item_name}'")

        elif target_key is None and not caption:
            if media_group_id and _last_session_key and _last_session_key in _pending_sessions:
                # Captionless album photo — route to most recent session
                target_key = _last_session_key
                _media_group_map[media_group_id] = target_key
            elif _last_session_key and _last_session_key in _pending_sessions:
                # Captionless non-album photo — add to most recent session
                target_key = _last_session_key
            else:
                # No session at all — create an unnamed one
                item_name = f"item-{datetime.now().strftime('%Y%m%d-%H%M')}"
                session = PendingSession(item_name, message_id)
                target_key = session.folder_name
                _pending_sessions[target_key] = session
                _last_session_key = target_key
                log.info(f"New unnamed session started: '{item_name}'")

        # Add the photo to the target session
        if target_key and target_key in _pending_sessions:
            _pending_sessions[target_key].add_photo(photo_info)
            s = _pending_sessions[target_key]
            log.info(f"Photo added to '{s.caption}' ({len(s.photos)} total)")

    elif text:
        text_lower = text.lower().strip()

        if _pending_sessions and text_lower in GO_WORDS:
            # User confirmed — trigger research for ALL pending sessions
            count = len(_pending_sessions)
            total_photos = sum(len(s.photos) for s in _pending_sessions.values())
            log.info(f"User confirmed research for {count} item(s) — triggering workflows")

            items_list = "\n".join(
                f"  • \"{s.caption}\" ({len(s.photos)} photos)"
                for s in _pending_sessions.values()
            )
            send_reply(
                f"On it! Researching {count} item(s) ({total_photos} photos total):\n\n"
                f"{items_list}\n\n"
                f"I'll research them all and send updates as I go.",
                reply_to=message_id,
            )

            trigger_batch_research(list(_pending_sessions.values()))

            _pending_sessions.clear()
            _media_group_map.clear()
            _last_session_key = None

        elif _pending_sessions and text_lower in CANCEL_WORDS:
            count = len(_pending_sessions)
            log.info(f"User cancelled {count} pending session(s)")
            send_reply(f"Got it, cancelled {count} item(s).", reply_to=message_id)
            _pending_sessions.clear()
            _media_group_map.clear()
            _last_session_key = None

        elif _pending_sessions:
            # Check if this looks like context for pending photos or a general instruction.
            # If the user is replying to one of the bot's queue messages, treat as photo context.
            # Otherwise, just acknowledge it — it's saved in consumed_updates.json for
            # the morning run to pick up as a standing instruction.
            reply_to_msg = msg.get("reply_to_message", {})
            reply_from = reply_to_msg.get("from", {})
            is_reply_to_bot = reply_from.get("is_bot", False)

            if is_reply_to_bot:
                # User is replying to the bot's queue message — treat as photo context
                if _last_session_key and _last_session_key in _pending_sessions:
                    _pending_sessions[_last_session_key].add_context(text)
                    log.info(f"Added context to '{_pending_sessions[_last_session_key].caption}': {text[:50]}")
                send_reply(
                    f"Noted. You have {len(_pending_sessions)} item(s) queued:\n\n"
                    f"{_queue_summary()}\n\n"
                    f"Keep sending photos, or reply \"go\" to research them all.",
                    reply_to=message_id,
                )
            else:
                # General message — don't attach to photo sessions.
                # It's already saved in consumed_updates.json for the morning/followup run.
                log.info(f"General message (not photo context): {text[:80]}")
                send_reply(
                    f"Got it — I'll pass that along to your next scheduled run.\n\n"
                    f"(You also have {len(_pending_sessions)} item(s) queued for research — "
                    f"reply \"go\" when ready.)",
                    reply_to=message_id,
                )

        else:
            # No pending sessions — general message.
            # Saved in consumed_updates.json for the morning/followup run.
            log.info(f"General message (no sessions): {text[:80]}")
            send_reply(
                "Got it — I'll pass that along to your next scheduled run.",
                reply_to=message_id,
            )


def check_album_prompt() -> None:
    """After processing a batch of updates, send a summary of all new/updated sessions."""
    unprompted = [s for s in _pending_sessions.values() if not s.prompted]
    if not unprompted:
        return

    # Mark all as prompted
    for s in unprompted:
        s.prompted = True

    total = len(_pending_sessions)
    if total == 1:
        s = list(_pending_sessions.values())[0]
        send_reply(
            f"I see an item: \"{s.caption}\" ({len(s.photos)} photo(s))\n\n"
            f"Send more items or details if you have them.\n"
            f"When you're ready, reply \"go\" and I'll research everything.",
        )
    else:
        send_reply(
            f"I have {total} item(s) queued:\n\n"
            f"{_queue_summary()}\n\n"
            f"Keep sending more items, or reply \"go\" to research them all at once.",
        )


def _download_session_photos(session: PendingSession) -> Path:
    """Download all photos for a session and return the folder path."""
    item_folder = INBOX_DIR / session.folder_name
    item_folder.mkdir(parents=True, exist_ok=True)

    log.info(f"Downloading {len(session.photos)} photos to {item_folder}")
    for i, photo in enumerate(session.photos, 1):
        try:
            img_bytes = download_photo(photo["file_id"])
            out_path = item_folder / f"photo-{i}.jpg"
            out_path.write_bytes(img_bytes)
            log.info(f"  Saved {out_path.name} ({len(img_bytes)} bytes)")
        except Exception as e:
            log.error(f"  Failed to download photo {i}: {e}")

    return item_folder


def trigger_batch_research(sessions: list[PendingSession]) -> None:
    """Download photos for all sessions and spawn ONE Claude session to handle them all.

    A single session lets Claude see all items together, so it can:
    - Recognize that separate photo groups are actually the same item
    - Group related photos intelligently (e.g. "blue vase front" + "blue vase back")
    - Process everything with full context
    """
    # Download photos for each session
    items_info = []
    for session in sessions:
        folder = _download_session_photos(session)
        real_context = [c for c in session.extra_context if c != "__prompted__"]
        context_str = ""
        if real_context:
            context_str = "\n    Additional context: " + "; ".join(real_context)

        items_info.append(
            f"  - Caption: \"{session.caption}\"\n"
            f"    Photos: {folder} ({len(session.photos)} photo(s))\n"
            f"    Folder name: {session.folder_name}"
            f"{context_str}"
        )

    items_block = "\n\n".join(items_info)
    count = len(sessions)

    prompt = (
        f"Read CLAUDE.md first for project rules and layout.\n\n"
        f"The user sent {count} item(s) via Telegram for research and listing.\n\n"
        f"Items received:\n\n{items_block}\n\n"
        f"IMPORTANT — SMART GROUPING:\n"
        f"Before processing, look at ALL the photos and captions together. Some may\n"
        f"actually be the same item sent in separate batches (e.g. different angles,\n"
        f"or the user sent a few photos then sent more of the same thing later).\n"
        f"If you determine that multiple caption groups are actually the SAME item,\n"
        f"merge them — combine their photos into one folder and treat them as one item.\n"
        f"Use your best judgment based on the photos and captions.\n\n"
        f"For EACH distinct item (after any merging), follow skills/create-listing/SKILL.md\n"
        f"stages 1-5 ONLY. Do NOT attempt to publish or use Chrome browser tools.\n\n"
        f"Process items one at a time, completing all stages for each before moving on.\n\n"
        f"IMPORTANT — Send Telegram progress updates at these milestones using\n"
        f"  from notifications.notifier import notify\n\n"
        f"  1. At the start: tell the user how many distinct items you identified\n"
        f"     (mention any merges you made)\n"
        f"  2. After pricing each item: send the 3 price tiers and your recommendation\n\n"
        f"PRICING RULE: Default to Market Price for the listed price. The strategy is to\n"
        f"start at market price and lower over time if there's no interest.\n\n"
        f"After completing stages 1-5 for EACH item:\n"
        f"  1. Update resell_inventory.xlsx with status 'ready' using scripts/update_inventory.py\n"
        f"     Set the listed price to the Market Price tier.\n"
        f"  2. Move photos from photo-inbox/<folder>/ to items/<folder>/\n"
        f"  3. After ALL items are done, send ONE final Telegram summary with all items:\n"
        f"     - Each item's identification, key details, and 3 price tiers\n"
        f"     - The listing title and description draft for each\n"
        f"     - End with: \"All {count} item(s) researched and ready! Tell Claude Cowork\n"
        f"       to publish them, or they'll be posted on the next scheduled run.\"\n"
    )

    label = ", ".join(s.caption for s in sessions)
    _spawn_claude(
        prompt,
        log_name=f"research-batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        label=label,
    )


def _spawn_claude(prompt: str, log_name: str, label: str) -> None:
    """Spawn a Claude CLI session in the background.

    Uses -p (print) mode which is non-interactive. No Chrome — uses WebSearch
    for market research. Publishing is handled separately by Cowork or the
    morning scheduled run.

    The prompt is piped via stdin to avoid shell escaping issues with special
    characters in item captions (quotes, dimensions like 37 1/2" x 56").
    """
    cmd = [
        "claude",
        "-p",
        "--permission-mode", "auto",
        "--model", "sonnet",
        "--allowedTools",
        "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch",
    ]

    log.info(f"Spawning Claude session for '{label}'")
    try:
        log_path = REPO_ROOT / "logs" / f"{log_name}.log"
        log_file = open(log_path, "w")
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdin=subprocess.PIPE,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        # Write prompt to stdin and close to signal EOF
        proc.stdin.write(prompt.encode("utf-8"))
        proc.stdin.close()
        log.info(f"Claude session started (PID {proc.pid}) — log: {log_path}")
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

    # Save ALL consumed updates so other systems (followup) can read them
    append_consumed_updates(results)

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
                # Save ALL consumed updates so other systems (followup) can read them
                append_consumed_updates(results)

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
