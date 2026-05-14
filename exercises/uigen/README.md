# UIGen

AI-powered React component generator with live preview.

## Prerequisites

- Node.js 18+
- npm

## Setup

1. Install dependencies and initialize the database:

```bash
npm run setup
```

> **Don't run `npm audit fix`.** Dependencies are pinned to specific versions that work together. The vulnerability warnings are cosmetic for a local-only project, and `audit fix` can bump packages past compatible versions and break the app.

This command will:

- Install all dependencies
- Generate Prisma client
- Run database migrations (SQLite)

2. Configure the `.env` file with your ZAI API credentials:

```
ZAI_API_KEY=your-zai-api-key
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4/
```

The project falls back to a mock provider (canned components) if no API key is set.

## Running the Application

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Usage

1. Sign up or continue as anonymous user
2. Describe the React component you want to create in the chat
3. View generated components in real-time preview
4. Switch to Code view to see and edit the generated files
5. Continue iterating with the AI to refine your components

## Features

- AI-powered component generation
- Live preview with hot reload
- Virtual file system (no files written to disk)
- Syntax highlighting and code editor
- Component persistence for registered users
- Export generated code

## Tech Stack

- Next.js 15 with App Router
- React 19
- TypeScript
- Tailwind CSS v4
- Prisma with SQLite
- ZAI API (glm-5-turbo) via OpenAI-compatible provider
- Vercel AI SDK

## Changes from Original

The original project used the Anthropic Claude API (`@ai-sdk/anthropic`). It has been adapted to use the ZAI API with `glm-5-turbo` (fast model) via `@ai-sdk/openai-compatible`. Key changes:

- `src/lib/provider.ts` — replaced Anthropic provider with ZAI OpenAI-compatible provider, reads `ZAI_API_KEY` and `ZAI_BASE_URL` from `.env`
- `src/app/api/chat/route.ts` — removed Anthropic-specific `providerOptions` cache control, updated mock provider check to use `ZAI_API_KEY`
- `.env` — uses `ZAI_API_KEY` and `ZAI_BASE_URL` instead of `ANTHROPIC_API_KEY`
