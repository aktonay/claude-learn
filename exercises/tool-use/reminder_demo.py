"""
Tool Use Exercise — Reminder System
=====================================
Demonstrates the complete tool-use pattern with 3 scenarios:

Demo 1 — "What time is it?"
  Model calls: get_current_datetime
  Turns: 1
  Shows: simplest tool call (one tool, one argument)

Demo 2 — "What day is 103 days from today?"
  Model calls: get_current_datetime → add_duration_to_datetime
  Turns: 2
  Shows: multi-turn chaining (model needs result from tool 1 to call tool 2)

Demo 3 — "Set a reminder for my doctor's appointment, it's a week from today"
  Model calls: get_current_datetime → add_duration_to_datetime → set_reminder
  Turns: 3
  Shows: full 3-tool pipeline (get time → calculate future → set reminder)

Each demo shows the multi-turn tool calling loop in action:
  - The model decides WHICH tools to call and in what ORDER
  - Your code executes the tools and sends results back
  - The model uses tool results to decide next steps
  - Loop continues until the model has enough info for a final answer

Run: python reminder_demo.py
"""

import sys
import os
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from tool_functions import clear_reminders, get_all_reminders
from conversation_loop import run_conversation, save_log, MODEL


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------
DEMOS = [
    {
        "name": "SINGLE TOOL — Get current time",
        "description": "Model calls one tool (get_current_datetime) and returns the answer.",
        "message": "What time is it right now? Please give me the exact time formatted as HH:MM:SS.",
    },
    {
        "name": "TOOL CHAINING — Calculate a future date",
        "description": "Model chains 2 tools: get time, then add 103 days.",
        "message": "What day is 103 days from today?",
    },
    {
        "name": "FULL PIPELINE — Set a reminder",
        "description": "Model chains all 3 tools: get time → add 7 days → set reminder.",
        "message": (
            "Set a reminder for my doctor's appointment. "
            "It's a week from today at 2:30 PM. "
            "The reminder text should say 'Doctor appointment'."
        ),
    },
]


# ---------------------------------------------------------------------------
# Run all demos
# ---------------------------------------------------------------------------
def run_all_demos():
    """Run all 3 demo scenarios and save combined results."""

    all_results = []
    all_logs = []

    print("=" * 70)
    print("  TOOL USE EXERCISE — Reminder System")
    print(f"  Model: {MODEL}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    for i, demo in enumerate(DEMOS, 1):
        # Clear reminders between demos so each starts fresh
        clear_reminders()

        print()
        print("=" * 70)
        print(f"  DEMO {i}: {demo['name']}")
        print(f"  {demo['description']}")
        print("=" * 70)
        print()

        result = run_conversation(demo["message"])
        all_results.append({
            "demo": demo,
            "result": result,
            "reminders": get_all_reminders(),
        })

        print()
        print(f"  Final answer: {result['final_response']}")
        print(f"  Turns: {result['turns']}  |  Tool calls: {len(result['tool_calls_made'])}")
        print()

    # Save combined log
    filepath = save_combined_log(all_results)
    return filepath


# ---------------------------------------------------------------------------
# Save combined log for all demos
# ---------------------------------------------------------------------------
def save_combined_log(all_results):
    """Save all demo results into one formatted log file."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(logs_dir, f"tool_use_demos_{timestamp}.txt")

    sep = "=" * 70
    lines = []

    # Header
    lines.append(sep)
    lines.append("  TOOL USE EXERCISE — REMINDER SYSTEM")
    lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Model: {MODEL}")
    lines.append(sep)
    lines.append("")

    # How it works
    lines.append("  HOW TOOL CALLING WORKS (OpenAI-compatible API):")
    lines.append("-" * 70)
    lines.append("")
    lines.append("  THE FLOW:")
    lines.append("  1. You send a user message + tool schemas to the model")
    lines.append("  2. Model decides if it needs external data to answer")
    lines.append("  3. If yes: model returns finish_reason='tool_calls'")
    lines.append("     with a tool_calls list: [{id, function: {name, arguments}}]")
    lines.append("  4. Your code executes each tool function")
    lines.append("  5. You send tool results back as: {role: 'tool', tool_call_id, content}")
    lines.append("  6. Model uses results to either:")
    lines.append("     a. Call more tools (loop back to step 2)")
    lines.append("     b. Give a final text answer (finish_reason='stop')")
    lines.append("")
    lines.append("  THE 3 TOOLS:")
    lines.append("  ┌─────────────────────────┬────────────────────────────────────┐")
    lines.append("  │ Tool                    │ Purpose                            │")
    lines.append("  ├─────────────────────────┼────────────────────────────────────┤")
    lines.append("  │ get_current_datetime    │ Returns current date/time          │")
    lines.append("  │ add_duration_to_datetime│ Adds days/hours/min to a datetime  │")
    lines.append("  │ set_reminder            │ Records reminder with target time  │")
    lines.append("  └─────────────────────────┴────────────────────────────────────┘")
    lines.append("")
    lines.append("  WHY TOOLS ARE NEEDED:")
    lines.append("  - Model doesn't know EXACT current time → tool 1 fixes this")
    lines.append("  - Model struggles with complex date math → tool 2 fixes this")
    lines.append("  - Model can't actually SET anything → tool 3 fixes this")
    lines.append("")
    lines.append("  KEY INSIGHT:")
    lines.append("  The model decides WHAT tools to call and in WHAT ORDER.")
    lines.append("  Your job is to provide the implementations.")
    lines.append("  This is the 'agentic loop' pattern used in all AI agent systems.")
    lines.append("")

    # Each demo
    for i, entry in enumerate(all_results, 1):
        demo = entry["demo"]
        result = entry["result"]
        reminders = entry["reminders"]

        lines.append(sep)
        lines.append(f"  DEMO {i}: {demo['name']}")
        lines.append(f"  {demo['description']}")
        lines.append(sep)
        lines.append("")
        lines.append(f"  User request: {demo['message']}")
        lines.append(f"  Turns taken: {result['turns']}")
        lines.append(f"  Tool calls made: {len(result['tool_calls_made'])}")
        lines.append("")

        # Full message trace
        lines.append("  Conversation trace:")
        lines.append("-" * 70)
        for j, msg in enumerate(result["messages"]):
            role = msg["role"].upper()

            if role == "USER":
                lines.append(f"  [{j+1}] USER:")
                lines.append(f"      {msg['content']}")

            elif role == "ASSISTANT":
                lines.append(f"  [{j+1}] ASSISTANT:")
                if msg.get("content"):
                    lines.append(f"      Text: {msg['content']}")
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        func = tc["function"]
                        lines.append(f"      Tool Call: {func['name']}({func['arguments']})")

            elif role == "TOOL":
                lines.append(f"  [{j+1}] TOOL RESULT:")
                content = msg.get("content", "")
                try:
                    import json
                    parsed = json.loads(content)
                    lines.append(f"      {json.dumps(parsed, indent=6)}")
                except (json.JSONDecodeError, TypeError):
                    lines.append(f"      {content}")

            lines.append("")

        # Final answer
        lines.append(f"  Final answer: {result['final_response']}")
        lines.append("")

        # Reminders
        if reminders:
            lines.append(f"  Reminders set: {len(reminders)}")
            for r in reminders:
                lines.append(f"    - \"{r['text']}\" at {r['datetime']}")
            lines.append("")

    # Summary
    lines.append(sep)
    lines.append("  SUMMARY")
    lines.append(sep)
    lines.append("")
    lines.append("  | Demo | Scenario       | Tools Called                          | Turns |")
    lines.append("  |------|-----------------|---------------------------------------|-------|")
    lines.append("  | 1    | Current time    | get_current_datetime                  | 1     |")
    lines.append("  | 2    | Future date     | get_current → add_duration            | 2     |")
    lines.append("  | 3    | Set reminder    | get_current → add_duration → reminder | 2-3   |")
    lines.append("")
    lines.append("  PATTERN FOR ADDING NEW TOOLS:")
    lines.append("  1. Write the Python function (tool_functions.py)")
    lines.append("  2. Write the JSON schema (tool_functions.py)")
    lines.append("  3. Add routing in run_tool() (tool_functions.py)")
    lines.append("  4. Add schema to ALL_TOOL_SCHEMAS list (tool_functions.py)")
    lines.append("  That's it — the conversation loop handles everything else.")
    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    filepath = run_all_demos()
    print()
    print(f"  Full results saved to: {filepath}")
