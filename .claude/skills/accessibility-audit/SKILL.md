---
# ACCESSIBILITY AUDIT SKILL
# Audits frontend code for WCAG 2.1 AA compliance issues.
# Activates when user asks about accessibility, a11y, WCAG, or screen reader support.
# Uses progressive disclosure — reference docs load only when needed.
name: accessibility-audit
description: Audits frontend code for accessibility issues. Use when the user asks about accessibility, a11y, WCAG compliance, screen reader support, or wants an accessibility review of their code.
allowed-tools: Read, Grep, Glob, Bash
model: sonnet
---

# Accessibility Audit Skill
# Walks through code looking for common WCAG 2.1 AA violations.
# Produces a structured report with severity levels and fix suggestions.

When auditing for accessibility:

## Step 1: Identify All UI Components

# First, find all frontend files so we know what to audit
- Run `Glob` to find all `.tsx`, `.jsx`, `.html`, `.vue`, `.svelte` files
- Focus on components that render interactive or visual content

## Step 2: Run Checks

# These are the core checks — run ALL of them on every relevant file
- Use `Grep` to search for each pattern listed below
- Record every match as a finding

| Check | What to grep for | Severity |
|-------|-----------------|----------|
| Missing alt text | `<img` without `alt=` | HIGH |
| Empty links | `<a>` with no text content | HIGH |
| Missing form labels | `<input` without associated `<label>` or `aria-labelledby` | HIGH |
| Low contrast text | Inline styles with light colors on light backgrounds | MEDIUM |
| Missing lang attribute | `<html` without `lang=` | MEDIUM |
| Keyboard traps | `tabindex="-1"` on interactive elements | HIGH |
| Missing focus styles | `:focus` not defined in CSS | MEDIUM |
| Autoplay media | `<video` or `<audio` without `autoplay=false` | MEDIUM |
| Missing skip nav | No skip-to-content link at page top | LOW |
| ARIA misuse | `role=` without corresponding behavior | HIGH |

## Step 3: Load Reference Files When Needed

# PROGRESSIVE DISCLOSURE — only load when the topic comes up
- If the user asks about **specific WCAG success criteria**, read `references/wcag-checklist.md`
- If the user asks **how to fix a specific issue**, read `references/fix-patterns.md`
- If the user asks about **testing tools**, read `references/testing-tools.md`

## Step 4: Produce Report

# Standard output format for the audit
Format findings as:

### Accessibility Audit Report

**Files scanned:** N
**Issues found:** N

| # | File | Line | Check | Severity | Fix |
|---|------|------|-------|----------|-----|
| 1 | ... | ... | ... | HIGH/MEDIUM/LOW | One-line fix |

**Summary:** X HIGH, Y MEDIUM, Z LOW issues
