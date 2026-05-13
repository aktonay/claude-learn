"""
Prompt Caching Exercise
=======================
Demonstrates prompt caching concepts and measures the performance
impact of repeated requests with identical content.

NOTE: Prompt caching is an Anthropic Claude API feature. The ZAI
OpenAI-compatible API does NOT support cache_control breakpoints
or return cache_creation/cache_read token counts.

This exercise:
  1. Explains how prompt caching works (conceptual)
  2. Measures repeated requests to simulate caching behavior
  3. Shows the Anthropic API structure for reference
  4. Compares request timing with large vs small system prompts
  5. Saves a formatted report to logs/

Key concepts:
  - Without caching: every request re-processes the ENTIRE input
  - With caching: first request writes to cache, follow-ups read from it
  - Cache lives for 1 hour, minimum 1024 tokens to be eligible
  - Cache breakpoints: manual markers on specific blocks
  - Order: tools -> system prompt -> messages
  - Up to 4 breakpoints per request
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

client = OpenAI(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url=os.getenv("ZAI_BASE_URL"),
)

MODEL = "glm-4.5-air"
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")


# ===================================================================
# CHAT HELPERS
# ===================================================================

def chat(messages, max_tokens=100):
    start = time.time()
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=messages,
        extra_body={"thinking": {"type": "disabled"}},
    )
    elapsed = time.time() - start
    return {
        "content": resp.choices[0].message.content or "",
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        "elapsed": elapsed,
    }


# ===================================================================
# LARGE SYSTEM PROMPT (to simulate real caching scenarios)
# ===================================================================

LARGE_SYSTEM = """You are an expert coding assistant. Follow these rules carefully:

1. LANGUAGE & FRAMEWORK:
   - Use TypeScript with strict mode enabled
   - Follow the Next.js App Router conventions
   - Use Tailwind CSS for all styling
   - Prefer React Server Components over Client Components
   - Use Zod for all runtime validation

2. CODE STYLE:
   - Use const over let, never use var
   - Prefer arrow functions for React components
   - Use descriptive variable names (no single letters except loops)
   - Add JSDoc comments for exported functions
   - Use template literals over string concatenation

3. ERROR HANDLING:
   - Always wrap async operations in try/catch
   - Use Result type for functions that can fail
   - Never catch and swallow errors silently
   - Log errors with context (function name, inputs)
   - Show user-friendly error messages in UI

4. SECURITY:
   - Validate all user inputs on the server side
   - Use parameterized queries for database access
   - Never expose internal error details to clients
   - Sanitize HTML to prevent XSS attacks
   - Use CSRF tokens for state-changing operations

5. DATABASE:
   - Use Prisma as the ORM
   - Define all models in schema.prisma
   - Use transactions for multi-step operations
   - Add indexes for frequently queried fields
   - Use soft deletes (deletedAt) instead of hard deletes

6. TESTING:
   - Write tests for all business logic
   - Use Vitest for unit tests, Playwright for E2E
   - Aim for 80% code coverage minimum
   - Test edge cases and error paths
   - Use factory functions for test data

7. API DESIGN:
   - Use RESTful conventions for endpoints
   - Return proper HTTP status codes
   - Paginate list endpoints (default 20 per page)
   - Version the API (e.g., /api/v1/users)
   - Use consistent error response format

8. PERFORMANCE:
   - Implement caching headers for static assets
   - Use streaming for large responses
   - Lazy load below-the-fold content
   - Optimize images with next/image
   - Minimize client-side JavaScript bundle size
"""

SHORT_SYSTEM = "You are a helpful assistant."


# ===================================================================
# TEST 1: REPEATED REQUESTS WITH LARGE SYSTEM PROMPT
# ===================================================================
# Simulates the caching scenario: same large prompt sent multiple times.
# On Anthropic API with caching: request 1 writes, requests 2-N read.
# On ZAI (no caching): every request reprocesses everything.

def test_repeated_requests(num_runs=3):
    results = []
    question = "What are 3 best practices for API error handling?"

    for i in range(num_runs):
        r = chat([
            {"role": "system", "content": LARGE_SYSTEM},
            {"role": "user", "content": question},
        ])
        results.append({
            "run": i + 1,
            "prompt_tokens": r["prompt_tokens"],
            "completion_tokens": r["completion_tokens"],
            "elapsed": r["elapsed"],
        })
        print(f"        Run {i+1}: {r['elapsed']:.2f}s, {r['prompt_tokens']} prompt tokens")
        time.sleep(1)

    return results


# ===================================================================
# TEST 2: GROWING CONVERSATION (multi-turn)
# ===================================================================
# Simulates a conversation where context grows each turn.
# With caching: only the NEW message gets processed fresh.
# Without caching: entire conversation reprocessed every turn.

def test_growing_conversation():
    messages = [{"role": "system", "content": LARGE_SYSTEM}]
    results = []
    questions = [
        "What is TypeScript strict mode?",
        "How do I set up Prisma with Next.js?",
        "Explain React Server Components.",
    ]

    for i, q in enumerate(questions, 1):
        messages.append({"role": "user", "content": q})
        r = chat(messages)
        messages.append({"role": "assistant", "content": r["content"]})
        results.append({
            "turn": i,
            "question": q,
            "prompt_tokens": r["prompt_tokens"],
            "completion_tokens": r["completion_tokens"],
            "elapsed": r["elapsed"],
            "total_messages": len(messages),
        })
        print(f"        Turn {i}: {r['elapsed']:.2f}s, {r['prompt_tokens']} tokens, {len(messages)} messages")
        time.sleep(1)

    return results


# ===================================================================
# TEST 3: SHORT vs LARGE SYSTEM PROMPT COMPARISON
# ===================================================================

def test_system_prompt_size():
    question = "What is REST?"
    results = []

    for label, system in [("Short system", SHORT_SYSTEM), ("Large system", LARGE_SYSTEM)]:
        r = chat([
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ])
        results.append({
            "label": label,
            "prompt_tokens": r["prompt_tokens"],
            "completion_tokens": r["completion_tokens"],
            "elapsed": r["elapsed"],
            "system_length": len(system),
        })
        print(f"        {label}: {r['elapsed']:.2f}s, {r['prompt_tokens']} tokens")
        time.sleep(1)

    return results


# ===================================================================
# TXT REPORT
# ===================================================================

def save_report(test1, test2, test3, timestamp_str):
    os.makedirs(LOGS_DIR, exist_ok=True)
    filepath = os.path.join(LOGS_DIR, f"prompt_caching_{timestamp_str}.txt")

    sep = "=" * 70
    dash = "-" * 70
    lines = []

    lines.append(sep)
    lines.append("  PROMPT CACHING EXERCISE REPORT")
    lines.append(f"  Date: {timestamp_str}")
    lines.append(f"  Model: {MODEL}")
    lines.append(sep)
    lines.append("")

    lines.append(sep)
    lines.append("  WHAT IS PROMPT CACHING?")
    lines.append(sep)
    lines.append("")
    lines.append("  When you send a request to an LLM:")
    lines.append("    1. Tokenize the prompt into pieces")
    lines.append("    2. Create embeddings for each token")
    lines.append("    3. Add context based on surrounding text")
    lines.append("    4. Generate the output")
    lines.append("")
    lines.append("  Without caching: steps 1-3 are DISCARDED after each request.")
    lines.append("  With caching: steps 1-3 are SAVED for reuse (up to 1 hour).")
    lines.append("")
    lines.append("  This means:")
    lines.append("    - First request: normal speed (writes to cache)")
    lines.append("    - Follow-up requests: faster + cheaper (reads from cache)")
    lines.append("    - Only works if content is IDENTICAL up to the cache breakpoint")
    lines.append("")
    lines.append("  ANTHROPIC API STRUCTURE (reference):")
    lines.append("  -------------------------------")
    lines.append("  Add cache_control to specific blocks:")
    lines.append("")
    lines.append("    # System prompt caching")
    lines.append('    params["system"] = [{')
    lines.append('        "type": "text",')
    lines.append('        "text": system_prompt,')
    lines.append('        "cache_control": {"type": "ephemeral"}')
    lines.append('    }]')
    lines.append("")
    lines.append("    # Tool schema caching (add to last tool)")
    lines.append('    tools_clone = tools.copy()')
    lines.append('    last_tool = tools_clone[-1].copy()')
    lines.append('    last_tool["cache_control"] = {"type": "ephemeral"}')
    lines.append('    tools_clone[-1] = last_tool')
    lines.append("")
    lines.append("    # Message block caching")
    lines.append('    {"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}')
    lines.append("")
    lines.append("  CACHE RULES:")
    lines.append("    - Minimum 1024 tokens to be eligible")
    lines.append("    - Cache lives for 1 hour")
    lines.append("    - Up to 4 breakpoints per request")
    lines.append("    - Processing order: tools -> system prompt -> messages")
    lines.append("    - ANY change to cached content invalidates the entire cache")
    lines.append("")
    lines.append("  RESPONSE USAGE FIELDS (Anthropic API):")
    lines.append("    cache_creation_input_tokens: tokens written to cache (first request)")
    lines.append("    cache_read_input_tokens: tokens read from cache (follow-ups)")
    lines.append("")
    lines.append(f"  NOTE: ZAI API does NOT support prompt caching.")
    lines.append("  This exercise measures what caching WOULD optimize.")
    lines.append("")

    lines.append(sep)
    lines.append("  TEST 1: REPEATED REQUESTS WITH LARGE SYSTEM PROMPT")
    lines.append(sep)
    lines.append("")
    lines.append(f"  System prompt: {len(LARGE_SYSTEM)} chars (~{test1[0]['prompt_tokens']} tokens)")
    lines.append(f"  Same question asked {len(test1)} times.")
    lines.append("")
    lines.append("  Without caching: every request processes the full system prompt.")
    lines.append("  With caching: only request 1 processes it, requests 2-N read cache.")
    lines.append("")
    lines.append(f"  {'Run':>4s} | {'Time':>8s} | {'Prompt Tokens':>14s} | {'Completion':>10s}")
    lines.append("  " + "-" * 50)
    for r in test1:
        lines.append(f"  {r['run']:4d} | {r['elapsed']:7.2f}s | {r['prompt_tokens']:14d} | {r['completion_tokens']:10d}")
    avg_time = sum(r["elapsed"] for r in test1) / len(test1)
    lines.append("")
    lines.append(f"  Average time: {avg_time:.2f}s")
    lines.append(f"  Wasted reprocessing: {len(test1) - 1} full re-processes of {test1[0]['prompt_tokens']} tokens")
    lines.append(f"  With caching: would save ~{(len(test1)-1) * avg_time:.1f}s total")
    lines.append("")

    lines.append(sep)
    lines.append("  TEST 2: GROWING CONVERSATION (multi-turn)")
    lines.append(sep)
    lines.append("")
    lines.append("  Each turn sends ALL previous messages back (LLMs are stateless).")
    lines.append("  With caching: only the NEW message gets fresh processing.")
    lines.append("  Without caching: entire conversation reprocessed every turn.")
    lines.append("")
    lines.append(f"  {'Turn':>4s} | {'Messages':>8s} | {'Prompt Tok':>10s} | {'Time':>8s} | Question")
    lines.append("  " + "-" * 65)
    for r in test2:
        q_short = r["question"][:35]
        lines.append(f"  {r['turn']:4d} | {r['total_messages']:8d} | {r['prompt_tokens']:10d} | {r['elapsed']:7.2f}s | {q_short}")
    lines.append("")
    lines.append("  Token growth: each turn adds ~200-400 tokens of conversation.")
    lines.append("  Without caching: turn 3 reprocesses ALL tokens from turns 1+2+3.")
    lines.append("  With caching: turn 3 only processes the new user message.")
    lines.append("")

    lines.append(sep)
    lines.append("  TEST 3: SHORT vs LARGE SYSTEM PROMPT")
    lines.append(sep)
    lines.append("")
    lines.append(f"  {'Type':15s} | {'Chars':>8s} | {'Prompt Tok':>10s} | {'Time':>8s}")
    lines.append("  " + "-" * 50)
    for r in test3:
        lines.append(f"  {r['label']:15s} | {r['system_length']:8d} | {r['prompt_tokens']:10d} | {r['elapsed']:7.2f}s")
    lines.append("")
    if len(test3) == 2:
        time_diff = test3[1]["elapsed"] - test3[0]["elapsed"]
        token_diff = test3[1]["prompt_tokens"] - test3[0]["prompt_tokens"]
        lines.append(f"  Large prompt costs {token_diff} extra tokens per request.")
        lines.append(f"  Over 100 requests: {token_diff * 100} tokens wasted without caching.")
    lines.append("")

    lines.append(sep)
    lines.append("  KEY TAKEAWAYS")
    lines.append(sep)
    lines.append("")
    lines.append("  1. PROMPT CACHING saves processing when you repeat identical content")
    lines.append("     - First request: writes to cache (normal speed + cost)")
    lines.append("     - Follow-up requests: reads from cache (faster + cheaper)")
    lines.append("")
    lines.append("  2. BEST USE CASES:")
    lines.append("     - Large system prompts sent with every request")
    lines.append("     - Tool definitions that don't change between calls")
    lines.append("     - Multi-turn conversations where history grows")
    lines.append("     - Document analysis workflows (same doc, different questions)")
    lines.append("")
    lines.append("  3. REQUIREMENTS:")
    lines.append("     - Minimum 1024 tokens of content")
    lines.append("     - Content must be IDENTICAL (any change invalidates cache)")
    lines.append("     - Cache lives 1 hour")
    lines.append("     - Up to 4 breakpoints per request")
    lines.append("")
    lines.append("  4. NOT WORTH IT WHEN:")
    lines.append("     - Each request has unique content")
    lines.append("     - System prompts are short (<1024 tokens)")
    lines.append("     - Requests are infrequent (>1 hour apart)")
    lines.append("")
    lines.append("  5. ZAI API STATUS:")
    lines.append("     - Does NOT support prompt caching")
    lines.append("     - Every request is fully processed from scratch")
    lines.append("     - Anthropic Claude API supports it natively")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


# ===================================================================
# MAIN
# ===================================================================

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print(f"  PROMPT CACHING EXERCISE (model: {MODEL})")
    print("=" * 60)
    print()

    print("  [1/3] Repeated requests with large system prompt...")
    test1 = test_repeated_requests(3)
    print()

    print("  [2/3] Growing conversation (multi-turn)...")
    test2 = test_growing_conversation()
    print()

    print("  [3/3] Short vs large system prompt comparison...")
    test3 = test_system_prompt_size()
    print()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = save_report(test1, test2, test3, timestamp)

    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print()
    print(f"  Repeated requests: avg {sum(r['elapsed'] for r in test1)/len(test1):.2f}s, "
          f"{test1[0]['prompt_tokens']} tokens each (all reprocessed)")
    print(f"  Growing conversation: turn 1={test2[0]['elapsed']:.2f}s -> "
          f"turn {len(test2)}={test2[-1]['elapsed']:.2f}s "
          f"({test2[-1]['prompt_tokens']} tokens)")
    print(f"  Short system: {test3[0]['elapsed']:.2f}s, "
          f"Large system: {test3[1]['elapsed']:.2f}s")
    print()
    print(f"  Report: {filepath}")
