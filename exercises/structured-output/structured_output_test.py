"""
Structured Output Exercise
===========================
Demonstrates how to get CLEAN structured data from the API with zero commentary.
Uses two techniques combined:

1. ASSISTANT MESSAGE PREFILLING:
   - You add a fake "assistant" message BEFORE the API responds
   - The model thinks it already started writing, so it CONTINUES in that format
   - E.g., prefill "```json\n" → model continues with pure JSON inside the code block

2. STOP SEQUENCES:
   - You specify a string that triggers IMMEDIATE stop of generation
   - E.g., stop on "```" → model stops right before closing the code block
   - Result: pure JSON, no markdown wrapping, no explanations

Combined: prefill opens the format, stop sequence closes it.
You get EXACTLY the data you want — nothing before, nothing after.

This is critical for building apps where output goes directly into:
  - JSON parsers (API pipelines, config generators)
  - Code execution (generated scripts)
  - CSV importers (data pipelines)
  - Copy-paste workflows (no manual cleanup needed)
"""

import os
import sys
import json
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


# ---------------------------------------------------------------------------
# Helper: Chat with optional stop sequence
# ---------------------------------------------------------------------------
def chat(messages, stop=None):
    """Send messages with optional stop sequence."""
    params = {
        "model": MODEL,
        "max_tokens": 1000,
        "messages": messages,
    }
    # Stop sequence: when the model generates this string, it STOPS immediately
    # This is how you prevent the model from adding closing markdown or explanations
    if stop:
        params["stop"] = stop

    response = client.chat.completions.create(**params)
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Demo 1: DEFAULT — no prefill, no stop sequence
# ---------------------------------------------------------------------------
# Shows the problem: model adds markdown wrapping + explanations
def demo_default():
    """Get JSON output the default way — includes commentary."""
    messages = [
        {"role": "user", "content": "Generate a short EventBridge rule as JSON that captures EC2 instance state changes when instances start running."}
    ]
    # No system prompt, no stop — shows default behavior with markdown wrapping
    return chat(messages)


# ---------------------------------------------------------------------------
# Demo 2: WITH EXPLICIT INSTRUCTIONS + STOP SEQUENCE — clean JSON
# ---------------------------------------------------------------------------
# For this model, system-role messages cause reasoning tokens to eat the output.
# Instead, we put format instructions IN the user message + use stop sequences.
# This works reliably across OpenAI-compatible APIs.
def demo_clean_json():
    """Get pure JSON using explicit instructions + stop sequence."""
    messages = [
        {"role": "user", "content":
            "Output ONLY raw valid JSON. No markdown code blocks. No backticks. "
            "No explanation. Start with { end with }. "
            "Generate an EventBridge rule as JSON that captures EC2 instance state changes when instances start running."
        },
    ]

    # Stop sequence as safety net — cuts off markdown or commentary
    return chat(messages, stop=["```"])


# ---------------------------------------------------------------------------
# Demo 3: Get 3 shell commands — no comments, no explanations
# ---------------------------------------------------------------------------
# Strict instruction in user message constrains format
def demo_three_commands():
    """Get exactly 3 shell commands with no commentary."""
    messages = [
        {"role": "user", "content":
            "Output ONLY 3 raw shell commands. One per line. "
            "No numbers. No explanations. No comments. No descriptions. No markdown. "
            "Just the raw commands, nothing else. "
            "Give me: 1) create a git branch called 'feature', 2) add all files, 3) commit with message 'update'."
        },
    ]

    # Stop before any explanation appears (fewer stop words — max 4 allowed)
    return chat(messages, stop=["These are", "Explanation"])


# ---------------------------------------------------------------------------
# Demo 4: Generate a Python function — no comments, no docstrings
# ---------------------------------------------------------------------------
# Explicit format instruction + stop sequence to prevent markdown wrapping
def demo_clean_python():
    """Get pure Python code using explicit instructions + stop sequence."""
    messages = [
        {"role": "user", "content":
            "Output ONLY raw Python code. No markdown code blocks. No backticks. "
            "No explanations. No docstrings. No comments. "
            "Write a function called has_duplicates that takes a string and returns True if it has duplicate characters."
        },
    ]

    # Stop when it tries to close a code block or add explanation
    return chat(messages, stop=["```", "This function", "The function"])


# ---------------------------------------------------------------------------
# Run all demos and save results
# ---------------------------------------------------------------------------
def run_all_demos():
    """Run all 4 demos and save comparison results."""

    print("  [1/4] Running DEFAULT (no prefill, no stop)...")
    default_output = demo_default()

    print("  [2/4] Running CLEAN JSON (prefill + stop)...")
    clean_json_output = demo_clean_json()

    print("  [3/4] Running 3 COMMANDS (prefill + stop)...")
    commands_output = demo_three_commands()

    print("  [4/4] Running CLEAN PYTHON (prefill + stop)...")
    clean_python_output = demo_clean_python()

    # --- Save results ---
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(LOGS_DIR, f"structured_output_{timestamp}.txt")

    separator = "=" * 70
    lines = []

    lines.append(separator)
    lines.append("  STRUCTURED OUTPUT TECHNIQUES COMPARISON")
    lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Model: {MODEL}")
    lines.append(separator)
    lines.append("")

    # How it works
    lines.append("  HOW IT WORKS:")
    lines.append("-" * 70)
    lines.append("")
    lines.append("  TECHNIQUE 1: Explicit Format Instructions in User Message")
    lines.append("  ─────────────────────────────────────────")
    lines.append("  Put strict format rules directly in the user message:")
    lines.append("  'Output ONLY raw JSON. No markdown. No backticks. Start with { end with }.'")
    lines.append("  This constrains the model's output format before it even starts.")
    lines.append("")
    lines.append("    messages = [")
    lines.append('      {"role": "user", "content": "Output ONLY raw JSON..."}')
    lines.append("    ]")
    lines.append("")
    lines.append("  NOTE: On some models, system-role messages cause reasoning tokens")
    lines.append("  to consume the output. Putting instructions in the user message")
    lines.append("  works more reliably across different API providers.")
    lines.append("")
    lines.append("  TECHNIQUE 2: Stop Sequences")
    lines.append("  ─────────────────────────────────────────")
    lines.append("  You specify a string that triggers IMMEDIATE stop of generation.")
    lines.append("  When the model generates that string, output is cut off right there.")
    lines.append("  Safety net in case the model tries to add commentary.")
    lines.append("")
    lines.append('    response = client.chat.completions.create(')
    lines.append('        ..., stop=["```"]  ← STOP SEQUENCE')
    lines.append("    )")
    lines.append("")
    lines.append("  ANTHROPIC-SPECIFIC: Assistant Message Prefilling")
    lines.append("  ─────────────────────────────────────────")
    lines.append("  On Anthropic's Claude API, you can add a fake assistant message")
    lines.append("  to make Claude think it already started writing in a format:")
    lines.append("")
    lines.append("    messages = [")
    lines.append('      {"role": "user", "content": "Generate JSON..."},')
    lines.append('      {"role": "assistant", "content": "```json\\n"},  ← PREFILL (Anthropic only)')
    lines.append("    ]")
    lines.append("")
    lines.append("  COMBINED: System prompt constrains format, stop sequence cuts extras.")
    lines.append("  You get EXACTLY the data you want — nothing before, nothing after.")
    lines.append("")

    # Demo 1: Default
    lines.append(separator)
    lines.append("  DEMO 1: DEFAULT OUTPUT (no prefill, no stop sequence)")
    lines.append("  Problem: markdown wrapping + explanatory text around the JSON")
    lines.append(separator)
    lines.append("")
    lines.append("  Request: Generate an EventBridge rule as JSON")
    lines.append("")
    lines.append("  Raw output:")
    lines.append("  " + "-" * 66)
    for text_line in default_output.split("\n"):
        lines.append(f"  {text_line}")
    lines.append("")

    # Demo 2: Clean JSON
    lines.append(separator)
    lines.append("  DEMO 2: CLEAN JSON (system prompt + stop sequence)")
    lines.append("  Result: pure JSON, no markdown, no explanations — ready to parse")
    lines.append(separator)
    lines.append("")
    lines.append("  Request: Generate an EventBridge rule as JSON")
    lines.append("")
    lines.append("  Raw output:")
    lines.append("  " + "-" * 66)
    for text_line in clean_json_output.split("\n"):
        lines.append(f"  {text_line}")
    lines.append("")

    # Try to parse it as JSON to prove it's valid
    lines.append("  Parse test:")
    try:
        parsed = json.loads(clean_json_output.strip())
        lines.append(f"    VALID JSON ✓ — parsed successfully with {len(str(parsed))} chars")
    except json.JSONDecodeError as e:
        lines.append(f"    INVALID JSON ✗ — {e}")
    lines.append("")

    # Demo 3: Three commands
    lines.append(separator)
    lines.append("  DEMO 3: EXACTLY 3 COMMANDS (system prompt + stop sequence)")
    lines.append("  Result: just the commands, no explanations")
    lines.append(separator)
    lines.append("")
    lines.append("  Request: 3 git commands (branch, add, commit)")
    lines.append("")
    lines.append("  Raw output:")
    lines.append("  " + "-" * 66)
    for text_line in commands_output.split("\n"):
        lines.append(f"  {text_line}")
    lines.append("")

    # Demo 4: Clean Python
    lines.append(separator)
    lines.append("  DEMO 4: CLEAN PYTHON CODE (system prompt + stop sequence)")
    lines.append("  Result: pure code, no comments, no explanations — ready to execute")
    lines.append(separator)
    lines.append("")
    lines.append("  Request: Write a function that checks for duplicate characters")
    lines.append("")
    lines.append("  Raw output:")
    lines.append("  " + "-" * 66)
    for text_line in clean_python_output.split("\n"):
        lines.append(f"  {text_line}")
    lines.append("")

    # Summary
    lines.append(separator)
    lines.append("  SUMMARY: WHEN TO USE THESE TECHNIQUES")
    lines.append(separator)
    lines.append("")
    lines.append("  | Use Case                    | System Prompt              | Stop Sequence |")
    lines.append("  |-----------------------------|----------------------------|---------------|")
    lines.append("  | JSON for API pipelines      | Only JSON, no markdown     | ```           |")
    lines.append("  | Python code for execution   | Only code, no comments     | ```           |")
    lines.append("  | Shell commands              | Only commands, one/line    | \\n\\n          |")
    lines.append("  | CSV data for import         | Only CSV rows              | ```           |")
    lines.append("  | YAML config                 | Only YAML, no markdown     | ```           |")
    lines.append("")
    lines.append("  NOTE: On Anthropic Claude API, also use assistant message prefilling")
    lines.append("  (add fake assistant message like '```json\\n' to make it continue in")
    lines.append("  that format). On OpenAI-compatible APIs, system prompts work better.")
    lines.append("")
    lines.append("  KEY INSIGHT:")
    lines.append("  Without these techniques: output needs manual cleanup before use.")
    lines.append("  With these techniques: output goes directly into your pipeline.")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath, default_output, clean_json_output, commands_output, clean_python_output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("  STRUCTURED OUTPUT TECHNIQUES")
    print("  Prefilling + Stop Sequences")
    print("=" * 60)
    print()

    filepath, default, json_out, cmds, py_out = run_all_demos()

    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print()
    print("  DEMO 1 (default):")
    print(f"    {default[:120]}...")
    print()
    print("  DEMO 2 (clean JSON):")
    print(f"    {json_out[:120]}...")
    print()
    print("  DEMO 3 (3 commands):")
    print(f"    {cmds[:120]}...")
    print()
    print("  DEMO 4 (clean Python):")
    print(f"    {py_out[:120]}...")
    print()
    print(f"  Full results saved to: {filepath}")
