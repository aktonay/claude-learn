"""
Streaming vs Standard Demo
==========================
Demonstrates the difference between standard (wait-for-complete) and streaming
(chunk-by-chunk) API responses. Runs BOTH modes on the same prompt, measures
timing at each stage, and saves a formatted comparison to logs/.

Why streaming matters:
  - Standard: user stares at a spinner for 10-30 seconds, then sees the full text
  - Streaming: user sees the FIRST WORD in ~1 second, text builds up live
  - Same total generation time, but streaming FEELS 10x faster

Stream events (what the API sends):
  1. MessageStart      → "I heard you, starting now"
  2. ContentBlockStart → "Starting a text block"
  3. ContentBlockDelta → "Here's a chunk of text" (this fires MANY times)
  4. ContentBlockStop  → "Text block done"
  5. MessageDelta      → "Message wrapping up"
  6. MessageStop       → "All done"

This demo uses the OpenAI-compatible streaming format (ZAI API).
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

client = OpenAI(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url=os.getenv("ZAI_BASE_URL"),
)

MODEL = "glm-4.5-air"
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")

# A prompt that generates a long enough response to see the streaming effect
# Short answers finish too fast to notice the difference
TEST_PROMPT = "Write a detailed 5-sentence description of a fictional cyberpunk city. Make it vivid and atmospheric."


# ---------------------------------------------------------------------------
# Test 1: STANDARD (non-streaming) response
# ---------------------------------------------------------------------------
# The entire response is generated BEFORE anything is returned.
# User sees nothing until the last token is generated.
def run_standard():
    """Run a standard (non-streaming) request and measure timing."""
    messages = [{"role": "user", "content": TEST_PROMPT}]

    # Time the full request
    start = time.time()

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1000,
        messages=messages,
    )

    end = time.time()

    full_text = response.choices[0].message.content
    total_time = end - start

    return {
        "mode": "STANDARD (non-streaming)",
        "full_text": full_text,
        "total_time": total_time,
        "time_to_first_token": total_time,  # user sees nothing until complete
        "tokens": response.usage.completion_tokens if response.usage else "N/A",
    }


# ---------------------------------------------------------------------------
# Test 2: STREAMING response
# ---------------------------------------------------------------------------
# Chunks arrive one by one as they're generated.
# User sees the first chunk almost immediately, then text builds up live.
def run_streaming():
    """Run a streaming request and measure timing for each chunk."""
    messages = [{"role": "user", "content": TEST_PROMPT}]

    chunks = []          # each chunk's text and timestamp
    first_chunk_time = None
    start = time.time()

    # stream=True enables chunk-by-chunk delivery
    stream = client.chat.completions.create(
        model=MODEL,
        max_tokens=1000,
        messages=messages,
        stream=True,
    )

    # Iterate over each chunk as it arrives
    for chunk in stream:
        now = time.time()

        # Each chunk has a choices array with delta.content
        if chunk.choices and chunk.choices[0].delta:
            content = chunk.choices[0].delta.content
            if content:
                if first_chunk_time is None:
                    first_chunk_time = now - start
                chunks.append({
                    "text": content,
                    "elapsed": now - start,
                })

    end = time.time()
    full_text = "".join(c["text"] for c in chunks)

    return {
        "mode": "STREAMING (chunk-by-chunk)",
        "full_text": full_text,
        "total_time": end - start,
        "time_to_first_token": first_chunk_time or 0,
        "num_chunks": len(chunks),
        "chunks": chunks,
    }


# ---------------------------------------------------------------------------
# Save comparison results
# ---------------------------------------------------------------------------
def save_results(standard_result, streaming_result):
    """Save a formatted comparison of both modes to a .txt file."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(LOGS_DIR, f"streaming_comparison_{timestamp}.txt")

    separator = "=" * 70
    lines = []

    # Header
    lines.append(separator)
    lines.append("  STREAMING vs STANDARD RESPONSE COMPARISON")
    lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Model: {MODEL}")
    lines.append(separator)
    lines.append("")

    # The prompt
    lines.append("  PROMPT USED:")
    lines.append("-" * 70)
    lines.append(f"  {TEST_PROMPT}")
    lines.append("")

    # --- Standard results ---
    lines.append(separator)
    lines.append(f"  TEST 1: {standard_result['mode']}")
    lines.append("-" * 70)
    lines.append("")
    lines.append(f"  Total time:           {standard_result['total_time']:.2f}s")
    lines.append(f"  Time to first token:  {standard_result['time_to_first_token']:.2f}s  (user sees NOTHING until this)")
    lines.append(f"  Completion tokens:    {standard_result['tokens']}")
    lines.append("")
    lines.append("  What the user experiences:")
    lines.append("    0.00s → User sends message")
    lines.append(f"    ... → User stares at a loading spinner for {standard_result['total_time']:.1f}s ...")
    lines.append(f"    {standard_result['total_time']:.2f}s → ENTIRE response appears at once")
    lines.append("")
    lines.append("  Full response:")
    lines.append("  " + "-" * 66)
    for text_line in standard_result["full_text"].split("\n"):
        lines.append(f"  {text_line}")
    lines.append("")

    # --- Streaming results ---
    lines.append(separator)
    lines.append(f"  TEST 2: {streaming_result['mode']}")
    lines.append("-" * 70)
    lines.append("")
    lines.append(f"  Total time:           {streaming_result['total_time']:.2f}s")
    lines.append(f"  Time to first chunk:  {streaming_result['time_to_first_token']:.2f}s  (user sees text IMMEDIATELY)")
    lines.append(f"  Number of chunks:     {streaming_result['num_chunks']}")
    lines.append("")
    lines.append("  What the user experiences:")
    lines.append("    0.00s → User sends message")
    lines.append(f"    {streaming_result['time_to_first_token']:.2f}s → First words appear!")
    lines.append(f"    ...  → Text builds up word by word, live")
    lines.append(f"    {streaming_result['total_time']:.2f}s → Complete response")
    lines.append("")

    # Show chunk-by-chunk timeline
    lines.append("  Chunk-by-chunk timeline (first 20 chunks):")
    lines.append("  " + "-" * 66)
    for i, chunk in enumerate(streaming_result["chunks"][:20]):
        text_preview = chunk["text"].replace("\n", "\\n")
        if len(text_preview) > 40:
            text_preview = text_preview[:40] + "..."
        lines.append(f"    {chunk['elapsed']:6.2f}s | chunk {i+1:3d} | \"{text_preview}\"")
    if len(streaming_result["chunks"]) > 20:
        lines.append(f"    ... ({len(streaming_result['chunks']) - 20} more chunks)")
    lines.append("")

    lines.append("  Full response:")
    lines.append("  " + "-" * 66)
    for text_line in streaming_result["full_text"].split("\n"):
        lines.append(f"  {text_line}")
    lines.append("")

    # --- Comparison ---
    speedup_feel = standard_result["time_to_first_token"] / max(streaming_result["time_to_first_token"], 0.01)
    lines.append(separator)
    lines.append("  HEAD-TO-HEAD COMPARISON")
    lines.append(separator)
    lines.append("")
    lines.append(f"  | Metric              | Standard   | Streaming   |")
    lines.append(f"  |---------------------|------------|-------------|")
    lines.append(f"  | Time to first text  | {standard_result['time_to_first_token']:8.2f}s  | {streaming_result['time_to_first_token']:9.2f}s   |")
    lines.append(f"  | Total time          | {standard_result['total_time']:8.2f}s  | {streaming_result['total_time']:9.2f}s   |")
    lines.append(f"  | Chunks delivered    | {'1 (bulk)':>10s} | {streaming_result['num_chunks']:>11d}   |")
    lines.append("")
    lines.append(f"  PERCEIVED speedup: {speedup_feel:.1f}x faster")
    lines.append(f"  (User sees text {standard_result['time_to_first_token']:.2f}s sooner with streaming)")
    lines.append("")
    lines.append("  KEY INSIGHT:")
    lines.append("  Total generation time is SIMILAR for both modes.")
    lines.append("  But streaming gives the FIRST token almost immediately,")
    lines.append("  making the experience FEEL dramatically faster.")
    lines.append("")
    lines.append("  When to use each:")
    lines.append("    - STANDARD: batch processing, background jobs, when you need the complete text")
    lines.append("    - STREAMING: chat UIs, real-time apps, anything a user is waiting for")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Fix Windows console encoding for emoji/special chars
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("  STREAMING vs STANDARD DEMO")
    print("=" * 60)
    print()

    # Run standard test
    print("  [1/2] Running STANDARD (non-streaming) request...")
    standard = run_standard()
    print(f"        Done in {standard['total_time']:.2f}s")
    print()

    # Run streaming test
    print("  [2/2] Running STREAMING request...")
    print()
    streaming = run_streaming()
    print(f"        Done in {streaming['total_time']:.2f}s ({streaming['num_chunks']} chunks)")
    print()

    # Save results
    filepath = save_results(standard, streaming)

    # Print summary
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print()
    print(f"  Time to first text:")
    print(f"    Standard:  {standard['time_to_first_token']:.2f}s  (user waits in silence)")
    print(f"    Streaming: {streaming['time_to_first_token']:.2f}s  (user sees text immediately)")
    print()
    print(f"  Total time:")
    print(f"    Standard:  {standard['total_time']:.2f}s")
    print(f"    Streaming: {streaming['total_time']:.2f}s")
    print()
    speedup = standard["time_to_first_token"] / max(streaming["time_to_first_token"], 0.01)
    print(f"  Perceived speedup: {speedup:.1f}x faster with streaming")
    print()
    print(f"  Full comparison saved to: {filepath}")
