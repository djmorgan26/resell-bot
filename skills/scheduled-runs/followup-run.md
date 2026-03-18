# Followup Run — Act on the user's Telegram Replies

This is the orchestration doc for the follow-up scheduled run (typically 1 hour after the morning run). It checks for the user's Telegram replies and executes any decisions they made.

---

## Step 1 — Find the workspace

```bash
find /sessions -name "resell_inventory.xlsx" 2>/dev/null | head -1 | xargs dirname
```

Store the result as WORKSPACE.

---

## Step 2 — Fix Chrome if needed

If Chrome tools are timing out, follow the "Fixing Chrome timeouts" instructions in `[WORKSPACE]/CLAUDE.md`.

---

## Step 3 — Run the followup skill

Read and follow `[WORKSPACE]/skills/followup/SKILL.md`.

This skill handles everything:
- Reading the user's Telegram replies from `consumed_updates.json` (written by the poll bot)
- Falling back to Chrome JS if the poll bot isn't running
- Reading `pending_actions.json` to match replies to actions
- Sending buyer replies in the browser
- Resolving handled actions
- Updating inventory
- Sending Telegram confirmation

If the user hasn't replied yet, the skill exits cleanly with no message sent.
