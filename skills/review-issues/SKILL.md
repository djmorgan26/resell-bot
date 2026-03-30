---
name: review-issues
description: "Review and act on issues logged by other skills. Use this skill when the user wants to see what problems have occurred, debug recurring issues, or optimize skill behavior. Reads from logs/issues/ where each skill writes its own JSON log file. Provides summaries, identifies patterns, and suggests fixes. Trigger when the user mentions: review issues, check errors, what went wrong, skill problems, debug skills, optimize skills, or issue log."
---

# Review Issues: Skill Diagnostics & Optimization

You help the user review problems that other skills have encountered, identify patterns, and fix recurring issues.

## Before You Start

Read all issue log files in `logs/issues/`:

```bash
ls [WORKSPACE]/logs/issues/*.json 2>/dev/null
```

Each skill writes its own log file:
- `organize-photos.json` — photo intake, naming, dedup issues
- `create-listing.json` — research, pricing, listing creation issues
- `manage-listings.json` — marketplace monitoring, auto-reply issues

---

## What This Skill Does

### 1. Summarize Recent Issues

Read each log file and present a summary:

```
── Issues Summary ──────────────────────────────────

organize-photos: 3 issues (1 unresolved)
  - 2x naming convention violations (resolved)
  - 1x duplicate detection failure (unresolved)

create-listing: 1 issue (0 unresolved)
  - 1x eBay publish timeout (resolved — Chrome reconnect)

manage-listings: 0 issues
────────────────────────────────────────────────────
```

### 2. Identify Patterns

Look for:
- **Repeated issues** — same type of error happening multiple times
- **Skill-specific weaknesses** — one skill consistently failing at a particular step
- **Chrome/browser issues** — timeouts, login expirations, CSP blocks
- **Data issues** — inventory mismatches, missing photos, stale URLs

### 3. Suggest Fixes

For each pattern, suggest a concrete fix:
- Update the skill's SKILL.md with better instructions
- Add a workaround step for known browser quirks
- Update user-preferences.yaml if a preference is causing friction
- Flag items in the inventory that need manual attention

### 4. Act on Fixes (with user approval)

If the user agrees to a fix:
- Edit the relevant SKILL.md
- Update preferences
- Fix inventory data
- Clear resolved issues from the log

---

## Issue Log Format

Each entry in a skill's JSON log looks like:

```json
{
  "timestamp": "2026-03-30T10:15:00",
  "type": "category of issue",
  "description": "what happened",
  "resolution": "what was done, or 'unresolved'",
  "item": "item folder name if applicable"
}
```

### Common issue types by skill:

**organize-photos:** `naming`, `duplicate`, `conversion`, `misplaced`, `other`
**create-listing:** `research`, `pricing`, `description`, `publish`, `chrome`, `inventory`, `other`
**manage-listings:** `chrome`, `auto-reply`, `offer-eval`, `inventory`, `stale-listing`, `other`

---

## Clearing Resolved Issues

After reviewing, offer to clear resolved issues:

```bash
source [WORKSPACE]/.venv/bin/activate
python3 - << 'EOF'
import json
from pathlib import Path

for log_file in Path("[WORKSPACE]/logs/issues").glob("*.json"):
    issues = json.loads(log_file.read_text())
    unresolved = [i for i in issues if i["resolution"] == "unresolved"]
    log_file.write_text(json.dumps(unresolved, indent=2))
    cleared = len(issues) - len(unresolved)
    if cleared:
        print(f"{log_file.name}: cleared {cleared} resolved, {len(unresolved)} remaining")
EOF
```

---

## Optimization Workflow

When the user wants to optimize a skill based on issues:

1. Read the skill's issue log
2. Read the skill's SKILL.md
3. Identify which instructions led to the issues
4. Propose specific edits to the SKILL.md
5. Get user approval
6. Apply the edits
7. Clear the related issues from the log

---

## What NOT To Do

- Don't delete issue logs without asking
- Don't modify skill files without user approval
- Don't dismiss unresolved issues — they need attention
- Don't over-optimize — if an issue happened once and was resolved, it might not need a skill change
