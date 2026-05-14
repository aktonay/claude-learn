# Claude Learn

A learning sandbox for exploring Claude Code, AI SDKs, and LLM capabilities using the ZAI API (GLM models).

## What This Repo Contains

This repo is a hands-on learning playground built while following the Claude Code course. Every exercise is self-contained with its own code, logs, and output files.

## API Configuration

All exercises use the **ZAI API** (not Anthropic/OpenAI directly).

- Base URL: `https://api.z.ai/api/coding/paas/v4/`
- Available models: `glm-4.5`, `glm-4.5-air`, `glm-4.6`, `glm-4.7`, `glm-5`, `glm-5-turbo`, `glm-5.1`
- API key is stored in root `.env` (gitignored)

Note: GLM models are reasoning models by default. They consume `max_tokens` on internal chain-of-thought. Disable reasoning with `extra_body={"thinking": {"type": "disabled"}}` for faster direct responses.

## Exercises Completed

### Part 1: API Basics

| Exercise | What It Does | Output |
|----------|-------------|--------|
| `multi-turn-chatbot` | Multi-turn conversation with helper functions | Chat logs saved to txt |
| `system-prompts` | System prompt comparison (with vs without) | Results in txt |
| `temperature-test` | Temperature sweep 0.0 to 1.0 with same prompt | Results in txt |
| `streaming-demo` | Streaming vs standard response, chunk-by-chunk timeline | Comparison log |

### Part 2: Prompt Engineering

| Exercise | What It Does | Output |
|----------|-------------|--------|
| `structured-output` | Prefilling + stop sequences for clean JSON/code | Structured outputs |
| `prompt-eval` | Full eval pipeline: auto dataset, V1 vs V2 prompts, code + model grader | txt report |
| `prompt-eval-engineering` | 4 techniques (clear, specific, XML tags, examples) measured step-by-step | txt log + HTML report |
| `prompt-caching` | Prompt caching experiments | |

### Part 3: Advanced Features

| Exercise | What It Does | Output |
|----------|-------------|--------|
| `tool-use` | Multi-turn tool calling: 3 tools (datetime, date math, reminders), agentic chaining | Conversation trace logs |
| `rag` | Full RAG pipeline: chunking (4 strategies), VoyageAI embeddings, VectorIndex + BM25Index, hybrid Retriever (RRF fusion) | 3-query comparison log |
| `thinking-test` | Extended thinking: 3 modes (disabled, budget, enabled), accuracy + speed + token trade-offs | txt + HTML report |
| `vision` | Vision API: naive vs structured prompts, multi-image comparison | Requires images in `images/` subfolder |
| `pdf-citations` | 3 citation approaches (baseline, inline, structured JSON) with verification | Citation logs |
| `code-execution` | Client-side code execution via tool calling: direct analysis, one-shot generation, agentic loop | Analysis output |
| `mcp` | Full MCP project: FastMCP server (tools, resources, prompts) + CLI chatbot with @mentions, /commands, autonomous tool use | Working client/server |

### Part 4: UIGen App

| Exercise | What It Does |
|----------|-------------|
| `uigen` | AI-powered React component generator with live preview. Adapted to use ZAI API with `glm-5-turbo`. |

Setup: `cd exercises/uigen && npm run setup && npm run dev` then open http://localhost:3000

## Claude Code Customization

This repo also demonstrates Claude Code's customization system:

### Skills (`.claude/skills/`)

On-demand instructions loaded by semantic matching:

1. **pr-description** — PR descriptions from git diff
2. **codebase-onboarding** — progressive disclosure for new devs
3. **accessibility-audit** — WCAG 2.1 AA compliance checks
4. **skill-troubleshooter** — diagnose and fix skill problems
5. **system-prompt-builder** — project-specific system prompts

### Custom Subagents (`.claude/agents/`)

Isolated execution contexts with skill access:

1. **pr-reviewer** — PR descriptions + issue flags
2. **codebase-explainer** — architecture walkthroughs
3. **accessibility-auditor** — full a11y scans
4. **skill-troubleshooter-agent** — validator + targeted fixes
5. **system-prompt-builder-agent** — create/test system prompts

### Customization Layers

| Layer | Trigger | Purpose |
|-------|---------|---------|
| CLAUDE.md | Every conversation | Always-on project standards |
| Skills | On-demand semantic match | Task-specific expertise |
| Subagents | Delegated tasks | Isolated execution |
| Hooks | Events (file save, tool call) | Auto-lint, validation |
| MCP servers | Tool calls | External integrations |

## Progress Timeline

| Date | Milestone |
|------|-----------|
| May 10 | First commit, Part 1 basics (multi-turn, system prompts, temperature, streaming) |
| May 11 | Accessing Claude, prompt caching |
| May 12 | Prompt eval, prompt engineering, tool use, RAG |
| May 13 | PDF generation |
| May 14 | Vision, code execution, MCP, UIGen app setup, full completion |

## Tech Stack

- ZAI API (GLM models via OpenAI-compatible endpoint)
- VoyageAI (embeddings for RAG)
- Next.js 15, React 19 (UIGen)
- Prisma + SQLite (UIGen)
- Vercel AI SDK
- FastMCP (MCP exercise)
- Python (code execution exercise)
- Claude Code skills system
