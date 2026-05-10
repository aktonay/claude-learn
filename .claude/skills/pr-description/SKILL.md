---
# SKILL.MD FRONTMATTER
# name: (required) identifier — lowercase, numbers, hyphens only, max 64 chars
# description: (required) tells Claude WHEN to use this skill, max 1024 chars
# allowed-tools: (optional) restricts which tools Claude can use when this skill is active
# model: (optional) which Claude model to use for this skill
name: pr-description
description: Writes pull request descriptions. Use when creating a PR, writing a PR, or when the user asks to summarize changes for a pull request.
allowed-tools: Bash, Read, Grep, Glob
model: sonnet
---

# PR Description Skill
# This skill activates when the user asks to create/write a PR description.
# It reads the git diff and formats a structured PR description.

When writing a PR description:

# Step 1: Get the full diff of all changes on this branch vs main
1. Run `git diff main...HEAD` to see all changes on this branch

# Step 2: Format the output using the template below
2. Write a description following this format:

## What
# One clear sentence summarizing what this PR does (the "what", not the "why")
One sentence explaining what this PR does.

## Why
# Brief context — why was this change needed? What problem does it solve?
Brief context on why this change is needed

## Changes
# Bullet list of specific changes — group related items together
# Mention any files that were deleted or renamed
- Bullet points of specific changes made
- Group related changes together
- Mention any files deleted or renamed
