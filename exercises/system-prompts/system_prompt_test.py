"""
System Prompt Exercise
======================
Demonstrates how system prompts change Claude's behavior.
Runs the SAME question twice — once WITHOUT system prompt, once WITH.
Saves both results side-by-side in a formatted .txt file so you can compare.

Key concept:
  - WITHOUT system prompt: Claude answers normally (direct, generic)
  - WITH system prompt: Claude follows the persona you define
  - System prompt is NOT a message in the conversation — it's a separate parameter
"""

import os
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
# Helper: Send chat with OPTIONAL system prompt
# ---------------------------------------------------------------------------
# Two ways to pass system prompts depending on the API:
#
# 1. Anthropic Claude API: system is a SEPARATE parameter (not in messages)
#    client.messages.create(system="...", messages=[...])
#
# 2. OpenAI-compatible APIs (like ZAI): system is a MESSAGE with role "system"
#    It goes as the FIRST message in the messages array.
#
# This exercise uses approach #2 since we're hitting the ZAI OpenAI-compatible API.
def chat(messages, system_prompt=None):
    """Send messages to the API with an optional system prompt."""
    # If a system prompt is given, prepend it as a system-role message
    # This is the OpenAI-compatible way — system message goes first in the array
    if system_prompt:
        all_messages = [{"role": "system", "content": system_prompt}] + messages
    else:
        all_messages = messages

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1000,
        messages=all_messages,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# The test: same question, two different behaviors
# ---------------------------------------------------------------------------
def run_comparison():
    """Run the same question with and without a system prompt, save results."""

    # The question we'll ask both times
    user_question = "How do I solve 5x + 2 = 3 for x?"

    # The system prompt that transforms behavior from "answer directly"
    # to "guide step by step like a tutor"
    system_prompt = (
        "You are a patient math tutor.\n"
        "Do not directly answer a student's questions.\n"
        "Guide them to a solution step by step.\n"
        "Ask questions to make the student think.\n"
        "Give hints, not solutions."
    )

    # --- Test 1: WITHOUT system prompt ---
    messages_no_system = [
        {"role": "user", "content": user_question}
    ]
    answer_no_system = chat(messages_no_system, system_prompt=None)

    # --- Test 2: WITH system prompt ---
    messages_with_system = [
        {"role": "user", "content": user_question}
    ]
    answer_with_system = chat(messages_with_system, system_prompt=system_prompt)

    # --- Save the comparison ---
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(LOGS_DIR, f"system_prompt_comparison_{timestamp}.txt")

    separator = "=" * 70
    lines = []
    lines.append(separator)
    lines.append("  SYSTEM PROMPT COMPARISON TEST")
    lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Model: {MODEL}")
    lines.append(separator)
    lines.append("")

    # Section 1: The question
    lines.append("  THE QUESTION:")
    lines.append("-" * 70)
    lines.append(f"  {user_question}")
    lines.append("")

    # Section 2: The system prompt
    lines.append(separator)
    lines.append("  THE SYSTEM PROMPT (only used in Test 2):")
    lines.append("-" * 70)
    for line in system_prompt.split("\n"):
        lines.append(f"  {line}")
    lines.append("")

    # Section 3: WITHOUT system prompt
    lines.append(separator)
    lines.append("  TEST 1: WITHOUT SYSTEM PROMPT (default behavior)")
    lines.append("  Expected: Direct answer with full solution")
    lines.append(separator)
    lines.append("")
    for line in answer_no_system.split("\n"):
        lines.append(f"  {line}")
    lines.append("")

    # Section 4: WITH system prompt
    lines.append(separator)
    lines.append("  TEST 2: WITH SYSTEM PROMPT (math tutor persona)")
    lines.append("  Expected: Guiding questions, hints, no direct answer")
    lines.append(separator)
    lines.append("")
    for line in answer_with_system.split("\n"):
        lines.append(f"  {line}")
    lines.append("")

    # Section 5: Analysis
    lines.append(separator)
    lines.append("  ANALYSIS: What changed?")
    lines.append(separator)
    lines.append("")
    lines.append("  WITHOUT system prompt:")
    lines.append("    - Claude gives a complete step-by-step solution immediately")
    lines.append("    - Student doesn't need to think — just reads the answer")
    lines.append("")
    lines.append("  WITH system prompt (math tutor):")
    lines.append("    - Claude asks guiding questions instead of giving answers")
    lines.append("    - Student is prompted to think and participate")
    lines.append("    - Response style matches a real tutor, not a calculator")
    lines.append("")
    lines.append("  This is why system prompts matter — same question, completely")
    lines.append("  different behavior. You control HOW Claude responds, not just WHAT.")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath, answer_no_system, answer_with_system


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Running system prompt comparison test...")
    print()

    filepath, no_system, with_system = run_comparison()

    print("=" * 60)
    print("  WITHOUT SYSTEM PROMPT:")
    print("=" * 60)
    print(no_system)
    print()

    print("=" * 60)
    print("  WITH SYSTEM PROMPT (math tutor):")
    print("=" * 60)
    print(with_system)
    print()

    print(f"  Results saved to: {filepath}")
