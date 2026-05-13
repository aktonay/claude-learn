"""
Extended Thinking vs No Thinking Exercise
==========================================
Compares three modes of the GLM model on reasoning-heavy tasks:

  1. THINKING DISABLED — fast, direct, no reasoning tokens
  2. THINKING ENABLED (default) — model uses internal chain-of-thought
  3. THINKING ENABLED + BUDGET — reasoning with a token budget cap

Runs each mode on the same set of prompts, measures:
  - Output quality (correctness, depth, structure)
  - Speed (wall clock time)
  - Token usage (how many tokens consumed)
  - Output length

Saves results to:
  - logs/thinking_test_*.txt  — full comparison report
  - logs/thinking_test_*.html — visual report with comparison tables

Key concepts:
  - Reasoning models use hidden "thinking" tokens for chain-of-thought
  - These tokens count against max_tokens but are NOT visible in output
  - If max_tokens is too low, reasoning eats the entire budget → 0 visible output
  - Fix: either disable thinking OR set max_tokens high enough (8192+)
  - Trade-off: thinking = better reasoning but slower + more expensive

ZAI API configuration:
  - Disable: extra_body={"thinking": {"type": "disabled"}}
  - Enable with budget: extra_body={"thinking": {"type": "enabled", "budget_tokens": 2048}}
  - Enable (default): just don't pass extra_body (or omit thinking param)
"""

import os
import sys
import time
import html as html_lib
from datetime import datetime
from statistics import mean
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
# CHAT FUNCTIONS — three thinking modes
# ===================================================================

MODE_DISABLED = "thinking_disabled"
MODE_ENABLED = "thinking_enabled"
MODE_BUDGET = "thinking_budget_4096"

MODE_LABELS = {
    MODE_DISABLED: "Thinking Disabled",
    MODE_ENABLED: "Thinking Enabled (default)",
    MODE_BUDGET: "Thinking Enabled (budget: 4096)",
}

MODE_DESCRIPTIONS = {
    MODE_DISABLED: "No reasoning tokens. Model responds directly. Fast and cheap. Good for simple tasks.",
    MODE_ENABLED: "Full reasoning allowed. Model thinks first, then responds. Slower but better for complex problems. Needs high max_tokens (16384+).",
    MODE_BUDGET: "Reasoning capped at 4096 tokens. Balance between quality and speed. Model thinks within budget, then responds.",
}


def chat(prompt, mode=MODE_DISABLED, max_tokens=4096):
    """Send a prompt with the specified thinking mode. Returns result dict."""
    params = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    if mode == MODE_DISABLED:
        params["extra_body"] = {"thinking": {"type": "disabled"}}
    elif mode == MODE_BUDGET:
        params["extra_body"] = {"thinking": {"type": "enabled", "budget_tokens": 4096}}
        params["max_tokens"] = max(max_tokens, 8192)
    elif mode == MODE_ENABLED:
        params["max_tokens"] = max(max_tokens, 16384)

    start = time.time()
    resp = client.chat.completions.create(**params)
    elapsed = time.time() - start

    return {
        "content": resp.choices[0].message.content or "",
        "finish_reason": resp.choices[0].finish_reason,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "elapsed": elapsed,
        "mode": mode,
        "max_tokens": max_tokens,
    }


# ===================================================================
# TEST PROMPTS — designed to expose reasoning differences
# ===================================================================

TEST_PROMPTS = [
    {
        "name": "Bat and Ball (Classic Trap)",
        "prompt": "A bat and ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
        "category": "reasoning_trap",
        "expected": "$0.05 — most people intuitively answer $0.10 but that's wrong",
    },
    {
        "name": "Logic Puzzle",
        "prompt": "If all roses are flowers, and some flowers fade quickly, can we conclude that some roses fade quickly? Explain your reasoning.",
        "category": "logic",
        "expected": "No, we cannot conclude that. 'Some flowers fade quickly' doesn't guarantee those flowers are roses.",
    },
    {
        "name": "Code Bug Detection",
        "prompt": "def calculate_average(numbers):\n    total = 0\n    for n in numbers:\n        total += n\n    return total / len(numbers)\n\nFind any bugs in this code and explain the fix.",
        "category": "code_review",
        "expected": "Division by zero when list is empty. Fix: check if len(numbers) == 0.",
    },
    {
        "name": "Multi-step Math",
        "prompt": "A store has a 20% off sale. An item originally costs $80. After the discount, sales tax of 8% is applied. What is the final price?",
        "category": "math",
        "expected": "$69.12 — $80 * 0.8 = $64, then $64 * 1.08 = $69.12",
    },
]


# ===================================================================
# RUN THE COMPARISON
# ===================================================================

def run_comparison():
    results = {}

    for prompt_info in TEST_PROMPTS:
        name = prompt_info["name"]
        prompt = prompt_info["prompt"]
        results[name] = {"prompt_info": prompt_info, "modes": {}}

        for mode in [MODE_DISABLED, MODE_BUDGET, MODE_ENABLED]:
            label = MODE_LABELS[mode]
            print(f"  [{name[:30]:30s}] {label[:35]:35s} ...", end="", flush=True)
            try:
                r = chat(prompt, mode=mode)
                results[name]["modes"][mode] = r
                print(f" {r['elapsed']:5.1f}s, {len(r['content']):5d} chars, {r['completion_tokens']:5d} tokens, finish={r['finish_reason']}")
            except Exception as e:
                results[name]["modes"][mode] = {
                    "content": f"ERROR: {str(e)[:200]}",
                    "finish_reason": "error",
                    "completion_tokens": 0,
                    "prompt_tokens": 0,
                    "elapsed": 0,
                    "mode": mode,
                    "max_tokens": 4096,
                }
                print(f" ERROR: {str(e)[:80]}")

            time.sleep(1)

        print()

    return results


# ===================================================================
# GRADE OUTPUTS
# ===================================================================

def grade_result(prompt_info, result):
    """Grade whether the output is correct and well-reasoned."""
    content = result["content"]
    expected = prompt_info["expected"]
    prompt = prompt_info["prompt"]

    grade_prompt = f"""You are grading an AI response. Rate it on correctness and quality.

Question: {prompt}

Expected answer: {expected}

AI Response:
{content}

Grade on a 1-10 scale:
- 10: Correct answer with clear, accurate reasoning
- 7-9: Correct answer, reasoning mostly clear
- 4-6: Partially correct or missing key reasoning steps
- 1-3: Wrong answer or no reasoning shown

Output ONLY raw valid JSON. No markdown. No backticks.
{{"correct": true/false, "score": 1-10, "reasoning": "brief explanation"}}"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": grade_prompt}],
            extra_body={"thinking": {"type": "disabled"}},
        )
        import json, re
        text = resp.choices[0].message.content.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
    except Exception:
        pass
    return {"correct": False, "score": 0, "reasoning": "Grading failed"}


# ===================================================================
# TXT REPORT
# ===================================================================

def generate_txt_report(results, timestamp_str):
    sep = "=" * 70
    dash = "-" * 70

    lines = []
    lines.append(sep)
    lines.append("  EXTENDED THINKING VS NO THINKING - COMPARISON REPORT")
    lines.append(f"  Date: {timestamp_str}")
    lines.append(f"  Model: {MODEL}")
    lines.append(f"  Prompts tested: {len(TEST_PROMPTS)}")
    lines.append(sep)
    lines.append("")

    lines.append(sep)
    lines.append("  MODES EXPLAINED")
    lines.append(sep)
    lines.append("")
    for mode, label in MODE_LABELS.items():
        lines.append(f"  {label}")
        lines.append(f"    {MODE_DESCRIPTIONS[mode]}")
        lines.append("")

    lines.append(sep)
    lines.append("  SUMMARY COMPARISON")
    lines.append(sep)
    lines.append("")

    header = f"  {'Prompt':32s} | {'Disabled':>18s} | {'Budget 2048':>18s} | {'Enabled':>18s} |"
    lines.append(header)
    lines.append("  " + "-" * 68 + "|" + "-" * 20 + "|" + "-" * 20 + "|" + "-" * 20 + "|")

    for name, data in results.items():
        row = f"  {name[:32]:32s}"
        for mode in [MODE_DISABLED, MODE_BUDGET, MODE_ENABLED]:
            m = data["modes"].get(mode, {})
            grade = m.get("grade", {})
            score = grade.get("score", 0)
            elapsed = m.get("elapsed", 0)
            tokens = m.get("completion_tokens", 0)
            row += f" | {score:.0f}/10 {elapsed:4.1f}s {tokens:4d}t"
        row += " |"
        lines.append(row)

    lines.append("")

    for name, data in results.items():
        pi = data["prompt_info"]

        lines.append(sep)
        lines.append(f"  {name}")
        lines.append(f"  Category: {pi['category']}")
        lines.append(f"  Expected: {pi['expected']}")
        lines.append(sep)
        lines.append("")
        lines.append(f"  Prompt: {pi['prompt'][:200]}")
        lines.append("")

        for mode in [MODE_DISABLED, MODE_BUDGET, MODE_ENABLED]:
            m = data["modes"].get(mode, {})
            label = MODE_LABELS[mode]
            grade = m.get("grade", {})
            content = m.get("content", "")
            elapsed = m.get("elapsed", 0)
            tokens = m.get("completion_tokens", 0)
            finish = m.get("finish_reason", "?")

            lines.append(dash)
            lines.append(f"  {label}")
            lines.append(f"  Time: {elapsed:.1f}s | Tokens: {tokens} | Finish: {finish}")
            lines.append(f"  Grade: {grade.get('score', 0)}/10 | Correct: {grade.get('correct', '?')}")
            lines.append(f"  Grading reasoning: {grade.get('reasoning', 'N/A')}")
            lines.append(dash)
            lines.append("")
            for text_line in content.split("\n")[:20]:
                lines.append(f"    {text_line}")
            if content.count("\n") > 20:
                lines.append(f"    ... ({content.count(chr(10)) - 20} more lines)")
            lines.append("")

    lines.append(sep)
    lines.append("  KEY TAKEAWAYS")
    lines.append(sep)
    lines.append("")
    lines.append("  1. THINKING DISABLED is fastest but may fail on reasoning traps")
    lines.append("     Good for: simple tasks, factual queries, formatting, coding")
    lines.append("")
    lines.append("  2. THINKING ENABLED gives better reasoning but costs more tokens")
    lines.append("     The model 'thinks' first (hidden tokens), then responds")
    lines.append("     CRITICAL: max_tokens must be high enough (8192+) or you get 0 output")
    lines.append("")
    lines.append("  3. THINKING WITH BUDGET is a middle ground")
    lines.append("     Caps reasoning tokens at budget_tokens, then generates output")
    lines.append("     Balances quality vs speed/cost")
    lines.append("")
    lines.append("  4. THE DECISION IS SIMPLE:")
    lines.append("     Run your prompt WITHOUT thinking first.")
    lines.append("     If accuracy meets requirements -> done, no thinking needed.")
    lines.append("     If accuracy is too low AFTER optimizing prompt -> enable thinking.")
    lines.append("")
    lines.append("  5. IMPORTANT COMPATIBILITY:")
    lines.append("     Extended thinking is NOT compatible with:")
    lines.append("     - Temperature (must be 1.0 or omitted)")
    lines.append("     - Message prefilling (assistant messages)")
    lines.append("     - Forced tool use (tool_choice)")
    lines.append("     - Some stop sequences")

    return "\n".join(lines)


# ===================================================================
# HTML REPORT
# ===================================================================

def generate_html_report(results, timestamp_str):
    rows = ""
    for name, data in results.items():
        pi = data["prompt_info"]
        for mode in [MODE_DISABLED, MODE_BUDGET, MODE_ENABLED]:
            m = data["modes"].get(mode, {})
            grade = m.get("grade", {})
            content = m.get("content", "")
            score = grade.get("score", 0)
            elapsed = m.get("elapsed", 0)
            tokens = m.get("completion_tokens", 0)
            correct = grade.get("correct", False)

            if score >= 8:
                sc = "score-high"
            elif score >= 5:
                sc = "score-mid"
            else:
                sc = "score-low"

            rows += f"""
            <tr>
                <td>{html_lib.escape(name)}</td>
                <td>{MODE_LABELS[mode]}</td>
                <td><span class="score-badge {sc}">{score}/10</span></td>
                <td>{"Yes" if correct else "No"}</td>
                <td>{elapsed:.1f}s</td>
                <td>{tokens}</td>
                <td>{m.get('finish_reason', '?')}</td>
                <td><details><summary>Show</summary><pre>{html_lib.escape(content[:1500])}</pre></details></td>
            </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Thinking vs No Thinking - Comparison</title>
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; color: #333; }}
    .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; }}
    .header h1 {{ margin: 0 0 8px 0; }}
    .header p {{ margin: 0; opacity: 0.8; }}
    .summary {{ display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }}
    .card {{ background: white; border-radius: 8px; padding: 18px; flex: 1; min-width: 180px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-top: 4px solid #333; }}
    .card h3 {{ margin: 0 0 8px 0; font-size: 14px; color: #888; }}
    .card .val {{ font-size: 28px; font-weight: bold; }}
    .card .sub {{ font-size: 12px; color: #666; margin-top: 5px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    th {{ background: #1a1a2e; color: white; text-align: left; padding: 10px; font-size: 13px; }}
    td {{ padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 13px; vertical-align: top; }}
    tr:hover {{ background: #f8f9fa; }}
    .score-badge {{ font-weight: bold; padding: 3px 10px; border-radius: 15px; display: inline-block; }}
    .score-high {{ background: #c8e6c9; color: #2e7d32; }}
    .score-mid {{ background: #fff9c4; color: #f57f17; }}
    .score-low {{ background: #ffcdd2; color: #c62828; }}
    pre {{ background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; padding: 10px; font-size: 12px; white-space: pre-wrap; max-height: 300px; overflow-y: auto; }}
    details {{ cursor: pointer; }}
    .tip {{ background: white; border-radius: 8px; padding: 20px; margin-top: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    .tip h2 {{ margin-top: 0; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
</style>
</head>
<body>

<div class="header">
    <h1>Extended Thinking vs No Thinking</h1>
    <p>Date: {timestamp_str} | Model: {MODEL} | Prompts: {len(TEST_PROMPTS)}</p>
</div>

<div class="summary">
    <div class="card" style="border-top-color: #e74c3c;">
        <h3>Thinking Disabled</h3>
        <div class="val">{sum(data['modes'].get(MODE_DISABLED, {}).get('grade', {}).get('score', 0) for data in results.values()) / max(len(results), 1):.1f}/10</div>
        <div class="sub">Avg score | Fastest</div>
    </div>
    <div class="card" style="border-top-color: #f39c12;">
        <h3>Budget 2048</h3>
        <div class="val">{sum(data['modes'].get(MODE_BUDGET, {}).get('grade', {}).get('score', 0) for data in results.values()) / max(len(results), 1):.1f}/10</div>
        <div class="sub">Avg score | Balanced</div>
    </div>
    <div class="card" style="border-top-color: #2ecc71;">
        <h3>Thinking Enabled</h3>
        <div class="val">{sum(data['modes'].get(MODE_ENABLED, {}).get('grade', {}).get('score', 0) for data in results.values()) / max(len(results), 1):.1f}/10</div>
        <div class="sub">Avg score | Best quality</div>
    </div>
</div>

<table>
    <thead>
        <tr>
            <th>Prompt</th>
            <th>Mode</th>
            <th>Score</th>
            <th>Correct</th>
            <th>Time</th>
            <th>Tokens</th>
            <th>Finish</th>
            <th>Output</th>
        </tr>
    </thead>
    <tbody>
        {rows}
    </tbody>
</table>

<div class="tip">
    <h2>Key Takeaways</h2>
    <p><strong>Thinking Disabled:</strong> Fastest, cheapest. Use for simple tasks, formatting, factual queries. May fail on reasoning traps (like the bat-and-ball problem).</p>
    <p><strong>Thinking Enabled (default):</strong> Best reasoning quality but slowest and most expensive. <em>Critical:</em> needs max_tokens >= 8192 or output is empty (reasoning eats the budget).</p>
    <p><strong>Thinking with Budget:</strong> Middle ground. Caps reasoning tokens so output is guaranteed. Good balance of quality vs cost.</p>
    <p><strong>Decision framework:</strong> Run without thinking first. If accuracy is good enough, stop. Only enable thinking if prompt optimization alone isn't sufficient.</p>
</div>

</body>
</html>"""


# ===================================================================
# MAIN
# ===================================================================

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("  EXTENDED THINKING VS NO THINKING")
    print(f"  Model: {MODEL} | Prompts: {len(TEST_PROMPTS)}")
    print("=" * 60)
    print()

    print("  Running comparison (3 modes x {} prompts)...".format(len(TEST_PROMPTS)))
    print()

    results = run_comparison()

    print("  Grading outputs...")
    for name, data in results.items():
        for mode in [MODE_DISABLED, MODE_BUDGET, MODE_ENABLED]:
            m = data["modes"].get(mode, {})
            if m.get("content") and not m.get("finish_reason") == "error":
                grade = grade_result(data["prompt_info"], m)
                data["modes"][mode]["grade"] = grade
                print(f"    {name[:25]:25s} {MODE_LABELS[mode][:25]:25s} -> {grade.get('score', 0)}/10")
            else:
                data["modes"][mode]["grade"] = {"correct": False, "score": 0, "reasoning": "No output to grade"}

    print()

    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    txt_path = os.path.join(LOGS_DIR, f"thinking_test_{timestamp}.txt")
    html_path = os.path.join(LOGS_DIR, f"thinking_test_{timestamp}.html")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(generate_txt_report(results, timestamp))

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(generate_html_report(results, timestamp))

    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print()

    print(f"  {'Prompt':30s} | {'Disabled':>10s} | {'Budget':>10s} | {'Enabled':>10s}")
    print("  " + "-" * 30 + "-+-" + "-" * 10 + "-+-" + "-" * 10 + "-+-" + "-" * 10)

    for name, data in results.items():
        scores = []
        for mode in [MODE_DISABLED, MODE_BUDGET, MODE_ENABLED]:
            s = data["modes"].get(mode, {}).get("grade", {}).get("score", 0)
            scores.append(f"{s:.0f}/10")
        print(f"  {name[:30]:30s} | {scores[0]:>10s} | {scores[1]:>10s} | {scores[2]:>10s}")

    print()
    print(f"  TXT:  {txt_path}")
    print(f"  HTML: {html_path}")
