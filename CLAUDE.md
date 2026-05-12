# Project: Claude Learn

# This project is a learning sandbox for Claude Code's skills system.
# Everything here is documented for easy understanding and future reference.

## Skills Built

# Skills are task-specific instructions that Claude loads ON DEMAND (not every conversation).
# They live in .claude/skills/<skill-name>/SKILL.md
# Claude matches user requests against the skill's description to decide when to activate it.

Five skills in `.claude/skills/`:

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

5. **system-prompt-builder** — builds project-specific system prompts
   - Saves prompts to `.claude/system-prompts/<project>.md` (version-controlled)
   - `references/prompt-templates.md` — ready-made templates by role (engineer, tutor, reviewer, writer)
   - `references/best-practices.md` — 4-dimension framework (Role, Behavior, Constraints, Style)
   - `references/api-patterns.md` — OpenAI vs Anthropic system prompt patterns

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

Five agents in `.claude/agents/`:

1. **pr-reviewer** — uses `pr-description` skill, produces structured PR descriptions + flags issues
2. **codebase-explainer** — uses `codebase-onboarding` skill, guides new devs through architecture/conventions
3. **accessibility-auditor** — uses `accessibility-audit` skill, runs full a11y scan with structured report
4. **skill-troubleshooter-agent** — uses `skill-troubleshooter` skill, runs validator + provides targeted fixes
5. **system-prompt-builder-agent** — uses `system-prompt-builder` skill, creates/tests project prompts

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

## Exercises

# Hands-on exercises in exercises/ folder, each self-contained:
- `exercises/multi-turn-chatbot/` — multi-turn conversation with helper functions + log saving
- `exercises/system-prompts/` — system prompt comparison test (with vs without) + results saved to txt
- `exercises/temperature-test/` — temperature sweep (0.0 to 1.0) with same prompt, results saved to txt
- `exercises/streaming-demo/` — streaming vs standard response comparison with chunk-by-chunk timeline
- `exercises/structured-output/` — prefilling + stop sequences for clean JSON/code/commands (no commentary)
- `exercises/prompt-eval/` — full evaluation pipeline: dataset generation, V1 vs V2 prompts, code grader (syntax) + model grader (quality), combined scoring with formatted report
- `exercises/prompt-eval-engineering/` — iterative prompt engineering: 4 techniques (be clear, be specific, XML tags, provide examples) measured step-by-step with HTML visual report

## API Configuration

# ZAI API key lives in root .env (gitignored)
# Base URL: https://api.z.ai/api/coding/paas/v4/
# Available models: glm-4.5, glm-4.5-air, glm-4.6, glm-4.7, glm-5, glm-5-turbo, glm-5.1
# IMPORTANT: All GLM models are reasoning models by default. They consume max_tokens
# on internal chain-of-thought, leaving 0 visible output when budget is too low.
# Fix: Pass extra_body={"thinking": {"type": "disabled"}} to disable reasoning.
# This makes responses fast and direct without wasting tokens on hidden reasoning.
