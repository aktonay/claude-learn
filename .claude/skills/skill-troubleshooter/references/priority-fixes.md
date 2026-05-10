# Priority Fix Guide
# Fixes for: The wrong skill gets used, or your skill is being shadowed.

## Understanding the Priority Hierarchy

# When two skills have the same name, this order determines which wins:
#
# 1. ENTERPRISE    (managed settings)     — highest priority, always wins
# 2. PERSONAL      (~/.claude/skills/)    — your home directory skills
# 3. PROJECT       (.claude/skills/)      — repo-level skills
# 4. PLUGINS       (installed plugins)    — lowest priority
#
# A higher-priority skill with the same name completely shadows lower ones.

## Problem: Enterprise Skill Shadows Yours

# If your company has an enterprise skill with the same name as yours,
# the enterprise version ALWAYS wins — you cannot override it.

### Fix: Rename Your Skill

# This is usually the easiest path:
# Instead of:    name: code-review
# Use:           name: custom-code-review
# Or:            name: frontend-review

# Remember to also rename the directory to match:
mv .claude/skills/code-review .claude/skills/custom-code-review

## Problem: Personal Skill Shadows Project Skill

# If you have ~/.claude/skills/pr-description/ AND .claude/skills/pr-description/,
# the personal one (home directory) wins.

### Fix Option A: Rename One of Them

# Give them distinct names so both can coexist:
# Personal:    name: personal-pr-description
# Project:     name: team-pr-description

### Fix Option B: Remove the Personal Version

# If the project version is the one you want:
rm -rf ~/.claude/skills/pr-description

## Problem: Skills Have Similar Descriptions

# Even with different names, similar descriptions can cause confusion.
# Claude might pick the wrong one based on description overlap.

### Fix: Make Descriptions Distinct

# BAD — two skills with overlapping descriptions:
# Skill A: description: Reviews code for issues.
# Skill B: description: Analyzes code for problems.

# GOOD — clearly differentiated:
# Skill A: description: Reviews pull requests for bugs and security issues. Use when reviewing PRs.
# Skill B: description: Analyzes code performance and suggests optimizations. Use when profiling.

### Fix: Use Descriptive Names

# Generic names cause confusion:
# BAD:  review, check, analyze
# GOOD: frontend-review, security-check, performance-analyze

## Problem: Plugin Skills Not Appearing

# Installed a plugin but can't see its skills?

### Fix: Clear Cache and Reinstall

# Step 1: Clear Claude Code plugin cache
# Step 2: Restart Claude Code
# Step 3: Reinstall the plugin
# Step 4: Check /skills again

# If still missing, the plugin's internal structure might be wrong.
# Run the validator against the plugin's skill files.
