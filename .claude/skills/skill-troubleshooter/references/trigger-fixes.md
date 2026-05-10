# Trigger Fix Guide
# Fixes for: Skill exists but Claude doesn't use it when expected.

## Problem: Description Doesn't Match User's Phrasing

# Claude uses SEMANTIC MATCHING — your request must overlap with the description's meaning.
# If you say "help me profile this" but the description only says "performance analysis",
# there might not be enough overlap for a match.

### Fix: Add Trigger Phrases

# BAD — too vague, no trigger words:
description: Helps with performance.

# GOOD — includes phrases users actually say:
description: Analyzes and improves code performance. Use when the user asks about slow code,
profiling, optimizing, benchmarking, "why is this slow", "make this faster", or performance issues.

### How to Test Trigger Phrases

# After updating the description, restart Claude Code and test with variations:
# 1. The exact phrases in your description
# 2. Synonyms and natural language versions
# 3. Short versions ("profile this") and long versions ("can you help me find the bottleneck?")
# If any variation fails, add those exact words to your description.

## Problem: Description Is Too Short

# Descriptions under ~50 characters rarely trigger reliably.
# Claude needs enough text to establish semantic overlap.

### Fix: Expand the Description

# Minimum viable description structure:
# [What the skill does]. Use when [specific trigger scenarios].

# BAD:
description: Code review.

# GOOD:
description: Reviews code for bugs, style issues, and best practices. Use when the user asks
to review code, check for issues, or wants feedback on a pull request or code snippet.

## Problem: Description Is Too Generic

# If your description could apply to many skills, Claude can't distinguish them.

### Fix: Be Specific

# BAD — applies to almost any skill:
description: Helps developers with their code.

# GOOD — clearly scoped:
description: Generates structured pull request descriptions from git diffs. Use when creating
a PR, writing PR descriptions, or summarizing branch changes.
