#!/usr/bin/env python3
"""
resell-bot setup wizard
-----------------------
Run this once to configure resell-bot for your machine.
It will walk you through creating config.yaml and user-preferences.yaml,
then verify everything is working.

Usage:
    python3 setup.py
"""

import os
import shutil
import sys
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
        import openpyxl  # noqa: F401
        ok("Python dependencies installed")
    except ImportError as e:
        err(f"Missing dependency: {e}")
        print("     Run: pip install -r requirements.txt")
        sys.exit(1)


# ── steps ─────────────────────────────────────────────────────────────────────

def step_user_info() -> dict:
    heading("Step 1 — About you")
    print("  This helps personalize skill behavior and listings.\n")

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
        f.write("# This file is gitignored — it contains your personal settings.\n")
        f.write("# See user-preferences.yaml for detailed selling preferences.\n\n")
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    ok(f"config.yaml written to {config_path}")


def step_preferences(config: dict) -> None:
    heading("Step 3 — Setting up user-preferences.yaml")
    prefs_path = REPO_ROOT / "user-preferences.yaml"
    template_path = REPO_ROOT / "user-preferences.yaml.template"

    if prefs_path.exists():
        ok("user-preferences.yaml already exists — leaving it untouched")
        print("     You can edit it anytime to adjust your selling preferences.")
        return

    if not template_path.exists():
        err("user-preferences.yaml.template not found — cannot create preferences file")
        return

    # Copy the template
    content = template_path.read_text()

    # Fill in required fields from config answers
    name = config.get("user", {}).get("name", "")
    ebay_username = config.get("selling", {}).get("ebay_username", "")
    priority = config.get("selling", {}).get("priority", "speed")
    marketplaces = config.get("marketplaces", ["ebay", "fb_marketplace"])

    # Replace blank required fields with user's answers
    content = content.replace('  name: ""', f'  name: "{name}"', 1)
    content = content.replace('  ebay_username: ""', f'  ebay_username: "{ebay_username}"', 1)
    content = content.replace('  priority: ""', f'  priority: "{priority}"', 1)

    # Update marketplace list
    mp_block = "  marketplaces:                         # required: true — which platforms to list on\n"
    for mp in marketplaces:
        mp_block += f'    - "{mp}"\n'

    import re
    content = re.sub(
        r'  marketplaces:.*?(?=\n# )',
        mp_block,
        content,
        count=1,
        flags=re.DOTALL,
    )

    prefs_path.write_text(content)
    ok("user-preferences.yaml created with your settings")
    print("     You can edit this file anytime to adjust preferences.")


def step_inventory() -> None:
    heading("Step 4 — Setting up inventory spreadsheet")
    dest = REPO_ROOT / "resell_inventory.xlsx"
    template = REPO_ROOT / "resell_inventory_template.xlsx"

    if dest.exists():
        ok("resell_inventory.xlsx already exists — leaving it untouched")
        return

    if not template.exists():
        err("resell_inventory_template.xlsx not found — skipping")
        return

    shutil.copy(template, dest)
    ok("resell_inventory.xlsx created from template")


def step_verify() -> None:
    heading("Step 5 — Verifying setup")

    # Check inventory
    inv = REPO_ROOT / "resell_inventory.xlsx"
    if inv.exists():
        ok("resell_inventory.xlsx exists")
    else:
        warn("resell_inventory.xlsx not found — run setup again or create manually")

    # Check config
    cfg = REPO_ROOT / "config.yaml"
    if cfg.exists():
        ok("config.yaml exists")
    else:
        warn("config.yaml not found")

    # Check preferences
    prefs = REPO_ROOT / "user-preferences.yaml"
    if prefs.exists():
        ok("user-preferences.yaml exists")
    else:
        warn("user-preferences.yaml not found")

    # Check logs/issues directory
    issues_dir = REPO_ROOT / "logs" / "issues"
    if issues_dir.exists():
        ok("logs/issues/ directory exists")
    else:
        issues_dir.mkdir(parents=True, exist_ok=True)
        ok("logs/issues/ directory created")


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

  3. To create your first listing:
       Tell Claude: "I want to list a new item"
       Or follow: skills/create-listing/SKILL.md

  4. To check on your listings:
       Tell Claude: "Check my listings"
       Or follow: skills/manage-listings/SKILL.md

  5. To organize photos:
       Tell Claude: "Organize my photos"
       Or follow: skills/organize-photos/SKILL.md
  ─────────────────────────────────────────────────────────────

  Your config lives in config.yaml (gitignored).
  Your preferences live in user-preferences.yaml (gitignored).
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
It takes about 2 minutes. You can quit at any time with Ctrl+C.
""")

    check_python()
    check_dependencies()

    config = step_user_info()
    step_write_config(config)
    step_preferences(config)
    step_inventory()
    step_verify()
    step_done(config)


if __name__ == "__main__":
    main()
