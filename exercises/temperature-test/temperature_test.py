"""
Temperature Test Exercise
=========================
Demonstrates how the temperature parameter changes AI output.
Runs the SAME prompt at 5 different temperature levels, multiple times each.
Saves all results in a formatted .txt file so you can compare side-by-side.

How temperature works:
  - Temperature is a decimal between 0.0 and 1.0
  - Low (0.0-0.3): deterministic, predictable, factual — picks top token almost always
  - Mid (0.4-0.7): balanced — some variety but stays on topic
  - High (0.8-1.0): creative, varied, unpredictable — spreads probability across tokens

The test proves this by asking for "a movie idea" at each temperature level.
At low temp you'll see similar responses each run. At high temp, wildly different.
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

# The prompt that will be tested at all temperature levels
# Deliberately open-ended so temperature differences are visible
TEST_PROMPT = "Give me a one-sentence movie idea."

# Temperature levels to test: low, low-mid, mid, high-mid, high
TEMPERATURES = [0.0, 0.3, 0.5, 0.7, 1.0]

# How many times to repeat at each temperature
# More runs = better proof that low temp is consistent, high temp is varied
RUNS_PER_TEMP = 3


# ---------------------------------------------------------------------------
# Helper: Chat with temperature control
# ---------------------------------------------------------------------------
# Temperature is passed as a parameter to the API call.
# It controls how the model samples from the probability distribution:
#   - 0.0: always pick the highest-probability token (deterministic)
#   - 1.0: sample more evenly across probable tokens (creative)
# This model has reasoning tokens (chain-of-thought) that count against max_tokens.
# Need higher limit so reasoning doesn't eat all the tokens before the actual answer.
def chat(messages, temperature=1.0):
    """Send messages with a specific temperature setting."""
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1000,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Run the full temperature sweep
# ---------------------------------------------------------------------------
def run_temperature_test():
    """Test the same prompt at multiple temperatures, save results."""

    # Store all results: { temperature: [response1, response2, ...] }
    results = {}

    for temp in TEMPERATURES:
        results[temp] = []
        for run in range(RUNS_PER_TEMP):
            messages = [{"role": "user", "content": TEST_PROMPT}]
            answer = chat(messages, temperature=temp)
            results[temp].append(answer)

    # --- Save results ---
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(LOGS_DIR, f"temperature_test_{timestamp}.txt")

    separator = "=" * 70
    lines = []

    # Header
    lines.append(separator)
    lines.append("  TEMPERATURE TEST RESULTS")
    lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Model: {MODEL}")
    lines.append(f"  Prompt: \"{TEST_PROMPT}\"")
    lines.append(f"  Runs per temperature: {RUNS_PER_TEMP}")
    lines.append(separator)
    lines.append("")

    # Explanation of what temperature does
    lines.append("  HOW TEMPERATURE WORKS:")
    lines.append("-" * 70)
    lines.append("  Temperature controls how the model picks the next token (word).")
    lines.append("")
    lines.append("  At each step, the model calculates probabilities for possible")
    lines.append("  next tokens. Temperature adjusts those probabilities:")
    lines.append("")
    lines.append("    temp=0.0 → Always picks the highest-probability token (deterministic)")
    lines.append("    temp=0.5 → Some variation, mostly follows top probabilities")
    lines.append("    temp=1.0 → Spreads probability evenly, more random/creative picks")
    lines.append("")
    lines.append("  You'll see below: at temp=0.0 all responses are similar.")
    lines.append("  At temp=1.0 responses are wildly different from each other.")
    lines.append("")

    # Results for each temperature level
    for temp in TEMPERATURES:
        # Category label
        if temp <= 0.3:
            category = "LOW — predictable, factual, deterministic"
        elif temp <= 0.7:
            category = "MEDIUM — balanced, some variety"
        else:
            category = "HIGH — creative, varied, unpredictable"

        lines.append(separator)
        lines.append(f"  TEMPERATURE: {temp}  ({category})")
        lines.append(separator)
        lines.append("")

        for i, response in enumerate(results[temp], 1):
            lines.append(f"  Run {i}: {response}")
            lines.append("")

    # Analysis section
    lines.append(separator)
    lines.append("  ANALYSIS: What to look for")
    lines.append(separator)
    lines.append("")
    lines.append("  1. CONSISTENCY across runs:")
    lines.append("     - At temp=0.0: all runs should be nearly identical")
    lines.append("     - At temp=1.0: each run should be different")
    lines.append("")
    lines.append("  2. CREATIVITY level:")
    lines.append("     - At temp=0.0: safe, predictable movie ideas")
    lines.append("     - At temp=1.0: wild, unexpected, creative ideas")
    lines.append("")
    lines.append("  3. When to use what:")
    lines.append("     - temp=0.0-0.3: coding, facts, data extraction, moderation")
    lines.append("     - temp=0.4-0.7: summarization, education, problem-solving")
    lines.append("     - temp=0.8-1.0: brainstorming, creative writing, marketing")
    lines.append("")

    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath, results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Running temperature test...")
    print(f"  Prompt: \"{TEST_PROMPT}\"")
    print(f"  Temperatures: {TEMPERATURES}")
    print(f"  Runs per temp: {RUNS_PER_TEMP}")
    print(f"  Total API calls: {len(TEMPERATURES) * RUNS_PER_TEMP}")
    print()

    filepath, results = run_temperature_test()

    # Print results to console too
    for temp in TEMPERATURES:
        print(f"\n  temp={temp}:")
        for i, r in enumerate(results[temp], 1):
            preview = r[:80] + ("..." if len(r) > 80 else "")
            print(f"    Run {i}: {preview}")

    print(f"\n  Full results saved to: {filepath}")
