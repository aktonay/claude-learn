# Project: Claude Learn

# This project is a learning sandbox for Claude Code's skills system.
# Everything here is documented for easy understanding and future reference.

## Skills Built

# Skills are task-specific instructions that Claude loads ON DEMAND (not every conversation).
# They live in .claude/skills/<skill-name>/SKILL.md
# Claude matches user requests against the skill's description to decide when to activate it.

Four skills in `.claude/skills/`:

1. **pr-description** — generates PR descriptions from git diff
   - `allowed-tools: Bash, Read, Grep, Glob` (restricts to read-only + bash for git commands)
   - `model: sonnet` (uses Claude Sonnet model for this skill)

2. **codebase-onboarding** — progressive disclosure structure
   - Has `references/`, `scripts/`, `assets/` subdirectories
   - Reference files load ONLY when the user asks a relevant topic (saves context tokens)
   - `scripts/detect-stack.sh` runs without loading into context (only output consumes tokens)

3. **accessibility-audit** — audits frontend code for WCAG 2.1 AA compliance
   - 10-point check table (alt text, form labels, contrast, keyboard nav, ARIA misuse, etc.)
   - `scripts/a11y-scan.sh` quick scan — runs without loading into context
   - `references/wcag-checklist.md` — detailed WCAG success criteria
   - `references/fix-patterns.md` — copy-paste fix patterns for common issues
   - `references/testing-tools.md` — axe-core, Lighthouse, eslint-plugin-jsx-a11y setup

4. **skill-troubleshooter** — diagnoses and fixes skill problems
   - `scripts/validate-skills.sh` — structural validator (checks frontmatter, naming, permissions, line count, description quality)
   - `references/trigger-fixes.md` — fixes for skills that don't trigger
   - `references/loading-fixes.md` — fixes for skills that don't load
   - `references/priority-fixes.md` — fixes for priority conflicts and wrong-skill-used
   - `references/runtime-fixes.md` — fixes for permission denied, path issues, missing deps

## Claude Code Customization Layers

# Each layer serves a different purpose — use the right tool for the job.
# Don't force everything into skills when another option fits better.

| Feature | Trigger | Use For |
|---------|---------|---------|
| CLAUDE.md | Every conversation | Always-on project standards, constraints, style |
| Skills | On-demand (semantic match on description) | Task-specific expertise, detailed procedures |
| Subagents | Delegated tasks | Isolated execution, separate tool access |
| Hooks | Events (file save, tool call) | Auto-lint, validation, side effects |
| MCP servers | Tool calls | External integrations, APIs |

## Skill Rules

# How skills work under the hood:
- Skills live in `.claude/skills/<name>/SKILL.md`
- Required frontmatter: `name`, `description`
- Optional: `allowed-tools`, `model`
- Priority: Enterprise > Personal (~/.claude/) > Project (.claude/) > Plugins
- Skills load at startup only — restart after changes
- Keep SKILL.md <500 lines; put details in `references/`, `scripts/`, `assets/`
- Scripts execute without loading into context — only output consumes tokens

## Custom Subagents

# Subagents are isolated execution contexts — they run tasks independently and return results.
# IMPORTANT: Subagents do NOT automatically see skills. You MUST explicitly list them.

Four agents in `.claude/agents/`:

1. **pr-reviewer** — uses `pr-description` skill, produces structured PR descriptions + flags issues
2. **codebase-explainer** — uses `codebase-onboarding` skill, guides new devs through architecture/conventions
3. **accessibility-auditor** — uses `accessibility-audit` skill, runs full a11y scan with structured report
4. **skill-troubleshooter-agent** — uses `skill-troubleshooter` skill, runs validator + provides targeted fixes

### Subagent Rules

- Subagents do NOT inherit skills automatically — must list in `skills:` frontmatter field
- Built-in agents (Explorer, Plan, Verify) cannot access skills at all
- Only custom subagents in `.claude/agents/` can use skills
- Skills load at subagent start, not on-demand like main conversation

## Sharing Strategy

# What gets shared vs what stays personal:
- `.claude/skills/` and `.claude/agents/` are committed to git — shared with team on clone
- `.claude/settings.json` is gitignored — personal per developer
- `.gitignore` blocks: secrets, env files, keys, personal settings, editor noise
- Enterprise skills (highest priority) override everything for compliance

## Conventions

- No emojis unless requested
- Concise responses preferred
