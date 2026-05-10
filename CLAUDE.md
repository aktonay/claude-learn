# Project: Claude Learn

Learning and experimenting with Claude Code skills system.

## Skills Built

Two skills in `.claude/skills/`:

1. **pr-description** — generates PR descriptions from git diff (allowed-tools: Bash, Read, Grep, Glob, model: sonnet)
2. **codebase-onboarding** — progressive disclosure structure with `references/`, `scripts/`, `assets/` subdirectories; loads reference files only when relevant topic is asked

## Claude Code Customization Layers

| Feature | Trigger | Use For |
|---------|---------|---------|
| CLAUDE.md | Every conversation | Always-on project standards, constraints, style |
| Skills | On-demand (semantic match on description) | Task-specific expertise, detailed procedures |
| Subagents | Delegated tasks | Isolated execution, separate tool access |
| Hooks | Events (file save, tool call) | Auto-lint, validation, side effects |
| MCP servers | Tool calls | External integrations, APIs |

## Skill Rules

- Skills live in `.claude/skills/<name>/SKILL.md`
- Required frontmatter: `name`, `description`
- Optional: `allowed-tools`, `model`
- Priority: Enterprise > Personal (~/.claude/) > Project (.claude/) > Plugins
- Skills load at startup only — restart after changes
- Keep SKILL.md <500 lines; put details in `references/`, `scripts/`, `assets/`
- Scripts execute without loading into context — only output consumes tokens

## Conventions

- No emojis unless requested
- No comments in code unless requested
- Concise responses preferred
