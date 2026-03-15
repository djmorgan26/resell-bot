#!/usr/bin/env python3
"""
Notifier — sends Telegram notifications for resell-bot events.

Usage from any script in this repo:

    from notifications.notifier import notify
    notify("Your PS5 listing got a new offer: $380")

Credentials flow:
  1. Azure Service Principal credentials are read from notifications/.env
  2. Those are used to authenticate to Azure Key Vault
  3. Key Vault returns the Telegram bot token and chat ID
  4. Message is sent directly via the Telegram Bot API (no LLM formatting)
"""

import logging
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv

import telegram

logger = logging.getLogger(__name__)

# Load .env from this directory (works on any machine as long as .env is present)
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)

KEY_VAULT_URL = "https://personal-key-vault1.vault.azure.net/"

_token: str | None = None
_chat_id: str | None = None


def _load_secrets() -> None:
    """Fetch Telegram credentials from Azure Key Vault (runs once, then cached)."""
    global _token, _chat_id
    credential = DefaultAzureCredential(additionally_allowed_tenants=["*"])
    client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
    _token = client.get_secret("TELEGRAM-BOT-TOKEN").value
    _chat_id = client.get_secret("TELEGRAM-CHAT-ID").value
    logger.debug("Telegram credentials loaded from Key Vault.")


def notify(message: str) -> None:
    """Send a Telegram notification. Loads credentials on first call."""
    global _token, _chat_id
    if not _token:
        _load_secrets()
    telegram.send_message(_token, _chat_id, message)
    logger.info("Notification sent.")
