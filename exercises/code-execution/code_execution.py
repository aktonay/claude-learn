"""
Code Execution Exercise
=======================
Demonstrates three approaches to AI-powered data analysis, inspired by
the Anthropic Files API + Code Execution feature.

The Anthropic API lets you:
  1. Upload files via the Files API
  2. Send file references to Claude
  3. Claude executes Python code in a server-side Docker container
  4. Download generated plots/files

Since the ZAI API doesn't support Files API or server-side code execution,
this exercise builds the equivalent pattern CLIENT-SIDE using tool calling:

  1. Read file data into the conversation
  2. Model decides to write Python code
  3. Our execute_python tool runs code locally
  4. Output is sent back to the model
  5. Model iterates until satisfied

This teaches the agentic loop pattern used by Claude Code, ChatGPT Code
Interpreter, and similar systems.

Three tests:
  Test 1: Direct Analysis      — model analyzes CSV data as text (no code)
  Test 2: Code Generation      — model writes analysis code, we run it once
  Test 3: Agentic Loop         — model uses execute_python tool iteratively
"""

import os
import sys
import csv
import json
import time
import subprocess
import tempfile
import textwrap
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
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "streaming_churn.csv")


# ===================================================================
# SAMPLE DATA GENERATOR
# ===================================================================

def generate_sample_csv():
    """
    Generate a streaming service churn dataset.
    Columns: user_id, age, subscription_tier, monthly_hours,
             total_sessions, account_age_days, support_tickets,
             payment_failures, has_promo, churned
    """
    import random
    random.seed(42)

    tiers = ["free", "basic", "premium", "family"]
    rows = []

    for i in range(200):
        tier = random.choice(tiers)
        age = random.randint(18, 65)
        account_age = random.randint(7, 730)

        if tier == "free":
            monthly_hours = round(random.uniform(1, 15), 1)
            sessions = random.randint(2, 30)
        elif tier == "basic":
            monthly_hours = round(random.uniform(5, 40), 1)
            sessions = random.randint(10, 60)
        elif tier == "premium":
            monthly_hours = round(random.uniform(10, 80), 1)
            sessions = random.randint(15, 100)
        else:
            monthly_hours = round(random.uniform(15, 100), 1)
            sessions = random.randint(20, 120)

        support_tickets = random.choices([0, 1, 2, 3, 4, 5], weights=[40, 25, 15, 10, 7, 3])[0]
        payment_failures = random.choices([0, 1, 2, 3], weights=[70, 18, 9, 3])[0]
        has_promo = random.choice([0, 1])

        churn_score = 0
        if support_tickets >= 3:
            churn_score += 0.3
        if payment_failures >= 2:
            churn_score += 0.25
        if monthly_hours < 10 and account_age > 180:
            churn_score += 0.2
        if tier == "free" and account_age < 60:
            churn_score += 0.15
        if has_promo == 0:
            churn_score += 0.1

        churned = 1 if random.random() < churn_score else 0

        rows.append([
            f"user_{i+1:04d}", age, tier, monthly_hours, sessions,
            account_age, support_tickets, payment_failures, has_promo, churned
        ])

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "user_id", "age", "subscription_tier", "monthly_hours",
            "total_sessions", "account_age_days", "support_tickets",
            "payment_failures", "has_promo", "churned"
        ])
        writer.writerows(rows)

    return len(rows)


def read_csv_as_text(path, max_rows=None):
    with open(path, "r") as f:
        if max_rows:
            lines = f.readlines()[:max_rows + 1]
            return "".join(lines)
        return f.read()


def get_csv_summary(path):
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total = len(rows)
    churned = sum(1 for r in rows if r["churned"] == "1")
    tiers = {}
    for r in rows:
        t = r["subscription_tier"]
        tiers[t] = tiers.get(t, 0) + 1

    return {
        "total_users": total,
        "churned": churned,
        "churn_rate": round(churned / total * 100, 1),
        "tier_distribution": tiers,
    }


# ===================================================================
# CHAT HELPER
# ===================================================================

def chat(messages, max_tokens=3000, tools=None, temperature=0.7):
    params = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    if tools:
        params["tools"] = tools

    return client.chat.completions.create(**params)


# ===================================================================
# TOOL DEFINITION: execute_python
# ===================================================================

EXECUTE_PYTHON_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_python",
        "description": (
            "Execute Python code and return stdout, stderr, and exit code. "
            "Use this to run data analysis code. Available libraries: csv, json, "
            "math, statistics, collections, itertools. "
            "The CSV data file is available at the path stored in variable DATA_FILE. "
            "Always import needed libraries at the top of your code. "
            "Print your results — only stdout is returned."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Print results for output.",
                },
                "purpose": {
                    "type": "string",
                    "description": "Brief description of what this code does.",
                },
            },
            "required": ["code", "purpose"],
        },
    },
}


def execute_python(code, timeout=30):
    """
    Run Python code in a subprocess and return stdout/stderr.
    The CSV file path is injected as DATA_FILE variable.
    """
    wrapper = "# -*- coding: utf-8 -*-\n"
    wrapper += "import os, sys, json, csv, math, statistics, collections\n"
    wrapper += "sys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
    wrapper += f"DATA_FILE = r'{CSV_PATH}'\n"
    wrapper += f"DATA_DIR = r'{DATA_DIR}'\n\n"
    wrapper += code

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(wrapper)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=DATA_DIR,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:1500],
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Timeout after {timeout}s", "exit_code": -1}
    finally:
        os.unlink(tmp_path)


def run_tool(tool_name, tool_input):
    if tool_name == "execute_python":
        return execute_python(tool_input["code"])
    raise ValueError(f"Unknown tool: {tool_name}")


# ===================================================================
# TEST 1: DIRECT ANALYSIS (no code)
# ===================================================================

def test_direct_analysis(csv_text, summary):
    print("  TEST 1: Direct Analysis (text only, no code)")
    print()

    prompt = f"""Analyze the following streaming service dataset and identify the major drivers of churn.
Provide a concise analysis with key findings.

Dataset summary: {json.dumps(summary)}

Sample data (first 30 rows):
{csv_text}

Provide:
1. Overall churn rate and what it means
2. Top 3 factors that drive churn (with evidence from the data)
3. Recommendations to reduce churn"""

    messages = [{"role": "user", "content": prompt}]
    resp = chat(messages, max_tokens=2000)
    analysis = resp.choices[0].message.content or ""

    print(f"    Response length: {len(analysis)} chars")
    print(f"    Preview: {analysis[:120]}...")
    print()

    return analysis


# ===================================================================
# TEST 2: CODE GENERATION (one-shot)
# ===================================================================

def test_code_generation(csv_text, summary):
    print("  TEST 2: Code Generation (model writes code, we run once)")
    print()

    prompt = f"""Write Python code to analyze a streaming service CSV dataset for churn drivers.

The CSV file is at: {CSV_PATH}
Columns: user_id, age, subscription_tier, monthly_hours, total_sessions, account_age_days, support_tickets, payment_failures, has_promo, churned

Dataset summary: {json.dumps(summary)}

CRITICAL CONSTRAINTS:
- Do NOT use pandas, numpy, or any third-party libraries.
- Use ONLY Python standard library: csv, json, math, statistics, collections.
- The file is a standard CSV, use csv.DictReader to read it.

Write a single Python script that:
1. Reads the CSV file using csv.DictReader
2. Calculates churn rate by subscription tier
3. Calculates churn rate by support ticket count (0, 1-2, 3+)
4. Calculates churn rate by payment failures (0, 1, 2+)
5. Calculates average monthly hours for churned vs retained users
6. Prints ALL results clearly

Only output the Python code. No explanations. Start with imports."""

    messages = [{"role": "user", "content": prompt}]
    resp = chat(messages, max_tokens=2000)
    content = resp.choices[0].message.content or ""

    code = extract_code(content)
    if not code:
        print("    Model did not generate valid code")
        return None, "Code extraction failed"

    print(f"    Generated code: {len(code)} chars, {code.count(chr(10))} lines")

    exec_result = execute_python(code)
    output = exec_result["stdout"]

    if exec_result["exit_code"] != 0:
        print(f"    Execution FAILED (exit code {exec_result['exit_code']})")
        print(f"    stderr: {exec_result['stderr'][:200]}")
    else:
        print(f"    Execution OK, output: {len(output)} chars")
        print(f"    Preview: {output[:120]}...")
    print()

    return code, output


def extract_code(text):
    if "```python" in text:
        start = text.find("```python") + 9
        end = text.find("```", start)
        return text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        return text[start:end].strip()
    elif "import " in text and "\n" in text:
        lines = text.split("\n")
        code_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                in_code = True
            if in_code:
                code_lines.append(line)
        return "\n".join(code_lines) if code_lines else text
    return text


# ===================================================================
# TEST 3: AGENTIC LOOP (tool calling)
# ===================================================================

def test_agentic_loop(csv_text, summary, max_iterations=5):
    print("  TEST 3: Agentic Loop (model calls execute_python iteratively)")
    print()

    system_msg = (
        "You are a data analyst. You have access to a Python code execution tool. "
        "The CSV data file is available at the path in variable DATA_FILE. "
        "CRITICAL: Do NOT use pandas, numpy, or any third-party libraries. "
        "Use ONLY Python standard library: csv, json, math, statistics, collections. "
        "Analyze the data iteratively: write code, check results, refine. "
        "After 2-3 successful code executions, STOP calling the tool and provide "
        "a final text summary of your findings. Do NOT keep calling the tool forever. "
        "Always import libraries at the top of your code. Print results clearly."
    )

    user_msg = f"""Analyze this streaming service dataset to find major churn drivers.

Dataset summary: {json.dumps(summary)}
CSV file path: {CSV_PATH}
Columns: user_id, age, subscription_tier, monthly_hours, total_sessions, account_age_days, support_tickets, payment_failures, has_promo, churned

Use the execute_python tool to run analysis code. Use ONLY standard library (csv module, no pandas).
After 2-3 successful analyses, summarize your findings in plain text WITHOUT calling the tool again."""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    tools = [EXECUTE_PYTHON_SCHEMA]
    iterations = []
    final_analysis = ""

    for i in range(max_iterations):
        print(f"    Iteration {i+1}/{max_iterations}...")
        resp = chat(messages, max_tokens=3000, tools=tools)

        choice = resp.choices[0]
        finish = choice.finish_reason
        assistant_msg = choice.message

        tool_calls_data = []
        if hasattr(assistant_msg, "tool_calls") and assistant_msg.tool_calls:
            for tc in assistant_msg.tool_calls:
                tool_calls_data.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })

        msg_dict = {"role": "assistant", "content": assistant_msg.content or ""}
        if tool_calls_data:
            msg_dict["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_calls_data
            ]
        messages.append(msg_dict)

        if finish == "stop" or not tool_calls_data:
            final_analysis = assistant_msg.content or ""
            print(f"    Model finished (stop). Final analysis: {len(final_analysis)} chars")
            break

        for tc in tool_calls_data:
            args = json.loads(tc["arguments"])
            code = args.get("code", "")
            purpose = args.get("purpose", "")
            print(f"      Tool call: {purpose[:60]} ({len(code)} chars code)")

            result = run_tool(tc["name"], args)
            result_str = json.dumps(result)
            print(f"      Result: {len(result_str)} chars, exit={result.get('exit_code')}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result_str,
            })

            iterations.append({
                "iteration": i + 1,
                "purpose": purpose,
                "code_length": len(code),
                "exit_code": result.get("exit_code", -1),
                "output_length": len(result.get("stdout", "")),
                "has_errors": bool(result.get("stderr")),
            })

        time.sleep(0.5)

    if not final_analysis:
        print("    Forcing final summary (model used all iterations)...")
        messages.append({
            "role": "user",
            "content": (
                "Based on all the analysis results above, provide a final summary "
                "of the major churn drivers. Do NOT call any more tools. "
                "Just write your summary in plain text."
            ),
        })
        resp = chat(messages, max_tokens=2000)
        final_analysis = resp.choices[0].message.content or ""
        print(f"    Final analysis: {len(final_analysis)} chars")

    print()
    return {
        "iterations": iterations,
        "total_iterations": len(iterations),
        "final_analysis": final_analysis,
    }


# ===================================================================
# TXT REPORT
# ===================================================================

def save_report(test1_result, test2_result, test3_result, timestamp_str):
    os.makedirs(LOGS_DIR, exist_ok=True)
    filepath = os.path.join(LOGS_DIR, f"code_execution_{timestamp_str}.txt")

    sep = "=" * 70
    dash = "-" * 70
    lines = []

    lines.append(sep)
    lines.append("  CODE EXECUTION EXERCISE REPORT")
    lines.append(f"  Date: {timestamp_str}")
    lines.append(f"  Model: {MODEL}")
    lines.append(sep)
    lines.append("")

    lines.append(sep)
    lines.append("  CONTEXT")
    lines.append(sep)
    lines.append("")
    lines.append("  Anthropic API provides:")
    lines.append("    - Files API: upload files, get file IDs, reference in messages")
    lines.append("    - Code Execution: server-side Docker container runs Python")
    lines.append("    - Download API: retrieve generated plots/files from container")
    lines.append("")
    lines.append("  ZAI API equivalent (this exercise):")
    lines.append("    - Read file data directly into prompt (no separate upload)")
    lines.append("    - Tool calling: model calls execute_python, we run locally")
    lines.append("    - Agentic loop: model sees output, iterates until satisfied")
    lines.append("")

    lines.append(sep)
    lines.append("  TEST 1: DIRECT ANALYSIS (no code execution)")
    lines.append(sep)
    lines.append("")
    for tl in test1_result.split("\n"):
        lines.append(f"  {tl}")
    lines.append("")

    lines.append(sep)
    lines.append("  TEST 2: CODE GENERATION (one-shot)")
    lines.append(sep)
    lines.append("")
    if test2_result[0]:
        lines.append("  Generated code:")
        lines.append("")
        for tl in test2_result[0].split("\n"):
            lines.append(f"    {tl}")
        lines.append("")
    else:
        lines.append("  (code generation failed)")
        lines.append("")

    lines.append(dash)
    lines.append("  Execution output:")
    lines.append(dash)
    lines.append("")
    for tl in test2_result[1].split("\n"):
        lines.append(f"  {tl}")
    lines.append("")

    lines.append(sep)
    lines.append("  TEST 3: AGENTIC LOOP (iterative tool calling)")
    lines.append(sep)
    lines.append("")
    lines.append(f"  Total iterations: {test3_result['total_iterations']}")
    lines.append("")
    for it in test3_result["iterations"]:
        lines.append(f"    Iter {it['iteration']}: {it['purpose'][:50]}")
        lines.append(f"      Code: {it['code_length']} chars | Output: {it['output_length']} chars | Exit: {it['exit_code']}")
        if it["has_errors"]:
            lines.append(f"      (had stderr)")
    lines.append("")

    lines.append(dash)
    lines.append("  Final analysis:")
    lines.append(dash)
    lines.append("")
    for tl in test3_result["final_analysis"].split("\n"):
        lines.append(f"  {tl}")
    lines.append("")

    lines.append(sep)
    lines.append("  KEY TAKEAWAYS")
    lines.append(sep)
    lines.append("")
    lines.append("  1. THREE APPROACHES TO AI DATA ANALYSIS:")
    lines.append("     a) Direct: send data as text, model analyzes from training")
    lines.append("        Fast, simple, but limited by context window and no computation")
    lines.append("     b) Code gen: model writes code, you run it once")
    lines.append("        More powerful, but no iteration if code has bugs")
    lines.append("     c) Agentic loop: model calls tools, sees output, iterates")
    lines.append("        Most powerful — handles errors, refines analysis, autonomous")
    lines.append("")
    lines.append("  2. ANTHROPIC FILES API vs ZAI APPROACH:")
    lines.append("     Anthropic: file upload → file ID → server-side exec → download")
    lines.append("     ZAI: read file → embed in prompt → tool-calling exec → local output")
    lines.append("     Same conceptual flow, different implementation layer")
    lines.append("")
    lines.append("  3. TOOL CALLING IS THE KEY PRIMITIVE:")
    lines.append("     The execute_python tool transforms the model from a text generator")
    lines.append("     into an agent that can compute, analyze, and iterate.")
    lines.append("     This is how ChatGPT Code Interpreter and Claude Code work internally.")
    lines.append("")
    lines.append("  4. SAFETY CONSIDERATIONS:")
    lines.append("     Anthropic's Docker container provides sandboxing (no network, limited FS)")
    lines.append("     Our local execution runs with full user permissions — production")
    lines.append("     systems should use containers or restricted execution environments.")
    lines.append("")
    lines.append("  5. ITERATION IS THE SUPERPOWER:")
    lines.append("     The agentic loop lets the model recover from errors, explore data")
    lines.append("     progressively, and refine its analysis — impossible with one-shot.")
    lines.append("     Each iteration adds context about what worked and what didn't.")

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
    print(f"  CODE EXECUTION EXERCISE (model: {MODEL})")
    print("=" * 60)
    print()

    print("  Generating sample dataset...")
    row_count = generate_sample_csv()
    print(f"  Created: {CSV_PATH} ({row_count} rows)")
    print()

    summary = get_csv_summary(CSV_PATH)
    print(f"  Dataset: {summary['total_users']} users, {summary['churn_rate']}% churn rate")
    print(f"  Tiers: {summary['tier_distribution']}")
    print()

    csv_text = read_csv_as_text(CSV_PATH, max_rows=30)

    print("-" * 60)
    print()
    test1_result = test_direct_analysis(csv_text, summary)
    time.sleep(1)

    print("-" * 60)
    print()
    test2_result = test_code_generation(csv_text, summary)
    time.sleep(1)

    print("-" * 60)
    print()
    test3_result = test_agentic_loop(csv_text, summary, max_iterations=5)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = save_report(test1_result, test2_result, test3_result, timestamp)

    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print()
    print(f"  Test 1 (Direct):  {len(test1_result)} chars analysis")
    print(f"  Test 2 (CodeGen): {'OK' if test2_result[0] else 'FAILED'}")
    print(f"  Test 3 (Agent):   {test3_result['total_iterations']} iterations, {len(test3_result['final_analysis'])} chars final")
    print()
    print(f"  Report: {filepath}")
