#!/usr/bin/env python3
"""Telegram delivery — raw Telegram Bot API calls."""

import requests


def send_message(token: str, chat_id: str, text: str) -> None:
    """Send a message to a Telegram chat."""
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    response.raise_for_status()
