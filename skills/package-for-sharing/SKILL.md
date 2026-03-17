---
name: package-for-sharing
description: "Transform a project built for personal use into something anyone can clone and use themselves. Audits the project for hardcoded personal data, extracts settings into a config layer, builds an interactive setup script, templatizes documentation, adds first-run guards, and creates an AI-guided setup skill. Use this when you want to share a project you originally built just for yourself."
---

# Package for Sharing

This skill transforms a personal project into a shareable one — anyone can clone it and get it running for their own situation with minimal friction.

---

## When to use this skill

- You built something for yourself and now want to share it with others
- Someone wants to reuse your work but needs to configure it for their own accounts/credentials
- You want to open-source a project that currently has your personal data baked in

---

## Phase 1 — Audit for personal data

Scan the project for anything that belongs to you specifically.

### What to look for

**In code and config files:**
- Hardcoded names, usernames, account IDs
- Email addresses, phone numbers
- API keys, tokens, passwords (especially any NOT already in `.env`)
- Personal file paths
- Hardcoded URLs pointing to your personal accounts (eBay seller page, FB profile, etc.)

**In documentation:**
- Your name used as if it's everyone's name (e.g. "David sends photos" instead of "the user sends photos")
- References to your specific accounts or setup
- "For me" language instead of "for you" language

**Data files:**
- Spreadsheets, databases, JSON files with your actual data
- Should these be gitignored, or replaced with empty templates?

### How to audit

```bash
# Search for common personal identifiers in text files
grep -r "your-name\|your-username\|your-email" --include="*.md" --include="*.py" --include="*.yaml" --include="*.json" .

# Find .env files that might not be gitignored
find . -name ".env" -not -path "./.git/*"

# Check what's currently gitignored vs tracked
git ls-files | head -50
cat .gitignore
```

Document findings as a list: **[file] → [what needs to change]**

---

## Phase 2 — Design the config layer

Decide what belongs in user config vs. what's project-level constants.

**Goes in config** (varies by user):
- Name, username, account IDs
- Preferences (speed vs. price, notification style, etc.)
- Which services/platforms they use

**Stays in code** (same for everyone):
- API endpoint URLs
- Logic, thresholds, business rules
- Skill instructions

### Create config.example.yaml

```yaml
# [Project name] configuration
# ---
# Copy this file to config.yaml and fill in your values.
# config.yaml is gitignored — never commit it.
# Run `python3 setup.py` to be guided through this automatically.

user:
  name: ""            # Your first name

# Add other sections based on what the project needs
```

### Create config.yaml (your personal version, gitignored)

Same structure but with your actual values filled in.

### Update .gitignore

```
# Personal data — gitignored so others get a clean slate on clone
config.yaml
[any personal data files]
```

---

## Phase 3 — Create data file templates

For any data files that contain your personal data (spreadsheets, databases, JSON):

1. Create a `*_template.*` version with just the structure (headers, schema) and no data
2. Gitignore the real file
3. The setup script will copy the template → real file for new users

Example:
- `resell_inventory.xlsx` (gitignored, contains your listings)
- `resell_inventory_template.xlsx` (tracked, headers only)

---

## Phase 4 — Build the setup script

Create `setup.py` (or `setup.sh` if the project is shell-based) that guides new users through configuration.

### Structure

```python
#!/usr/bin/env python3
"""
[Project] setup wizard
Run: python3 setup.py
"""

# 1. Pre-flight checks
#    - Python version, dependencies installed

# 2. Collect user info
#    - Ask questions in plain English
#    - Validate inputs before accepting

# 3. Handle third-party service setup
#    - Walk through creating accounts/bots/tokens step by step
#    - Include exact instructions with links
#    - Pause and wait for user to complete each step

# 4. Write config files
#    - config.yaml from answers
#    - .env from credentials

# 5. Set up data files
#    - Copy templates to working files

# 6. Verify everything works
#    - Test each integration (send a test message, check DB connection, etc.)
#    - Clear error messages if anything fails

# 7. Print "what's next" summary
```

### Key UX principles for setup scripts

- **Plain English only** — no jargon, no assumed knowledge
- **One thing at a time** — don't ask multiple questions at once
- **Pause and wait** — for steps that require the user to do something in another app, pause with `input("Press Enter when done...")`
- **Show exactly what to do** — include links, exact commands, screenshots descriptions
- **Validate before proceeding** — check that the token/credential actually works before moving on
- **Graceful failures** — if something fails, explain what went wrong and how to fix it
- **Idempotent** — running it twice should not break anything; detect existing config and skip or confirm

---

## Phase 5 — Templatize documentation

Update all docs to use generic "you/the user" language instead of your name.

### Find-and-replace list

Go through each doc file and:
- Replace your name with "the user" (in skill/technical docs) or "you" (in README/user-facing docs)
- Replace your account IDs with "your [account type]" or a config reference like `config.yaml → selling.ebay_username`
- Change "For me" / "For David" framing to "For you" framing
- Change "I want" to "You might want"

### README.md rewrite checklist

- [ ] Opening paragraph describes what the tool does for *anyone*, not for you specifically
- [ ] "Getting Started" section is the first thing after the description
- [ ] Setup instructions point to `python3 setup.py`, not to manual credential copying
- [ ] No personal account names/IDs anywhere
- [ ] Troubleshooting covers the most common new-user failure modes

### CLAUDE.md / project instructions checklist

- [ ] References `config.yaml` for user-specific values instead of hardcoding them
- [ ] Includes a "first-run check" section that detects missing setup
- [ ] Behavioral rules are framed as defaults, not as personal preferences

---

## Phase 6 — Add first-run guards

Detect missing setup at runtime and guide the user to fix it instead of crashing.

### Entry point guard (Python)

```python
from pathlib import Path

REPO_ROOT = Path(__file__).parent

def check_setup() -> None:
    missing = []
    if not (REPO_ROOT / "config.yaml").exists():
        missing.append("config.yaml")
    if not (REPO_ROOT / "notifications" / ".env").exists():
        missing.append("notifications/.env")
    if missing:
        print(
            f"Setup incomplete. Missing: {', '.join(missing)}\n"
            "Run `python3 setup.py` to get everything configured."
        )
        raise SystemExit(1)
```

### CLAUDE.md guard

Add a section at the top of CLAUDE.md that instructs Claude to check for config files before doing anything and redirect to setup if they're missing.

---

## Phase 7 — Create an AI-guided setup skill

If the project uses Claude/Cowork, create a `skills/setup/SKILL.md` that walks new users through the same steps as the setup script but conversationally, with Claude holding their hand the whole way.

The setup skill should:
1. Check what's already done (don't redo finished steps)
2. Walk through each stage clearly
3. Handle the parts the script can't — like opening a browser to log in
4. Verify each step before proceeding
5. End with a summary of what's set up and what to do next

Structure:
```markdown
## Before you begin
[check what's already done]

## Stage 1 — [name]
[step-by-step instructions]
[verification command]

## Stage 2 — [name]
...

## Final summary
[what got set up, what to do next]
```

---

## Phase 8 — Validate end-to-end

The final step: prove it works for a real new user.

```bash
# Simulate a fresh clone
cd /tmp
git clone [your-repo-url] test-clone
cd test-clone

# Verify the clean state
ls config.yaml         # should not exist
ls notifications/.env  # should not exist

# Run setup
python3 setup.py

# Verify it created the right files
ls config.yaml
ls notifications/.env
ls resell_inventory.xlsx   # or whatever your data file is
```

Then do a real end-to-end test: run the main workflow and confirm it works with the freshly-configured setup.

If anything breaks during validation, fix it and re-run until it passes cleanly.

---

## Checklist — "is it ready to share?"

- [ ] No personal names, usernames, or account IDs hardcoded anywhere in tracked files
- [ ] All credentials are in `.env` (gitignored)
- [ ] All personal preferences are in `config.yaml` (gitignored)
- [ ] `config.example.yaml` exists and is tracked
- [ ] Personal data files are gitignored; template versions are tracked
- [ ] `python3 setup.py` works start-to-finish on a clean clone
- [ ] README opens with "what this does for you" — not "what this does for me"
- [ ] Setup instructions are the first thing in the README
- [ ] First-run guard is in place — missing setup gives a helpful error, not a crash
- [ ] Validated with a fresh clone
