#!/usr/bin/env python3
"""
telegram_reader.py — reads incoming messages sent to the Telegram bot.

Returns messages sent by David (non-bot) within the last N hours.

IMPORTANT — Cowork sandbox vs. local use:
  In the Cowork VM, Python cannot reach api.telegram.org (sandbox proxy blocks it).
  Use `parse_updates_response(raw_json, hours)` instead — fetch the data via Chrome
  JS first, then pass the raw JSON string here for parsing.

  Outside the VM (local dev, CI), use `get_recent_messages(hours)` directly.

Usage (Cowork VM — Chrome JS fetch first):
    # Step 1: fetch via Chrome JS (see scheduled-task-prompt-followup.txt Step 3)
    # Step 2: pass result to Python
    from notifications.telegram_reader import parse_updates_response
    msgs = parse_updates_response(raw_json_string, hours=2)

Usage (local/non-sandbox):
    from notifications.telegram_reader import get_recent_messages, acknowledge_updates
    messages = get_recent_messages(hours=2)
    if messages:
        acknowledge_updates(max(m["update_id"] for m in messages))
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)


def parse_updates_response(
    raw_json: str,
    hours: float = 2.0,
    chat_id: str | int | None = None,
) -> list[dict]:
    """
    Parse a raw Telegram getUpdates API response (already fetched, e.g. via Chrome JS).

    Use this in the Cowork sandbox where Python cannot reach api.telegram.org directly.
    Pass the raw JSON string returned by the Chrome JS fetch call.

    Args:
        raw_json: Raw JSON string from Telegram getUpdates API.
        hours: Only return messages from the last N hours.
        chat_id: If provided, only return messages from this chat.
                 Pass TELEGRAM_CHAT_ID from .env to filter to the group chat only.
                 If None, returns messages from ALL chats (legacy behavior).

    Returns the same format as get_recent_messages():
      - text (str): message text
      - timestamp (datetime, UTC): when it was sent
      - update_id (int): Telegram update ID for acknowledgement
      - chat_id (int): the chat the message came from
    """
    data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json

    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    target_chat_id = str(chat_id) if chat_id is not None else None
    messages = []

    for update in data.get("result", []):
        msg = update.get("message") or update.get("channel_post")
        if not msg:
            continue

        # Filter by chat — only process messages from the target group chat
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

        text = msg.get("text", "").strip()
        if not text:
            continue

        messages.append({
            "text": text,
            "timestamp": ts,
            "update_id": update["update_id"],
            "chat_id": int(msg_chat_id) if msg_chat_id else None,
        })

    return messages


def get_recent_messages(hours: float = 2.0) -> list[dict]:
    """
    Return messages sent to the bot by David in the last `hours` hours.

    NOTE: This will fail in the Cowork sandbox VM (Python can't reach api.telegram.org).
    Use parse_updates_response() with a Chrome JS fetch instead for scheduled runs.

    Automatically filters to the group chat (TELEGRAM_CHAT_ID from .env).

    Each returned dict has:
      - text (str): message text
      - timestamp (datetime, UTC): when it was sent
      - update_id (int): Telegram update ID for acknowledgement
      - chat_id (int): the chat the message came from
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in notifications/.env")

    session = requests.Session()
    session.trust_env = False  # bypass VM SOCKS5 proxy

    response = session.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params={"limit": 100, "timeout": 5},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return parse_updates_response(data, hours=hours, chat_id=chat_id)


def acknowledge_updates(max_update_id: int) -> None:
    """
    Acknowledge processed updates so they won't reappear in future getUpdates calls.
    Passes offset = max_update_id + 1 to Telegram.

    NOTE: In the Cowork sandbox, use Chrome JS for this instead:
      See scheduled-task-prompt-followup.txt Step 6 for the JS snippet.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return

    session = requests.Session()
    session.trust_env = False

    try:
        session.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": max_update_id + 1, "limit": 1, "timeout": 1},
            timeout=10,
        )
    except Exception:
        pass  # acknowledgement failure is non-fatal
