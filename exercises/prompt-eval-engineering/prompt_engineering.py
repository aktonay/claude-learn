"""
Prompt Engineering Techniques Exercise
=======================================
Demonstrates how 4 prompt engineering techniques improve output quality,
measured objectively through a full evaluation pipeline.

The 4 steps (each building on the previous):
  Step 1: Be Clear and Direct (naive baseline)
  Step 2: Be Specific (add output quality guidelines + process steps)
  Step 3: Use XML Tags (structure content with clear boundaries)
  Step 4: Provide Examples (add sample input/output pairs)

Each step:
  - Runs the same test dataset through the updated prompt
  - Grades outputs using a model grader
  - Records scores to track progression

At the end:
  - A .txt log shows the full step-by-step progression
  - An .html report provides a visual comparison table

Adapted from Anthropic's prompt evaluation tutorial for the ZAI
OpenAI-compatible API (glm-4.5-air model).
"""

import os
import sys
import json
import re
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
# HELPER FUNCTIONS
# ===================================================================

def chat(messages, system_prompt=None, temperature=1.0, stop=None, max_tokens=2048):
    all_messages = []
    if system_prompt:
        all_messages.append({"role": "system", "content": system_prompt})
    all_messages.extend(messages)

    params = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": all_messages,
        "temperature": temperature,
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    if stop:
        params["stop"] = stop

    response = client.chat.completions.create(**params)
    return response.choices[0].message.content


def try_parse_json(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


def render_template(template_string, variables):
    placeholders = re.findall(r"{([^{}]+)}", template_string)
    result = template_string
    for placeholder in placeholders:
        if placeholder in variables:
            result = result.replace("{" + placeholder + "}", str(variables[placeholder]))
    return result.replace("{{", "{").replace("}}", "}")


# ===================================================================
# PROMPT EVALUATOR CLASS
# ===================================================================

class PromptEvaluator:
    def __init__(self, max_concurrent_tasks=1):
        self.max_concurrent_tasks = max_concurrent_tasks

    def generate_unique_ideas(self, task_description, prompt_inputs_spec, num_cases):
        example_inputs = ""
        for key, value in prompt_inputs_spec.items():
            example_inputs += f'  - {key}: {value}\n'

        prompt = f"""Generate {num_cases} unique, diverse ideas for testing a prompt that accomplishes this task:

Task: {task_description}

The prompt will receive these inputs:
{example_inputs}

Each idea should represent a distinct scenario or example that tests different aspects of the task.

IMPORTANT: Output ONLY a raw JSON array. No markdown. No backticks. No explanation. Start with [ end with ].
Each item should be a JSON object with an "idea" field containing a brief description.

Example: [{{"idea": "Testing with a competitive bodybuilder during cutting phase"}}, {{"idea": "Testing with an endurance runner who is vegan"}}]

Ensure each idea is:
- Clearly distinct from the others
- Relevant to the task
- Solvable with no more than 400 tokens of output

Generate exactly {num_cases} unique ideas."""

        messages = [{"role": "user", "content": prompt}]
        for attempt in range(3):
            text = chat(messages, max_tokens=8192)
            parsed = try_parse_json(text)
            if parsed is not None:
                ideas = []
                for item in parsed:
                    if isinstance(item, dict) and "idea" in item:
                        ideas.append(item["idea"])
                    elif isinstance(item, str):
                        ideas.append(item)
                if ideas:
                    return ideas
        raise ValueError(f"Could not parse ideas after 3 attempts: {text[:200]}")

    def generate_test_case(self, task_description, idea, prompt_inputs_spec):
        example_inputs = ""
        for key, value in prompt_inputs_spec.items():
            example_inputs += f'      "{key}": "EXAMPLE_VALUE",\n'

        allowed_keys = ", ".join([f'"{key}"' for key in prompt_inputs_spec.keys()])

        prompt = f"""Generate a single detailed test case for a prompt evaluation.

Task: {task_description}

Specific idea to base the test case on: {idea}

Allowed input keys (use ONLY these): {allowed_keys}

IMPORTANT: Output ONLY raw valid JSON. No markdown. No backticks. No explanation. Start with {{ end with }}.

Format:
{{
    "prompt_inputs": {{
{example_inputs}    }},
    "solution_criteria": ["criterion 1", "criterion 2"]
}}

REQUIREMENTS:
- Use ONLY these input keys: {allowed_keys}
- Do NOT add any additional keys to prompt_inputs
- All keys must be included in your response
- Include measurable, concise solution criteria (1-4 items)
- Keep criteria focused on the fundamental task
- Solvable with no more than 400 tokens of output"""

        messages = [{"role": "user", "content": prompt}]
        for attempt in range(3):
            text = chat(messages, max_tokens=8192)
            test_case = try_parse_json(text)
            if test_case is not None:
                test_case["task_description"] = task_description
                test_case["scenario"] = idea
                return test_case
        raise ValueError(f"Could not parse test case after 3 attempts: {text[:300]}")

    def generate_dataset(self, task_description, prompt_inputs_spec, num_cases=3):
        ideas = self.generate_unique_ideas(task_description, prompt_inputs_spec, num_cases)

        dataset = []
        for i, idea in enumerate(ideas, 1):
            print(f"        Generating test case {i}/{len(ideas)}: {idea[:60]}...")
            test_case = self.generate_test_case(task_description, idea, prompt_inputs_spec)
            dataset.append(test_case)

        return dataset

    def grade_output(self, test_case, output, extra_criteria):
        prompt_inputs_str = ""
        for key, value in test_case["prompt_inputs"].items():
            safe_val = value.replace("\n", "\\n")
            prompt_inputs_str += f'  "{key}": "{safe_val}",\n'

        extra_criteria_section = ""
        if extra_criteria:
            extra_criteria_section = f"""
Mandatory Requirements - ANY VIOLATION MEANS AUTOMATIC FAILURE (score of 3 or lower):
<extra_important_criteria>
{extra_criteria}
</extra_important_criteria>
"""

        criteria_text = "\n".join(test_case["solution_criteria"])

        eval_prompt = f"""Evaluate the following AI-generated solution with EXTREME RIGOR.

Original task description:
<task_description>
{test_case["task_description"]}
</task_description>

Original task inputs:
<task_inputs>
{prompt_inputs_str}
</task_inputs>

Solution to Evaluate:
<solution>
{output}
</solution>

Criteria you should use to evaluate the solution:
<criteria>
{criteria_text}
</criteria>

{extra_criteria_section}

Scoring Guidelines:
* Score 1-3: Solution fails to meet one or more MANDATORY requirements
* Score 4-6: Solution meets all mandatory requirements but has significant deficiencies
* Score 7-8: Solution meets all mandatory requirements and most secondary criteria
* Score 9-10: Solution meets all mandatory and secondary criteria

IMPORTANT SCORING INSTRUCTIONS:
* Grade based ONLY on the listed criteria. Do not add extra requirements.
* If a solution meets all criteria, give it a 10.
* ANY violation of a mandatory requirement MUST result in score 3 or lower.
* Use the full 1-10 scale.

IMPORTANT: Output ONLY raw valid JSON. No markdown. No backticks. No explanation.
Start with {{ end with }}.
{{
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1"],
    "reasoning": "explanation",
    "score": 7
}}"""

        messages = [{"role": "user", "content": eval_prompt}]
        eval_text = chat(messages, temperature=0.0, stop=["```"])
        parsed = try_parse_json(eval_text)

        if parsed is None:
            return {
                "strengths": ["N/A"],
                "weaknesses": ["Grader output could not be parsed"],
                "reasoning": "Fallback: grader returned non-JSON output",
                "score": 5,
            }
        return parsed

    def run_single_test(self, test_case, run_prompt_function, extra_criteria=None):
        output = run_prompt_function(test_case["prompt_inputs"])
        model_grade = self.grade_output(test_case, output, extra_criteria)

        return {
            "output": output,
            "test_case": test_case,
            "score": model_grade["score"],
            "reasoning": model_grade.get("reasoning", "N/A"),
            "strengths": model_grade.get("strengths", []),
            "weaknesses": model_grade.get("weaknesses", []),
        }

    def run_evaluation(self, dataset, run_prompt_function, extra_criteria=None):
        results = []
        for i, test_case in enumerate(dataset, 1):
            print(f"          [{i}/{len(dataset)}] {test_case['scenario'][:50]}...")
            result = self.run_single_test(test_case, run_prompt_function, extra_criteria)
            results.append(result)

        avg_score = mean([r["score"] for r in results]) if results else 0
        return {"results": results, "average_score": avg_score}


# ===================================================================
# THE 4 PROMPT VERSIONS
# ===================================================================
# Each version builds on the previous, adding one prompt engineering technique.

def prompt_v1(prompt_inputs):
    """STEP 1: Be Clear and Direct (naive baseline).
    Just ask the question with no structure or guidance."""
    prompt = f"""
What should this person eat?

- Height: {prompt_inputs["height"]}
- Weight: {prompt_inputs["weight"]}
- Goal: {prompt_inputs["goal"]}
- Dietary restrictions: {prompt_inputs["restrictions"]}
"""
    return chat([{"role": "user", "content": prompt}])


def prompt_v2(prompt_inputs):
    """STEP 2: Be Specific.
    Add output quality guidelines and process steps."""
    prompt = f"""
Generate a one-day meal plan for an athlete.

Height: {prompt_inputs["height"]}
Weight: {prompt_inputs["weight"]}
Goal: {prompt_inputs["goal"]}
Dietary restrictions: {prompt_inputs["restrictions"]}

Guidelines:
1. Include accurate daily calorie amount
2. Show protein, fat, and carb amounts
3. Specify when to eat each meal
4. Use only foods that fit restrictions
5. List all portion sizes in grams
6. Keep budget-friendly if mentioned
"""
    return chat([{"role": "user", "content": prompt}])


def prompt_v3(prompt_inputs):
    """STEP 3: Use XML Tags.
    Structure content with clear boundaries using XML tags."""
    prompt = f"""
Generate a one-day meal plan for an athlete that meets their dietary restrictions.

<athlete_information>
- Height: {prompt_inputs["height"]}
- Weight: {prompt_inputs["weight"]}
- Goal: {prompt_inputs["goal"]}
- Dietary restrictions: {prompt_inputs["restrictions"]}
</athlete_information>

Guidelines:
1. Include accurate daily calorie amount
2. Show protein, fat, and carb amounts
3. Specify when to eat each meal
4. Use only foods that fit restrictions
5. List all portion sizes in grams
6. Keep budget-friendly if mentioned
"""
    return chat([{"role": "user", "content": prompt}])


def prompt_v4(prompt_inputs):
    """STEP 4: Provide Examples.
    Add a sample input/output pair to guide the model."""
    prompt = f"""
Generate a one-day meal plan for an athlete that meets their dietary restrictions.

<athlete_information>
- Height: {prompt_inputs["height"]}
- Weight: {prompt_inputs["weight"]}
- Goal: {prompt_inputs["goal"]}
- Dietary restrictions: {prompt_inputs["restrictions"]}
</athlete_information>

Guidelines:
1. Include accurate daily calorie amount
2. Show protein, fat, and carb amounts
3. Specify when to eat each meal
4. Use only foods that fit restrictions
5. List all portion sizes in grams
6. Keep budget-friendly if mentioned

Here is an example with a sample input and an ideal output:
<sample_input>
height: 170
weight: 70
goal: Maintain fitness and improve cholesterol levels
restrictions: High cholesterol
</sample_input>
<ideal_output>
Here is a one-day meal plan for an athlete aiming to maintain fitness and improve cholesterol levels:

*   **Calorie Target:** Approximately 2500 calories
*   **Macronutrient Breakdown:** Protein (140g), Fat (70g), Carbs (340g)

**Meal Plan:**

*   **Breakfast (7:00 AM):** Oatmeal (80g dry weight) with berries (100g) and walnuts (15g). Skim milk (240g).
    *   Protein: 15g, Fat: 15g, Carbs: 60g
*   **Mid-Morning Snack (10:00 AM):** Apple (150g) with almond butter (30g).
    *   Protein: 7g, Fat: 18g, Carbs: 25g
*   **Lunch (1:00 PM):** Grilled chicken breast (120g) salad with mixed greens (150g), cucumber (50g), tomato (50g), and a light vinaigrette dressing (30g). Whole wheat bread (60g).
    *   Protein: 40g, Fat: 15g, Carbs: 70g
*   **Afternoon Snack (4:00 PM):** Greek yogurt (170g, non-fat) with a banana (120g).
    *   Protein: 20g, Fat: 0g, Carbs: 40g
*   **Dinner (7:00 PM):** Baked salmon (140g) with steamed broccoli (200g) and quinoa (75g dry weight).
    *   Protein: 40g, Fat: 20g, Carbs: 80g
*   **Evening Snack (9:00 PM):** Small handful of almonds (20g).
    *   Protein: 8g, Fat: 12g, Carbs: 15g

This meal plan prioritizes lean protein sources, whole grains, fruits, and vegetables, while limiting saturated and trans fats to support healthy cholesterol levels.
</ideal_output>
This example meal plan is well-structured, provides detailed information on food choices and quantities, and aligns with the athlete's goals and restrictions.
"""
    return chat([{"role": "user", "content": prompt}])


# ===================================================================
# HTML REPORT GENERATOR
# ===================================================================

def generate_html_report(all_steps, dataset, timestamp_str):
    total_cases = len(dataset)

    step_summaries = []
    for step in all_steps:
        results = step["results"]
        scores = [r["score"] for r in results]
        avg = mean(scores) if scores else 0
        pass_rate = 100 * len([s for s in scores if s >= 7]) / len(scores) if scores else 0
        step_summaries.append({
            "name": step["name"],
            "description": step["description"],
            "technique": step["technique"],
            "avg_score": avg,
            "pass_rate": pass_rate,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
        })

    best_avg = max(s["avg_score"] for s in step_summaries)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prompt Engineering Techniques - Evaluation Report</title>
<style>
    body {{
        font-family: 'Segoe UI', Arial, sans-serif;
        line-height: 1.6;
        margin: 0;
        padding: 20px;
        background-color: #f5f5f5;
        color: #333;
    }}
    .header {{
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        color: white;
        padding: 30px;
        border-radius: 10px;
        margin-bottom: 30px;
    }}
    .header h1 {{ margin: 0 0 10px 0; }}
    .header p {{ margin: 0; opacity: 0.8; }}
    .progression {{
        display: flex;
        align-items: flex-end;
        gap: 20px;
        margin: 30px 0;
        padding: 20px;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }}
    .bar-container {{
        flex: 1;
        text-align: center;
    }}
    .bar-wrapper {{
        height: 200px;
        display: flex;
        align-items: flex-end;
        justify-content: center;
        margin-bottom: 10px;
    }}
    .bar {{
        width: 80px;
        border-radius: 8px 8px 0 0;
        transition: height 0.5s ease;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        align-items: center;
        color: white;
        font-weight: bold;
        font-size: 18px;
        padding-bottom: 10px;
    }}
    .bar-step1 {{ background: linear-gradient(180deg, #e74c3c, #c0392b); }}
    .bar-step2 {{ background: linear-gradient(180deg, #f39c12, #e67e22); }}
    .bar-step3 {{ background: linear-gradient(180deg, #3498db, #2980b9); }}
    .bar-step4 {{ background: linear-gradient(180deg, #2ecc71, #27ae60); }}
    .bar-label {{
        font-size: 12px;
        color: #666;
        margin-top: 5px;
        line-height: 1.3;
    }}
    .bar-technique {{
        font-weight: bold;
        color: #333;
        font-size: 13px;
    }}
    .summary-cards {{
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
        margin-bottom: 30px;
    }}
    .card {{
        background: white;
        border-radius: 10px;
        padding: 20px;
        flex: 1;
        min-width: 200px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-top: 4px solid #333;
    }}
    .card.step1 {{ border-top-color: #e74c3c; }}
    .card.step2 {{ border-top-color: #f39c12; }}
    .card.step3 {{ border-top-color: #3498db; }}
    .card.step4 {{ border-top-color: #2ecc71; }}
    .card-title {{ font-size: 14px; color: #888; margin-bottom: 5px; }}
    .card-score {{ font-size: 28px; font-weight: bold; }}
    .card-detail {{ font-size: 12px; color: #666; margin-top: 5px; }}
    .card.best {{ background: #f0fff0; }}
    .section {{
        background: white;
        border-radius: 10px;
        padding: 25px;
        margin-bottom: 25px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }}
    .section h2 {{ margin-top: 0; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
    .technique-explain {{
        background: #f8f9fa;
        border-left: 4px solid #666;
        padding: 15px;
        margin: 15px 0;
        font-size: 14px;
    }}
    .technique-explain code {{
        background: #e8e8e8;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 13px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
    }}
    th {{
        background-color: #1a1a2e;
        color: white;
        text-align: left;
        padding: 12px;
        font-size: 13px;
    }}
    td {{
        padding: 10px 12px;
        border-bottom: 1px solid #eee;
        vertical-align: top;
        font-size: 13px;
    }}
    tr:hover {{ background-color: #f8f9fa; }}
    .score-badge {{
        font-weight: bold;
        padding: 4px 12px;
        border-radius: 20px;
        display: inline-block;
        font-size: 14px;
    }}
    .score-high {{ background-color: #c8e6c9; color: #2e7d32; }}
    .score-mid {{ background-color: #fff9c4; color: #f57f17; }}
    .score-low {{ background-color: #ffcdd2; color: #c62828; }}
    .output-pre {{
        background: #f5f5f5;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 8px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        white-space: pre-wrap;
        word-wrap: break-word;
        max-height: 200px;
        overflow-y: auto;
    }}
    .delta-positive {{ color: #27ae60; font-weight: bold; }}
    .delta-negative {{ color: #e74c3c; font-weight: bold; }}
    .delta-zero {{ color: #888; }}
</style>
</head>
<body>

<div class="header">
    <h1>Prompt Engineering Techniques - Evaluation Report</h1>
    <p>Date: {timestamp_str} | Model: {MODEL} | Test Cases: {total_cases}</p>
</div>

<div class="progression">
    <div style="width: 100px; text-align: right; padding-right: 10px; color: #888; font-size: 13px;">
        Score<br>out of 10
    </div>
"""

    for i, s in enumerate(step_summaries, 1):
        bar_height = max(int((s["avg_score"] / 10) * 180), 20)
        html += f"""
    <div class="bar-container">
        <div class="bar-wrapper">
            <div class="bar bar-step{i}" style="height: {bar_height}px;">
                {s['avg_score']:.1f}
            </div>
        </div>
        <div class="bar-technique">Step {i}</div>
        <div class="bar-label">{s['technique']}</div>
    </div>
"""

    html += """
</div>

<div class="summary-cards">
"""

    for i, s in enumerate(step_summaries, 1):
        prev_score = step_summaries[i - 2]["avg_score"] if i > 1 else None
        delta = s["avg_score"] - prev_score if prev_score is not None else None
        is_best = s["avg_score"] == best_avg

        delta_html = ""
        if delta is not None:
            cls = "delta-positive" if delta > 0 else ("delta-negative" if delta < 0 else "delta-zero")
            sign = "+" if delta > 0 else ""
            delta_html = f'<div class="card-detail {cls}">{sign}{delta:.1f} vs previous</div>'

        html += f"""
    <div class="card step{i} {"best" if is_best else ""}">
        <div class="card-title">Step {i}: {s['technique']}</div>
        <div class="card-score">{s['avg_score']:.1f} / 10</div>
        <div class="card-detail">Pass rate (>7): {s['pass_rate']:.0f}%</div>
        <div class="card-detail">Range: {s['min_score']}-{s['max_score']}</div>
        {delta_html}
    </div>
"""

    html += """
</div>
"""

    for i, step in enumerate(all_steps, 1):
        results = step["results"]
        s = step_summaries[i - 1]

        html += f"""
<div class="section">
    <h2>Step {i}: {s['technique']} &mdash; Average Score: {s['avg_score']:.1f}/10</h2>
    <div class="technique-explain">
        {step['description']}
    </div>
    <table>
        <thead>
            <tr>
                <th style="width:15%">Scenario</th>
                <th style="width:35%">Output (truncated)</th>
                <th style="width:8%">Score</th>
                <th style="width:22%">Reasoning</th>
                <th style="width:10%">Strengths</th>
                <th style="width:10%">Weaknesses</th>
            </tr>
        </thead>
        <tbody>
"""

        for r in results:
            score = r["score"]
            if score >= 8:
                score_cls = "score-high"
            elif score >= 5:
                score_cls = "score-mid"
            else:
                score_cls = "score-low"

            output_truncated = r["output"][:500] + ("..." if len(r["output"]) > 500 else "")
            scenario = html_lib.escape(r["test_case"].get("scenario", "N/A"))
            reasoning = html_lib.escape(r.get("reasoning", "N/A"))
            strengths = html_lib.escape(", ".join(r.get("strengths", [])))
            weaknesses = html_lib.escape(", ".join(r.get("weaknesses", [])))

            html += f"""
            <tr>
                <td>{scenario}</td>
                <td><div class="output-pre">{html_lib.escape(output_truncated)}</div></td>
                <td><span class="score-badge {score_cls}">{score}</span></td>
                <td>{reasoning}</td>
                <td>{strengths}</td>
                <td>{weaknesses}</td>
            </tr>
"""

        html += """
        </tbody>
    </table>
</div>
"""

    html += """
<div class="section">
    <h2>Key Takeaways</h2>
    <div class="technique-explain">
        <strong>Step 1: Be Clear and Direct</strong><br>
        A naive prompt with no guidance. The model has to guess what format, detail level,
        and structure you want. Expect low, inconsistent scores.
    </div>
    <div class="technique-explain">
        <strong>Step 2: Be Specific</strong><br>
        Adding explicit guidelines (calorie count, macro breakdown, meal timing, portion sizes)
        gives the model a clear target. This typically produces the largest score jump.
    </div>
    <div class="technique-explain">
        <strong>Step 3: Use XML Tags</strong><br>
        Wrapping content in XML tags like &lt;athlete_information&gt; creates clear boundaries.
        The model can distinguish instructions from data, reducing confusion.
        Impact grows with prompt complexity.
    </div>
    <div class="technique-explain">
        <strong>Step 4: Provide Examples</strong><br>
        A sample input/output pair shows the model exactly what "good" looks like.
        This is especially powerful for format, tone, and detail-level calibration.
        Find your best-scored outputs from evaluations and use them as examples.
    </div>
    <p>
        <strong>The evaluation pipeline makes this process objective.</strong>
        Instead of "this prompt feels better," you get:
        Step 1 scored X, Step 2 scored Y, Step 3 scored Z, Step 4 scored W.
        Each technique's contribution is measurable.
    </p>
</div>

</body>
</html>
"""
    return html


# ===================================================================
# TXT REPORT GENERATOR
# ===================================================================

def generate_txt_report(all_steps, dataset, timestamp_str):
    sep = "=" * 70
    dash = "-" * 70

    lines = []
    lines.append(sep)
    lines.append("  PROMPT ENGINEERING TECHNIQUES - EVALUATION REPORT")
    lines.append(f"  Date: {timestamp_str}")
    lines.append(f"  Model: {MODEL}")
    lines.append(f"  Test cases: {len(dataset)}")
    lines.append(sep)
    lines.append("")

    # Progression overview
    lines.append(sep)
    lines.append("  SCORE PROGRESSION")
    lines.append(sep)
    lines.append("")

    prev_score = None
    for i, step in enumerate(all_steps, 1):
        avg = step["average_score"]
        delta = ""
        if prev_score is not None:
            d = avg - prev_score
            sign = "+" if d > 0 else ""
            delta = f" ({sign}{d:.1f} vs previous)"
        lines.append(f"  Step {i} [{step['technique']:25s}] {avg:.1f}/10{delta}")
        prev_score = avg

    lines.append("")

    # Technique explanations
    lines.append(sep)
    lines.append("  TECHNIQUES EXPLAINED")
    lines.append(sep)
    lines.append("")

    techniques = [
        ("Step 1: Be Clear and Direct",
         "A naive prompt with no guidance. Just asks the question.",
         "No guidelines, no structure, no examples. The model guesses what you want."),
        ("Step 2: Be Specific",
         "Add output quality guidelines and process steps.",
         "Explicit instructions: calorie count, macro breakdown, meal timing, portion sizes in grams."),
        ("Step 3: Use XML Tags",
         "Structure content with clear boundaries using XML tags.",
         "Wrap athlete data in <athlete_information> tags. Model can distinguish instructions from data."),
        ("Step 4: Provide Examples",
         "Add a sample input/output pair to demonstrate ideal output.",
         "Shows model exactly what 'good' looks like. Calibrates format, tone, detail level."),
    ]

    for name, change, detail in techniques:
        lines.append(f"  {name}")
        lines.append(f"    What changed: {change}")
        lines.append(f"    Why it helps: {detail}")
        lines.append("")

    # Per-step detailed results
    for i, step in enumerate(all_steps, 1):
        lines.append(sep)
        lines.append(f"  STEP {i}: {step['technique'].upper()}")
        lines.append(f"  Average Score: {step['average_score']:.1f}/10")
        lines.append(sep)
        lines.append("")
        lines.append(f"  Technique applied: {step['description']}")
        lines.append("")

        for j, r in enumerate(step["results"], 1):
            tc = r["test_case"]
            lines.append(dash)
            lines.append(f"  Test Case {j}: {tc.get('scenario', 'N/A')[:60]}")
            lines.append(dash)
            lines.append("")
            for k, v in tc.get("prompt_inputs", {}).items():
                lines.append(f"  {k}: {v}")
            lines.append("")
            lines.append(f"  Criteria: {', '.join(tc.get('solution_criteria', []))}")
            lines.append("")
            lines.append(f"  Score: {r['score']}/10")
            lines.append(f"  Reasoning: {r.get('reasoning', 'N/A')}")
            lines.append(f"  Strengths: {', '.join(r.get('strengths', []))}")
            lines.append(f"  Weaknesses: {', '.join(r.get('weaknesses', []))}")
            lines.append("")
            lines.append("  Output:")
            for text_line in r["output"].split("\n")[:15]:
                lines.append(f"    {text_line}")
            if r["output"].count("\n") > 15:
                lines.append(f"    ... ({r['output'].count(chr(10)) - 15} more lines)")
            lines.append("")

    # Takeaways
    lines.append(sep)
    lines.append("  KEY TAKEAWAYS")
    lines.append(sep)
    lines.append("")
    lines.append("  1. BE CLEAR AND DIRECT: Start with a simple, clear ask.")
    lines.append("     This is your baseline. Low scores are expected.")
    lines.append("")
    lines.append("  2. BE SPECIFIC: Add guidelines for format, content, and detail level.")
    lines.append("     This typically produces the LARGEST score improvement.")
    lines.append("")
    lines.append("  3. USE XML TAGS: Structure your prompt with clear boundaries.")
    lines.append("     Impact grows with prompt complexity and data volume.")
    lines.append("")
    lines.append("  4. PROVIDE EXAMPLES: Show, don't tell.")
    lines.append("     One good example calibrates format, tone, and detail better")
    lines.append("     than paragraphs of instructions.")
    lines.append("")
    lines.append("  The evaluation pipeline makes each technique's contribution")
    lines.append("  measurable. You see EXACTLY how much each step improved scores.")

    return "\n".join(lines)


# ===================================================================
# MAIN
# ===================================================================

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("  PROMPT ENGINEERING TECHNIQUES EXERCISE")
    print("  4 steps: naive -> specific -> XML tags -> examples")
    print("=" * 60)
    print()

    evaluator = PromptEvaluator(max_concurrent_tasks=1)

    TASK_DESCRIPTION = "Write a compact, concise 1 day meal plan for a single athlete"
    PROMPT_INPUTS_SPEC = {
        "height": "Athlete's height in cm",
        "weight": "Athlete's weight in kg",
        "goal": "Goal of the athlete",
        "restrictions": "Dietary restrictions of the athlete",
    }
    EXTRA_CRITERIA = """
The output should include:
- Daily caloric total
- Macronutrient breakdown
- Meals with exact foods, portions, and timing
"""
    NUM_CASES = 2

    # Step 0: Generate dataset
    print("  [0/4] Generating evaluation dataset...")
    dataset = evaluator.generate_dataset(
        task_description=TASK_DESCRIPTION,
        prompt_inputs_spec=PROMPT_INPUTS_SPEC,
        num_cases=NUM_CASES,
    )
    print(f"        Generated {len(dataset)} test cases")
    print()

    # Steps 1-4: Run each prompt version
    prompt_versions = [
        {
            "name": "Step 1: Be Clear and Direct",
            "technique": "Be Clear and Direct",
            "description": "Naive baseline. Just asks 'What should this person eat?' with no guidance on format, structure, or detail level.",
            "function": prompt_v1,
        },
        {
            "name": "Step 2: Be Specific",
            "technique": "Be Specific",
            "description": "Adds explicit guidelines: calorie count, macro breakdown, meal timing, portion sizes in grams, budget-friendly.",
            "function": prompt_v2,
        },
        {
            "name": "Step 3: Use XML Tags",
            "technique": "Use XML Tags",
            "description": "Wraps athlete data in <athlete_information> XML tags for clear boundaries between instructions and data.",
            "function": prompt_v3,
        },
        {
            "name": "Step 4: Provide Examples",
            "technique": "Provide Examples",
            "description": "Adds a complete sample input/output pair showing the exact format, detail level, and structure expected.",
            "function": prompt_v4,
        },
    ]

    all_steps = []

    for i, version in enumerate(prompt_versions, 1):
        print(f"  [{i}/4] {version['name']}...")
        start_time = time.time()
        eval_result = evaluator.run_evaluation(
            dataset=dataset,
            run_prompt_function=version["function"],
            extra_criteria=EXTRA_CRITERIA,
        )
        elapsed = time.time() - start_time
        avg = eval_result["average_score"]

        all_steps.append({
            "name": version["name"],
            "technique": version["technique"],
            "description": version["description"],
            "results": eval_result["results"],
            "average_score": avg,
        })

        prev_avg = all_steps[i - 2]["average_score"] if i > 1 else None
        delta_str = ""
        if prev_avg is not None:
            d = avg - prev_avg
            sign = "+" if d > 0 else ""
            delta_str = f" ({sign}{d:.1f})"

        print(f"        Done in {elapsed:.1f}s — Average: {avg:.1f}/10{delta_str}")
        print()

    # Save reports
    print("  Saving reports...")

    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    txt_path = os.path.join(LOGS_DIR, f"prompt_engineering_{timestamp}.txt")
    html_path = os.path.join(LOGS_DIR, f"prompt_engineering_{timestamp}.html")

    txt_content = generate_txt_report(all_steps, dataset, timestamp)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)

    html_content = generate_html_report(all_steps, dataset, timestamp)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Print final summary
    print()
    print("=" * 60)
    print("  FINAL RESULTS")
    print("=" * 60)
    print()

    prev = None
    for i, step in enumerate(all_steps, 1):
        avg = step["average_score"]
        delta_str = ""
        if prev is not None:
            d = avg - prev
            sign = "+" if d > 0 else ""
            delta_str = f" ({sign}{d:.1f})"
        print(f"  Step {i} [{step['technique']:25s}] {avg:.1f}/10{delta_str}")
        prev = avg

    print()
    print(f"  TXT report: {txt_path}")
    print(f"  HTML report: {html_path}")
