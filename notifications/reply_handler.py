#!/usr/bin/env python3
"""
reply_handler.py — parses the user's Telegram replies and matches them to pending actions.

The user replies in the format:
    "Key N"  or  "Key: N"
    e.g.  "Carter 1"  → execute option 1 for the "Carter" pending action
          "Carter 2"  → execute option 2

Usage:
    from notifications.reply_handler import load_pending, match_replies, resolve_actions

    pending = load_pending()
    messages = get_recent_messages()  # from telegram_reader
    matched = match_replies(messages)

    for m in matched:
        print(m["action"]["thread_url"], m["reply_text"])

    resolve_actions([m["action"]["key"] for m in matched])
"""

import json
import re
from pathlib import Path

PENDING_FILE = Path(__file__).parent / "pending_actions.json"


def load_pending() -> dict:
    """
    Load pending actions from JSON file.
    Returns empty structure if file doesn't exist or has no pending items.
    """
    if not PENDING_FILE.exists():
        return {"run_date": None, "pending": []}
    with open(PENDING_FILE) as f:
        return json.load(f)


def save_pending(data: dict) -> None:
    """Save pending actions back to JSON file."""
    with open(PENDING_FILE, "w") as f:
        json.dump(data, f, indent=2)


def clear_pending() -> None:
    """Clear all pending actions (call after a run completes with no new items)."""
    save_pending({"run_date": None, "pending": []})


def has_pending() -> bool:
    """Return True if there are any unresolved pending actions."""
    data = load_pending()
    return bool(data.get("pending"))


def match_replies(messages: list[dict]) -> list[dict]:
    """
    Match the user's Telegram messages against pending actions.

    Accepts these reply formats (case-insensitive):
        "Carter 1"
        "Carter: 1"
        "carter 2"

    Returns a list of dicts, each with:
        - action:      the full pending action dict
        - reply_text:  the response text to send to the buyer
        - matched_by:  the raw message text that triggered the match
    """
    data = load_pending()
    pending = data.get("pending", [])
    if not pending:
        return []

    matched = []
    resolved_keys = set()

    for msg in messages:
        text = msg["text"].strip()

        # Match "Word Number" or "Word: Number"
        m = re.match(r"^([A-Za-z]+)[:\s]+(\d+)\s*$", text)
        if not m:
            continue

        key = m.group(1).lower()
        option_num = m.group(2)

        for action in pending:
            if action["key"].lower() == key and key not in resolved_keys:
                options = action.get("options", {})
                if option_num in options:
                    matched.append({
                        "action": action,
                        "reply_text": options[option_num],
                        "matched_by": text,
                    })
                    resolved_keys.add(key)
                break

    return matched


def resolve_actions(keys: list[str]) -> None:
    """
    Remove resolved actions from pending_actions.json by key.
    Call this after successfully executing the matched replies.
    """
    data = load_pending()
    lower_keys = {k.lower() for k in keys}
    data["pending"] = [
        a for a in data.get("pending", [])
        if a["key"].lower() not in lower_keys
    ]
    save_pending(data)
