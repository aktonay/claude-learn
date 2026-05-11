---
# SYSTEM PROMPT BUILDER SKILL
# Helps users create, test, and manage project-specific system prompts.
# System prompts define HOW the AI should behave for a given project.
# Stored in .claude/system-prompts/<project-name>.md so teams can share them.
name: system-prompt-builder
description: Builds and manages project-specific system prompts. Use when the user wants to create, edit, test, or apply a system prompt for their project. Also use when setting up AI behavior rules for a codebase.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
model: sonnet
---

# System Prompt Builder Skill
# Helps design project-specific system prompts that shape AI behavior.

## What System Prompts Do

# System prompts are the "persona" or "rules" that shape how the AI responds.
# Without one: AI gives generic, direct answers.
# With one: AI follows the behavior, tone, and constraints you define.
# They are NOT part of the conversation — they sit above it as instructions.

## Where System Prompts Live

# Project-specific system prompts are stored as markdown files:
#   .claude/system-prompts/<project-name>.md
# This way they're version-controlled and shared with the team via git.

## How to Build a System Prompt

When the user asks to create a system prompt, follow this structure:

### Step 1: Understand the Use Case

# Ask the user:
# - What is this project about? (domain, audience)
# - What tone/style should the AI use? (formal, casual, technical, beginner-friendly)
# - What should the AI always do? (give hints, write tests, use specific frameworks)
# - What should the AI never do? (give direct answers, use certain patterns, skip docs)

### Step 2: Write the Prompt Using This Template

# Write the system prompt to .claude/system-prompts/<project-name>.md
# using this structure:

"""
# System Prompt: <Project Name>

## Role
You are a <specific role — e.g., "senior Python engineer", "patient math tutor">.

## Behavior Rules
- <Rule 1: what to always do>
- <Rule 2: another always-do rule>
- <Rule 3: etc.>

## Constraints
- <Constraint 1: what to never do>
- <Constraint 2: etc.>

## Output Style
- <Style preference: concise, verbose, bullet points, step-by-step>
- <Format preferences: code blocks, markdown, plain text>
"""

### Step 3: Validate the Prompt

# Check that the prompt covers these 4 dimensions:
# 1. ROLE — who is the AI acting as?
# 2. BEHAVIOR — what should it do?
# 3. CONSTRAINTS — what should it NOT do?
# 4. STYLE — how should it format responses?

# If any dimension is missing, suggest additions.

### Step 4: Test the Prompt

# Offer to test the prompt by:
# 1. Sending a sample question WITHOUT the system prompt
# 2. Sending the SAME question WITH the system prompt
# 3. Showing both results side-by-side
# This proves the prompt actually changes behavior.

## Loading Reference Files

# PROGRESSIVE DISCLOSURE — load only when the topic comes up
- If the user asks for **example prompts by role**, read `references/prompt-templates.md`
- If the user asks **best practices for writing prompts**, read `references/best-practices.md`
- If the user asks about **API implementation details**, read `references/api-patterns.md`
