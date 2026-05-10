# Loading Fix Guide
# Fixes for: Skill doesn't appear in the available skills list at all.

## Problem: Wrong File Name

# The file MUST be named exactly "SKILL.md" — case-sensitive.
# These will NOT work: skill.md, Skills.md, SKILL.MD, Skill.md

### Fix: Rename the File

# Check with:
ls -la .claude/skills/<skill-name>/

# If the file is wrong, rename:
mv .claude/skills/<skill-name>/skill.md .claude/skills/<skill-name>/SKILL.md

## Problem: SKILL.md at Skills Root (not in a subdirectory)

# Skills must be inside a NAMED DIRECTORY — not directly in the skills folder.
# The structure MUST be: .claude/skills/<skill-name>/SKILL.md

### Fix: Create Proper Directory Structure

# BAD — SKILL.md directly in skills/:
.claude/skills/SKILL.md              # WRONG

# GOOD — SKILL.md inside a named directory:
.claude/skills/my-skill/SKILL.md     # CORRECT

# Fix:
mkdir .claude/skills/my-skill
mv .claude/skills/SKILL.md .claude/skills/my-skill/SKILL.md

## Problem: Missing or Malformed Frontmatter

# SKILL.md must start with --- on the very first line.
# The frontmatter block must have opening and closing --- delimiters.

### Fix: Check Frontmatter Structure

# CORRECT structure:
# ---
# name: my-skill
# description: Does something useful.
# ---

# WRONG — no closing dashes:
# ---
# name: my-skill
# description: Does something useful.
# (missing closing ---)

# WRONG — extra content before frontmatter:
# # My Skill          ← this line prevents frontmatter parsing
# ---
# name: my-skill
# ---

## Problem: Missing Required Fields

# 'name' and 'description' are both REQUIRED.
# Skill will silently fail to load if either is missing.

### Fix: Add Missing Fields

# Check for required fields:
grep -E "^name:|^description:" .claude/skills/<skill-name>/SKILL.md

# If missing, add them to the frontmatter between the --- delimiters.

## Problem: Changes Not Picked Up

# Skills load at STARTUP ONLY — changes mid-session are invisible.

### Fix: Restart Claude Code

# After ANY change to SKILL.md:
# 1. Exit Claude Code (Ctrl+C or /exit)
# 2. Start a new session
# 3. Check /skills to verify

## Problem: Wrong Directory Location

# Claude Code only scans these locations:
# 1. Enterprise (managed settings)
# 2. Personal: ~/.claude/skills/
# 3. Project: .claude/skills/ (inside repo root)
# 4. Plugins

# Custom paths like .pr-skills/, .my-skills/, etc. are INVISIBLE to Claude Code.

### Fix: Move to a Supported Location

# For project-level (shared with team):
mv .pr-skills/skills/my-skill .claude/skills/my-skill

# For personal (works across all projects):
mv .pr-skills/skills/my-skill ~/.claude/skills/my-skill
