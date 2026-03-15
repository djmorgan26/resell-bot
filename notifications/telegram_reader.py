#!/usr/bin/env python3
"""
telegram_reader.py — reads incoming messages sent to the Telegram bot.

Returns messages sent by David (non-bot) within the last N hours.
Uses trust_env=False to bypass the VM's SOCKS5 proxy (same pattern as telegram.py).

Usage:
    from notifications.telegram_reader import get_recent_messages, acknowledge_updates

    messages = get_recent_messages(hours=2)
    for msg in messages:
        print(msg["text"], msg["timestamp"])

    if messages:
        acknowledge_updates(max(m["update_id"] for m in messages))
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)


def get_recent_messages(hours: float = 2.0) -> list[dict]:
    """
    Return messages sent to the bot by David in the last `hours` hours.

    Skips messages from bots. Each returned dict has:
      - text (str): message text
      - timestamp (datetime, UTC): when it was sent
      - update_id (int): Telegram update ID for acknowledgement
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
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

    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    messages = []

    for update in data.get("result", []):
        msg = update.get("message") or update.get("channel_post")
        if not msg:
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
        })

    return messages


def acknowledge_updates(max_update_id: int) -> None:
    """
    Acknowledge processed updates so they won't reappear in future getUpdates calls.
    Passes offset = max_update_id + 1 to Telegram.
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
