#!/usr/bin/env python3
"""
Notifier — sends Telegram notifications for resell-bot events.

Usage from any script in this repo:

    from notifications.notifier import notify
    notify("Your PS5 listing got a new offer: $380")

Credentials flow:
  1. TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are read directly from notifications/.env
  2. Message is sent via the Telegram Bot API
"""

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from notifications import telegram

logger = logging.getLogger(__name__)

# Load .env from this directory (works on any machine as long as .env is present)
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)

_token: Optional[str] = None
_chat_id: Optional[str] = None


def _load_secrets() -> None:
    """Read Telegram credentials from .env file."""
    global _token, _chat_id

    if not _env_path.exists():
        raise RuntimeError(
            "notifications/.env not found. "
            "Run `python3 setup.py` to complete setup, "
            "or copy notifications/.env.example to notifications/.env and fill in your credentials."
        )

    _token = os.getenv("TELEGRAM_BOT_TOKEN")
    _chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not _token or not _chat_id:
        raise RuntimeError(
            "Missing Telegram credentials. "
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in notifications/.env"
        )
    logger.debug("Telegram credentials loaded from .env.")


def notify(message: str) -> None:
    """Send a Telegram notification. Loads credentials on first call."""
    global _token, _chat_id
    if not _token:
        _load_secrets()
    telegram.send_message(_token, _chat_id, message)
    logger.info("Notification sent.")
