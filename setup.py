#!/usr/bin/env python3
"""
resell-bot setup wizard
-----------------------
Run this once to configure resell-bot for your machine.
It will walk you through creating your config.yaml and notifications/.env,
then verify everything is working.

Usage:
    python3 setup.py
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"{GREEN}✓{RESET}  {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}!{RESET}  {msg}")


def err(msg: str) -> None:
    print(f"{RED}✗{RESET}  {msg}")


def heading(msg: str) -> None:
    print(f"\n{BOLD}{msg}{RESET}")
    print("─" * len(msg))


def ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    try:
        answer = input(f"  {prompt}{hint}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled.")
        sys.exit(0)
    return answer if answer else default


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    answer = ask(f"{prompt} ({hint})", "")
    if not answer:
        return default
    return answer.lower().startswith("y")


def pause(msg: str = "Press Enter when you're ready to continue...") -> None:
    try:
        input(f"\n  {msg}")
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled.")
        sys.exit(0)


# ── checks ────────────────────────────────────────────────────────────────────

def check_python() -> None:
    if sys.version_info < (3, 8):
        err(f"Python 3.8+ required. You have {sys.version}.")
        sys.exit(1)
    ok(f"Python {sys.version.split()[0]}")


def check_venv() -> None:
    venv = REPO_ROOT / ".venv"
    if venv.exists():
        ok(".venv already exists")
        return
    warn(".venv not found — creating it now...")
    import subprocess
    result = subprocess.run([sys.executable, "-m", "venv", str(venv)])
    if result.returncode != 0:
        err("Failed to create virtual environment.")
        sys.exit(1)
    pip = venv / "bin" / "pip"
    result = subprocess.run([str(pip), "install", "-r", str(REPO_ROOT / "requirements.txt")])
    if result.returncode != 0:
        err("Failed to install dependencies.")
        sys.exit(1)
    ok("Virtual environment created and dependencies installed")


def check_dependencies() -> None:
    try:
        import yaml  # noqa: F401
        import dotenv  # noqa: F401
        import openpyxl  # noqa: F401
        ok("Python dependencies installed")
    except ImportError as e:
        err(f"Missing dependency: {e}")
        print("     Run: pip install -r requirements.txt")
        sys.exit(1)


# ── steps ─────────────────────────────────────────────────────────────────────

def step_user_info() -> dict:
    heading("Step 1 — About you")
    print("  This helps personalize notifications and skill behavior.\n")

    name = ask("Your first name")
    while not name:
        warn("Name can't be empty.")
        name = ask("Your first name")

    ebay = ask("Your eBay seller username (leave blank if you don't use eBay)", "")
    use_fb = ask_yes_no("Do you sell on Facebook Marketplace?", True)

    priority = "speed"
    if ask_yes_no("Do you want to maximize sale price (vs. quick sale)?", False):
        priority = "price"

    marketplaces = []
    if ebay:
        marketplaces.append("ebay")
    if use_fb:
        marketplaces.append("fb_marketplace")
    if not marketplaces:
        warn("No marketplaces selected — you can edit config.yaml later to add them.")

    return {
        "user": {"name": name},
        "selling": {
            "ebay_username": ebay,
            "priority": priority,
        },
        "marketplaces": marketplaces,
    }


def step_write_config(config: dict) -> None:
    heading("Step 2 — Writing config.yaml")
    import yaml

    config_path = REPO_ROOT / "config.yaml"
    with open(config_path, "w") as f:
        f.write("# resell-bot configuration\n")
        f.write("# This file is gitignored — it contains your personal settings.\n\n")
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    ok(f"config.yaml written to {config_path}")


def step_telegram() -> tuple[str, str]:
    heading("Step 3 — Telegram bot setup")
    print("""
  resell-bot sends you notifications and reads your replies via a Telegram bot.
  You need to create a bot and get two pieces of info: a token and your chat ID.

  ┌─────────────────────────────────────────────────────────┐
  │  Part A — Create your Telegram bot (takes ~2 minutes)   │
  └─────────────────────────────────────────────────────────┘
  1. Open Telegram on your phone or computer
  2. Search for @BotFather and start a chat
  3. Send:  /newbot
  4. Follow the prompts — pick a name and username for your bot
     (the username must end in "bot", e.g. "myresellbot")
  5. BotFather will give you a token that looks like:
        1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk
  6. Copy that token.
""")
    pause("Press Enter once you have your bot token...")

    token = ask("Paste your bot token here")
    while not token or ":" not in token:
        err("That doesn't look like a bot token (expected format: 123456789:ABCDEF...)")
        token = ask("Paste your bot token here")

    print("""
  ┌─────────────────────────────────────────────────────────┐
  │  Part B — Find your Telegram chat ID                    │
  └─────────────────────────────────────────────────────────┘
  1. Open Telegram and search for the bot you just created
  2. Send it any message (e.g. "hello")
  3. Then open this URL in your browser — replace TOKEN with your token:

        https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates

  4. Look for "chat":{"id": followed by a number — that's your chat ID.
     It might be negative (e.g. -100123456789) or positive (e.g. 123456789).
""")
    pause("Press Enter once you have your chat ID...")

    chat_id = ask("Paste your chat ID here")
    while not chat_id:
        err("Chat ID can't be empty.")
        chat_id = ask("Paste your chat ID here")

    return token, chat_id


def step_write_env(token: str, chat_id: str) -> None:
    heading("Step 4 — Writing notifications/.env")
    env_path = REPO_ROOT / "notifications" / ".env"
    env_content = f"""# Telegram credentials
# This file is gitignored — never commit it.

TELEGRAM_BOT_TOKEN={token}
TELEGRAM_CHAT_ID={chat_id}
"""
    env_path.write_text(env_content)
    ok(f"notifications/.env written")


def step_inventory() -> None:
    heading("Step 5 — Setting up inventory spreadsheet")
    dest = REPO_ROOT / "resell_inventory.xlsx"
    template = REPO_ROOT / "resell_inventory_template.xlsx"

    if dest.exists():
        ok("resell_inventory.xlsx already exists — leaving it untouched")
        return

    if not template.exists():
        err("resell_inventory_template.xlsx not found — skipping")
        return

    shutil.copy(template, dest)
    ok(f"resell_inventory.xlsx created from template")


def step_verify(token: str, chat_id: str) -> None:
    heading("Step 6 — Verifying setup")

    # Check .env
    env_path = REPO_ROOT / "notifications" / ".env"
    if env_path.exists():
        ok("notifications/.env exists")
    else:
        err("notifications/.env not found")
        return

    # Check inventory
    inv = REPO_ROOT / "resell_inventory.xlsx"
    if inv.exists():
        ok("resell_inventory.xlsx exists")
    else:
        warn("resell_inventory.xlsx not found — run this setup again or create it manually")

    # Check config
    cfg = REPO_ROOT / "config.yaml"
    if cfg.exists():
        ok("config.yaml exists")
    else:
        warn("config.yaml not found")

    # Send test Telegram message
    print("\n  Sending a test Telegram message to verify your bot credentials...")
    try:
        import urllib.request

        test_msg = "🤖 resell-bot setup complete! Your bot is connected and ready."
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": test_msg}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        if result.get("ok"):
            ok("Test message sent! Check your Telegram — you should see it now.")
        else:
            err(f"Telegram returned an error: {result}")
    except Exception as e:
        err(f"Couldn't send test message: {e}")
        print("     Check that your bot token and chat ID are correct.")
        print("     You can fix them by editing notifications/.env directly.")


def step_done(config: dict) -> None:
    name = config.get("user", {}).get("name", "there")
    heading("Setup complete!")
    print(f"""
  Hey {name}! Your resell-bot is configured and ready to go.

  What's next:
  ─────────────────────────────────────────────────────────────
  1. Open Chrome and log in to:
       • eBay  → your seller account
       • Facebook → the account linked to your Marketplace listings

  2. In Claude (Cowork), open this folder as your workspace.

  3. To run the daily listing check:
       Read and follow: skills/scheduled-runs/morning-run.md

  4. To create your first listing:
       Read and follow: skills/create-listing/SKILL.md

  5. To set up the automated daily schedule:
       Read and follow: skills/setup/SKILL.md
  ─────────────────────────────────────────────────────────────

  Your config lives in config.yaml (gitignored).
  Your Telegram credentials live in notifications/.env (gitignored).
  Your inventory lives in resell_inventory.xlsx (gitignored).

  None of these files will be accidentally pushed to GitHub.
""")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"""
{BOLD}╔════════════════════════════════════════╗
║     resell-bot setup wizard            ║
╚════════════════════════════════════════╝{RESET}

This wizard will configure resell-bot for your machine.
It takes about 5 minutes. You can quit at any time with Ctrl+C.
""")

    check_python()
    check_dependencies()

    config = step_user_info()
    step_write_config(config)
    token, chat_id = step_telegram()
    step_write_env(token, chat_id)
    step_inventory()
    step_verify(token, chat_id)
    step_done(config)


if __name__ == "__main__":
    main()
