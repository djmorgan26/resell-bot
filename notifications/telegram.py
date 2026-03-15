#!/usr/bin/env python3
"""Telegram delivery — raw Telegram Bot API calls.

NOTE: In the Cowork sandbox VM, the system SOCKS5 proxy blocks api.telegram.org.
Python-based sending will fail with a DNS/proxy error in that environment.
Use the Chrome JavaScript method documented in notifications/SKILL.md instead.
This module is kept for use in non-sandbox environments (local dev, CI, etc.)
"""

import requests


def send_message(token: str, chat_id: str, text: str) -> None:
    """Send a message to a Telegram chat.
    Bypasses environment proxy settings (trust_env=False).
    """
    session = requests.Session()
    session.trust_env = False
    response = session.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    response.raise_for_status()
