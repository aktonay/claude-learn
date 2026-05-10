---
# SKILL TROUBLESHOOTER
# Diagnoses and fixes problems with Claude Code skills.
# Activates when user reports a skill not working, not triggering, or having errors.
# Uses progressive disclosure — detailed fix guides load only when needed.
name: skill-troubleshooter
description: Diagnoses and fixes Claude Code skill problems. Use when a skill doesn't trigger, doesn't load, has priority conflicts, or fails at runtime. Also use when the user asks to validate or test their skills.
allowed-tools: Read, Grep, Glob, Bash
model: sonnet
---

# Skill Troubleshooter
# Systematic diagnosis for skill problems — always start with validation.

When troubleshooting a skill issue:

## Step 1: Run the Validator First

# The validator catches 90% of structural problems automatically.
# Run it before doing any manual debugging.
- Run `bash scripts/validate-skills.sh .claude/skills` to check all skills for structural issues
- If the validator reports errors, fix those first before investigating further

## Step 2: Identify the Problem Category

# Ask the user which symptom they're seeing:
# A) Skill doesn't trigger (Claude doesn't use it)
# B) Skill doesn't load (not in available skills list)
# C) Wrong skill gets used (confusion between skills)
# D) Priority conflict (higher-priority skill shadows it)
# E) Runtime error (loads but fails during execution)

Based on the answer, load the appropriate reference:

## Step 3: Load Reference Files When Needed

# PROGRESSIVE DISCLOSURE — only load the guide for the specific problem
- If **skill doesn't trigger** → read `references/trigger-fixes.md`
- If **skill doesn't load** → read `references/loading-fixes.md`
- If **priority conflict** → read `references/priority-fixes.md`
- If **runtime error** → read `references/runtime-fixes.md`

## Step 4: Apply Fix and Re-validate

# After fixing, always re-run the validator to confirm
- Run `bash scripts/validate-skills.sh .claude/skills` again
- Verify the skill appears in `/skills` after restarting Claude Code
