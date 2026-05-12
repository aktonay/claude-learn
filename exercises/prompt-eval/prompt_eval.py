"""
Prompt Evaluation Exercise
==========================
Demonstrates how to build a complete prompt evaluation pipeline.
Runs the same test dataset through TWO prompt versions (baseline vs improved),
grades each output with BOTH model grading and code grading,
and saves a formatted comparison to logs/.

Why prompt evaluation matters:
  - Testing a prompt once or twice is not enough — real users hit edge cases
  - An eval pipeline gives you OBJECTIVE metrics to measure prompt quality
  - You can compare prompt versions side-by-side with real numbers

Pipeline overview:
  1. Generate a test dataset (AWS-related Python/JSON/Regex tasks)
  2. Run each test case through prompt v1 (naive) and prompt v2 (improved)
  3. Grade outputs using:
     - CODE GRADER: validates syntax (json.loads, ast.parse, re.compile)
     - MODEL GRADER: uses the API to evaluate quality, accuracy, task-following
  4. Combine scores and compare v1 vs v2 averages

Key concept:
  Code graders check STRUCTURE (syntax valid? correct format?).
  Model graders check QUALITY (accurate? helpful? follows instructions?).
  Together they give a complete picture of prompt performance.
"""

import os
import sys
import json
import re
import ast
import time
from datetime import datetime
from statistics import mean
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Setup: Load API key from .env and configure the client
# .env lives in the PROJECT ROOT — go up two levels from this script
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

client = OpenAI(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url=os.getenv("ZAI_BASE_URL"),
)

# Using the fast model for dataset generation and grading
# The actual prompt runs also use this model — in production you'd
# use a more capable model for the prompt and a cheaper one for grading
MODEL = "glm-4.5-air"
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")


# ===================================================================
# HELPER FUNCTIONS
# ===================================================================
# These are the same helpers used across all exercises.
# They wrap the OpenAI-compatible API calls used by the ZAI endpoint.

def add_user_message(messages, text):
    """Append a user message to the conversation history."""
    messages.append({"role": "user", "content": text})


def add_assistant_message(messages, text):
    """Append an assistant (AI) message to the conversation history."""
    messages.append({"role": "assistant", "content": text})


def chat(messages, system_prompt=None, temperature=1.0, stop=None):
    """
    Send messages to the API with optional system prompt, temperature, and stop sequences.

    OpenAI-compatible API differences from Anthropic:
      - System prompt is a message with role "system" (first in array)
      - Stop sequences use "stop" parameter (not "stop_sequences")
      - Response format: response.choices[0].message.content
    """
    all_messages = []
    if system_prompt:
        all_messages.append({"role": "system", "content": system_prompt})
    all_messages.extend(messages)

    params = {
        "model": MODEL,
        "max_tokens": 1000,
        "messages": all_messages,
        "temperature": temperature,
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    if stop:
        params["stop"] = stop

    response = client.chat.completions.create(**params)
    return response.choices[0].message.content


# ===================================================================
# STEP 1: GENERATE THE EVALUATION DATASET
# ===================================================================
# The dataset is an array of test cases. Each case has:
#   - task: what the prompt should produce
#   - format: "json", "python", or "regex" — used by code grader
#   - solution_criteria: key criteria for the model grader to check against
#
# We generate this automatically using the API itself.
# This is a common pattern — use the model to create test data for evals.

def generate_dataset():
    """Generate an evaluation dataset of AWS-related coding tasks."""
    prompt = """
Generate an evaluation dataset for a prompt evaluation. The dataset will be used to evaluate prompts
that generate Python, JSON, or Regex specifically for AWS-related tasks. Generate an array of JSON objects,
each representing a task that requires Python, JSON, or a Regex to complete.

Example output:
```json
[
    {
        "task": "Description of task",
        "format": "json" or "python" or "regex",
        "solution_criteria": "Key criteria for evaluating the solution"
    },
    ...additional
]
```

* Focus on tasks that can be solved by writing a single Python function, a single JSON object, or a regular expression.
* Focus on tasks that do not require writing much code.

Please generate 3 objects.
Output ONLY raw JSON. No markdown. No backticks. No explanation.
"""
    messages = []
    add_user_message(messages, prompt)
    text = chat(messages, stop=["```"])
    parsed = try_parse_json(text)
    if parsed is None:
        print("        Warning: dataset generation returned invalid JSON, retrying...")
        messages = []
        add_user_message(messages, prompt)
        text = chat(messages, stop=["```"])
        parsed = try_parse_json(text)
        if parsed is None:
            raise ValueError(f"Could not parse dataset as JSON: {text[:200]}")
    return parsed


# ===================================================================
# STEP 2: PROMPT VERSIONS (v1 = naive, v2 = improved)
# ===================================================================
# The whole point of prompt evaluation is comparing different prompts.
# v1 is a bare-bones prompt — no formatting instructions, no constraints.
# v2 adds explicit format rules + uses assistant prefilling + stop sequences.
# The eval pipeline measures HOW MUCH BETTER v2 is than v1.

def run_prompt_v1(test_case):
    """Naive prompt — no formatting instructions. Expected: verbose output with markdown."""
    prompt = f"""
Please solve the following task:

{test_case["task"]}
"""
    messages = []
    add_user_message(messages, prompt)
    return chat(messages)


def run_prompt_v2(test_case):
    """Improved prompt — explicit format constraints + stop sequence."""
    prompt = f"""
Please solve the following task:

{test_case["task"]}

* Respond only with Python, JSON, or a plain Regex
* Do not add any comments, commentary, or explanation
* No markdown code blocks, no backticks
* Start directly with the code/data
"""
    messages = []
    add_user_message(messages, prompt)
    output = chat(messages, stop=["```"])
    return output


# ===================================================================
# STEP 3a: CODE GRADER — validates syntax programmatically
# ===================================================================
# Code graders check STRUCTURE: does the output have valid syntax?
# They're fast, free, and deterministic — no API call needed.
# Returns 10 (valid) or 0 (invalid) — binary signal.

def validate_json(text):
    """Check if text is valid JSON. Returns 10 if valid, 0 if not."""
    try:
        json.loads(text.strip())
        return 10
    except json.JSONDecodeError:
        return 0


def validate_python(text):
    """Check if text is valid Python syntax. Returns 10 if valid, 0 if not."""
    try:
        ast.parse(text.strip())
        return 10
    except SyntaxError:
        return 0


def validate_regex(text):
    """Check if text is a valid regular expression. Returns 10 if valid, 0 if not."""
    try:
        re.compile(text.strip())
        return 10
    except re.error:
        return 0


def grade_syntax(output, test_case):
    """Run the appropriate syntax validator based on expected format."""
    fmt = test_case["format"]
    if fmt == "json":
        return validate_json(output)
    elif fmt == "python":
        return validate_python(output)
    else:
        return validate_regex(output)


# ===================================================================
# STEP 3b: MODEL GRADER — uses the API to evaluate quality
# ===================================================================
# Model graders check QUALITY: is the output accurate? Does it follow
# instructions? Is it complete? They're flexible but cost an API call.
# The eval prompt asks for strengths, weaknesses, reasoning, AND a score.
# Asking for reasoning prevents the model from defaulting to middling scores.

def grade_by_model(test_case, output):
    """Use the API itself to grade the output quality. Returns parsed JSON with score."""
    eval_prompt = f"""
You are an expert AWS code reviewer. Your task is to evaluate the following AI-generated solution.

Original Task:
<task>
{test_case["task"]}
</task>

Solution to Evaluate:
<solution>
{output}
</solution>

Criteria you should use to evaluate the solution:
<criteria>
{test_case["solution_criteria"]}
</criteria>

Output ONLY raw valid JSON. No markdown code blocks. No backticks. No explanation.
Start with {{ end with }}.
Provide your evaluation as a structured JSON object with these fields:
- "strengths": An array of 1-3 key strengths
- "weaknesses": An array of 1-3 key areas for improvement
- "reasoning": A concise explanation of your overall assessment
- "score": A number between 1-10

Example:
{{"strengths": ["s1"], "weaknesses": ["w1"], "reasoning": "reason", "score": 7}}
"""
    messages = []
    add_user_message(messages, eval_prompt)
    eval_text = chat(messages, stop=["```"])

    parsed = try_parse_json(eval_text)
    if parsed is None:
        return {
            "strengths": ["N/A"],
            "weaknesses": ["Grader output could not be parsed as JSON"],
            "reasoning": "Fallback: grader returned non-JSON output",
            "score": 5,
        }
    return parsed


def try_parse_json(text):
    """Try to extract and parse JSON from model output. Handles markdown wrapping."""
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting JSON from markdown code block
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try finding first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


# ===================================================================
# STEP 4: RUN THE FULL EVALUATION PIPELINE
# ===================================================================
# For each test case:
#   1. Run prompt v1 and prompt v2
#   2. Code-grade both outputs (syntax check)
#   3. Model-grade both outputs (quality check)
#   4. Combine scores: average of (syntax_score + model_score)
#   5. Collect all results

def run_test_case(test_case):
    """Run both prompt versions on a test case and grade the results."""
    # --- Prompt v1 (naive) ---
    output_v1 = run_prompt_v1(test_case)
    syntax_v1 = grade_syntax(output_v1, test_case)
    model_grade_v1 = grade_by_model(test_case, output_v1)
    combined_v1 = (syntax_v1 + model_grade_v1["score"]) / 2

    # --- Prompt v2 (improved) ---
    output_v2 = run_prompt_v2(test_case)
    syntax_v2 = grade_syntax(output_v2, test_case)
    model_grade_v2 = grade_by_model(test_case, output_v2)
    combined_v2 = (syntax_v2 + model_grade_v2["score"]) / 2

    return {
        "test_case": test_case,
        "v1": {
            "output": output_v1,
            "syntax_score": syntax_v1,
            "model_score": model_grade_v1["score"],
            "model_reasoning": model_grade_v1["reasoning"],
            "model_strengths": model_grade_v1["strengths"],
            "model_weaknesses": model_grade_v1["weaknesses"],
            "combined_score": combined_v1,
        },
        "v2": {
            "output": output_v2,
            "syntax_score": syntax_v2,
            "model_score": model_grade_v2["score"],
            "model_reasoning": model_grade_v2["reasoning"],
            "model_strengths": model_grade_v2["strengths"],
            "model_weaknesses": model_grade_v2["weaknesses"],
            "combined_score": combined_v2,
        },
    }


def run_eval(dataset):
    """Run the full evaluation pipeline on the dataset."""
    results = []

    for i, test_case in enumerate(dataset, 1):
        print(f"  [{i}/{len(dataset)}] Evaluating: {test_case['task'][:60]}...")
        result = run_test_case(test_case)
        results.append(result)

    avg_v1 = mean([r["v1"]["combined_score"] for r in results])
    avg_v2 = mean([r["v2"]["combined_score"] for r in results])
    avg_syntax_v1 = mean([r["v1"]["syntax_score"] for r in results])
    avg_syntax_v2 = mean([r["v2"]["syntax_score"] for r in results])
    avg_model_v1 = mean([r["v1"]["model_score"] for r in results])
    avg_model_v2 = mean([r["v2"]["model_score"] for r in results])

    return {
        "results": results,
        "summary": {
            "v1_avg_combined": avg_v1,
            "v2_avg_combined": avg_v2,
            "v1_avg_syntax": avg_syntax_v1,
            "v2_avg_syntax": avg_syntax_v2,
            "v1_avg_model": avg_model_v1,
            "v2_avg_model": avg_model_v2,
            "improvement": avg_v2 - avg_v1,
            "dataset_size": len(dataset),
        },
    }


# ===================================================================
# STEP 5: SAVE FORMATTED RESULTS TO LOGS
# ===================================================================
# Produces a detailed comparison report showing:
#   - Dataset overview
#   - Per-test-case results (v1 vs v2 side-by-side)
#   - Aggregate scores and improvement
#   - Grading methodology explanation

def save_report(eval_data):
    """Save the full evaluation report to a formatted .txt file."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(LOGS_DIR, f"prompt_eval_{timestamp}.txt")

    results = eval_data["results"]
    summary = eval_data["summary"]

    sep = "=" * 70
    dash = "-" * 70
    lines = []

    # --- Header ---
    lines.append(sep)
    lines.append("  PROMPT EVALUATION REPORT")
    lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Model: {MODEL}")
    lines.append(f"  Dataset size: {summary['dataset_size']} test cases")
    lines.append(sep)
    lines.append("")

    # --- Methodology ---
    lines.append(sep)
    lines.append("  METHODOLOGY")
    lines.append(sep)
    lines.append("")
    lines.append("  Two prompt versions tested on the same dataset:")
    lines.append("")
    lines.append("  PROMPT V1 (naive):")
    lines.append('    "Please solve the following task: {task}"')
    lines.append("    No formatting instructions. No constraints.")
    lines.append("")
    lines.append("  PROMPT V2 (improved):")
    lines.append('    Explicit format rules + assistant prefilling + stop sequence.')
    lines.append('    "Respond only with Python, JSON, or Regex. No comments. No markdown."')
    lines.append("    Prefills assistant with backtick to steer code output.")
    lines.append("    Uses stop sequence to cut off markdown wrapping.")
    lines.append("")
    lines.append("  GRADING (each output gets TWO scores averaged together):")
    lines.append("")
    lines.append("  CODE GRADER (syntax validation):")
    lines.append("    JSON  -> json.loads() — returns 10 (valid) or 0 (invalid)")
    lines.append("    Python -> ast.parse()  — returns 10 (valid) or 0 (invalid)")
    lines.append("    Regex -> re.compile()  — returns 10 (valid) or 0 (invalid)")
    lines.append("    Fast, free, deterministic. Checks STRUCTURE only.")
    lines.append("")
    lines.append("  MODEL GRADER (quality evaluation):")
    lines.append("    Sends output to API with eval prompt asking for:")
    lines.append("    - strengths (1-3 items)")
    lines.append("    - weaknesses (1-3 items)")
    lines.append("    - reasoning (why this score)")
    lines.append("    - score (1-10)")
    lines.append("    Uses solution_criteria from test case for targeted evaluation.")
    lines.append("    Flexible but costs an API call. Checks QUALITY.")
    lines.append("")
    lines.append("  COMBINED SCORE = (syntax_score + model_score) / 2")
    lines.append("")

    # --- Summary ---
    lines.append(sep)
    lines.append("  SUMMARY")
    lines.append(sep)
    lines.append("")
    lines.append(f"  | Metric              | V1 (naive)   | V2 (improved) | Delta    |")
    lines.append(f"  |---------------------|--------------|---------------|----------|")
    lines.append(f"  | Combined Score      | {summary['v1_avg_combined']:10.1f}   | {summary['v2_avg_combined']:11.1f}   | {summary['improvement']:+6.1f}   |")
    lines.append(f"  | Syntax Score        | {summary['v1_avg_syntax']:10.1f}   | {summary['v2_avg_syntax']:11.1f}   | {summary['v2_avg_syntax'] - summary['v1_avg_syntax']:+6.1f}   |")
    lines.append(f"  | Model Score         | {summary['v1_avg_model']:10.1f}   | {summary['v2_avg_model']:11.1f}   | {summary['v2_avg_model'] - summary['v1_avg_model']:+6.1f}   |")
    lines.append("")
    if summary["improvement"] > 0:
        lines.append(f"  RESULT: V2 is BETTER by {summary['improvement']:.1f} points on average.")
    elif summary["improvement"] < 0:
        lines.append(f"  RESULT: V1 is BETTER by {abs(summary['improvement']):.1f} points on average.")
    else:
        lines.append("  RESULT: Both versions scored the same.")
    lines.append("")

    # --- Per-test-case results ---
    for i, result in enumerate(results, 1):
        tc = result["test_case"]
        v1 = result["v1"]
        v2 = result["v2"]

        lines.append(sep)
        lines.append(f"  TEST CASE {i}/{len(results)}")
        lines.append(sep)
        lines.append("")
        lines.append(f"  Task: {tc['task']}")
        lines.append(f"  Expected format: {tc['format']}")
        lines.append(f"  Solution criteria: {tc['solution_criteria']}")
        lines.append("")

        # V1 results
        lines.append(dash)
        lines.append("  PROMPT V1 OUTPUT (naive):")
        lines.append(dash)
        lines.append("")
        for text_line in v1["output"].split("\n")[:20]:
            lines.append(f"  {text_line}")
        if v1["output"].count("\n") > 20:
            lines.append(f"  ... ({v1['output'].count(chr(10)) - 20} more lines)")
        lines.append("")
        lines.append(f"  Syntax score: {v1['syntax_score']}/10")
        lines.append(f"  Model score:  {v1['model_score']}/10")
        lines.append(f"  Combined:     {v1['combined_score']:.1f}/10")
        lines.append(f"  Reasoning:    {v1['model_reasoning']}")
        lines.append(f"  Strengths:    {', '.join(v1['model_strengths'])}")
        lines.append(f"  Weaknesses:   {', '.join(v1['model_weaknesses'])}")
        lines.append("")

        # V2 results
        lines.append(dash)
        lines.append("  PROMPT V2 OUTPUT (improved):")
        lines.append(dash)
        lines.append("")
        for text_line in v2["output"].split("\n")[:20]:
            lines.append(f"  {text_line}")
        if v2["output"].count("\n") > 20:
            lines.append(f"  ... ({v2['output'].count(chr(10)) - 20} more lines)")
        lines.append("")
        lines.append(f"  Syntax score: {v2['syntax_score']}/10")
        lines.append(f"  Model score:  {v2['model_score']}/10")
        lines.append(f"  Combined:     {v2['combined_score']:.1f}/10")
        lines.append(f"  Reasoning:    {v2['model_reasoning']}")
        lines.append(f"  Strengths:    {', '.join(v2['model_strengths'])}")
        lines.append(f"  Weaknesses:   {', '.join(v2['model_weaknesses'])}")
        lines.append("")

    # --- Key takeaways ---
    lines.append(sep)
    lines.append("  KEY TAKEAWAYS")
    lines.append(sep)
    lines.append("")
    lines.append("  1. PROMPT EVALUATION = OBJECTIVE MEASUREMENT")
    lines.append("     Instead of 'this prompt feels better', you get numbers.")
    lines.append("     V1 scored X/10, V2 scored Y/10 — clear, comparable, trackable.")
    lines.append("")
    lines.append("  2. TWO GRADER TYPES COVER DIFFERENT ASPECTS")
    lines.append("     Code grader: 'Is the syntax valid?' (binary, deterministic)")
    lines.append("     Model grader: 'Is the solution correct and helpful?' ( nuanced)")
    lines.append("     Neither alone gives the full picture. Combined = comprehensive.")
    lines.append("")
    lines.append("  3. ITERATION IS THE POINT")
    lines.append("     V1 is your baseline. V2 is your first improvement.")
    lines.append("     The delta between them proves whether your changes helped.")
    lines.append("     Keep iterating: V3, V4, V5... until scores plateau.")
    lines.append("")
    lines.append("  4. DATASET QUALITY MATTERS")
    lines.append("     3 test cases is minimal. Production evals use 50-200+ cases.")
    lines.append("     Include edge cases, ambiguous inputs, and realistic scenarios.")
    lines.append("     The dataset IS your test suite for prompts.")
    lines.append("")
    lines.append("  5. THE THREE OPTIONS AFTER WRITING A PROMPT:")
    lines.append("     Option 1: Test once, ship it.    (risky — breaks in production)")
    lines.append("     Option 2: Test a few times, tweak. (better — still misses edge cases)")
    lines.append("     Option 3: Run through eval pipeline. (best — objective metrics)")
    lines.append("")
    lines.append("  This exercise implements Option 3.")

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
    print("  PROMPT EVALUATION EXERCISE")
    print("  Dataset generation -> V1 vs V2 -> Code + Model grading")
    print("=" * 60)
    print()

    # Step 1: Generate dataset
    print("  [1/3] Generating evaluation dataset...")
    dataset = generate_dataset()
    print(f"        Generated {len(dataset)} test cases:")
    for i, tc in enumerate(dataset, 1):
        print(f"          {i}. [{tc['format']}] {tc['task'][:60]}...")
    print()

    # Step 2: Run evaluation pipeline
    print("  [2/3] Running evaluation (2 prompts x {} cases = {} API calls)...".format(
        len(dataset), len(dataset) * 2 + len(dataset) * 2  # 2 prompt runs + 2 grade runs per case
    ))
    start_time = time.time()
    eval_data = run_eval(dataset)
    elapsed = time.time() - start_time
    print(f"        Done in {elapsed:.1f}s")
    print()

    # Step 3: Save and display results
    print("  [3/3] Saving report...")
    filepath = save_report(eval_data)
    print()

    # Print summary to console
    summary = eval_data["summary"]
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print()
    print(f"  V1 (naive)    combined: {summary['v1_avg_combined']:.1f}/10")
    print(f"                syntax:   {summary['v1_avg_syntax']:.1f}/10")
    print(f"                model:    {summary['v1_avg_model']:.1f}/10")
    print()
    print(f"  V2 (improved) combined: {summary['v2_avg_combined']:.1f}/10")
    print(f"                syntax:   {summary['v2_avg_syntax']:.1f}/10")
    print(f"                model:    {summary['v2_avg_model']:.1f}/10")
    print()
    print(f"  Improvement: {summary['improvement']:+.1f} points")
    print()
    print(f"  Full report saved to: {filepath}")
