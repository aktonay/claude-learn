"""
Conversation Loop for Tool Calling
====================================
The core pattern for multi-turn tool use:

1. Send user message + tool schemas to the model
2. Model responds with either:
   a. Plain text (done — no tools needed)
   b. tool_calls list (model wants to call tools)
3. If tool_calls: execute each tool, send results back
4. Repeat until the model responds with plain text (no more tools)

This is the "agentic loop" — the model decides what tools to call,
your code executes them, and the loop continues until the model
has enough information to answer the user.

Key concepts:
  - finish_reason == "tool_calls" means the model wants tools
  - finish_reason == "stop" means the model is done
  - Each tool call has an ID that must match the tool result
  - The FULL conversation history is sent every turn (model is stateless)
  - Multiple tools can be requested in a single response

OpenAI-compatible API tool calling format:
  - Request: tools=[{"type": "function", "function": {...}}]
  - Response: message.tool_calls = [ChatCompletionMessageFunctionToolCall(...)]
  - Tool result: {"role": "tool", "tool_call_id": "...", "content": "..."}
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from tool_functions import run_tool, ALL_TOOL_SCHEMAS, get_all_reminders

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
# Chat helper — sends messages + tools, returns full response object
# ---------------------------------------------------------------------------
def chat(messages, tools=None):
    """
    Send messages to the model with optional tool schemas.

    Args:
        messages: Conversation history (list of dicts).
        tools: List of tool schema dicts. None = no tools.

    Returns:
        Full ChatCompletion response object (not just text).
    """
    params = {
        "model": MODEL,
        "max_tokens": 2000,
        "messages": messages,
    }
    if tools:
        params["tools"] = tools

    return client.chat.completions.create(**params)


# ---------------------------------------------------------------------------
# Helper: extract text from a response (ignoring tool call blocks)
# ---------------------------------------------------------------------------
def extract_text(response):
    """
    Get the text content from a model response.
    When the model calls tools, it may also include text explaining what it's doing.
    This extracts just the text portions.

    Args:
        response: ChatCompletion response object.

    Returns:
        String of all text content joined together.
    """
    message = response.choices[0].message
    # message.content can be None when the model only returns tool calls
    if message.content:
        return message.content.strip()
    return ""


# ---------------------------------------------------------------------------
# Helper: extract tool calls from a response
# ---------------------------------------------------------------------------
def extract_tool_calls(response):
    """
    Get tool calls from a model response.

    Args:
        response: ChatCompletion response object.

    Returns:
        List of tool call objects, or empty list if none.
    """
    message = response.choices[0].message
    if message.tool_calls:
        return message.tool_calls
    return []


# ---------------------------------------------------------------------------
# Helper: check if the model wants to call tools
# ---------------------------------------------------------------------------
def wants_tools(response):
    """
    Check if the model is requesting tool calls (vs. giving a final answer).

    On OpenAI-compatible APIs:
      finish_reason == "tool_calls" → model wants to call tools
      finish_reason == "stop"       → model is done, has final answer
    """
    return response.choices[0].finish_reason == "tool_calls"


# ---------------------------------------------------------------------------
# Execute tool calls and build result messages
# ---------------------------------------------------------------------------
def execute_tool_calls(tool_calls):
    """
    Execute each tool call and build the tool result messages.

    For each tool call the model makes, we:
      1. Parse the function name and JSON arguments
      2. Call the matching Python function via run_tool()
      3. Build a tool result message with the output
      4. If the function fails, send an error result (model can retry)

    Args:
        tool_calls: List of tool call objects from the model response.

    Returns:
        List of tool result dicts to append to messages.
    """
    tool_results = []

    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        # The model sends arguments as a JSON string — parse it
        try:
            tool_input = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            tool_input = {}

        print(f"    [TOOL CALL] {tool_name}({json.dumps(tool_input)})")

        # Execute the tool function, handle errors gracefully
        try:
            tool_output = run_tool(tool_name, tool_input)
            # Convert output to string for the API
            if isinstance(tool_output, (dict, list)):
                output_str = json.dumps(tool_output)
            else:
                output_str = str(tool_output)

            print(f"    [TOOL RESULT] {output_str[:100]}")

            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": output_str,
            })
        except Exception as e:
            # On error, still send a result — the model can read the error
            # and potentially retry with different arguments
            error_msg = f"Error executing {tool_name}: {e}"
            print(f"    [TOOL ERROR] {error_msg}")

            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": error_msg,
            })

    return tool_results


# ---------------------------------------------------------------------------
# The Main Conversation Loop
# ---------------------------------------------------------------------------
def run_conversation(user_message, tools=None, max_turns=10):
    """
    Run a complete multi-turn tool-use conversation.

    The loop:
      1. Send user message + tools to the model
      2. If model wants tools → execute them, send results back, repeat
      3. If model is done → return final text response

    Args:
        user_message: The user's request string.
        tools: List of tool schemas. Default: ALL_TOOL_SCHEMAS.
        max_turns: Safety limit to prevent infinite loops.

    Returns:
        Dict with:
          - "messages": full conversation history
          - "final_response": the model's final text answer
          - "turns": number of turns taken
          - "tool_calls_made": list of all tool calls executed
    """
    if tools is None:
        tools = ALL_TOOL_SCHEMAS

    # Start conversation history with the user's message
    messages = [{"role": "user", "content": user_message}]

    all_tool_calls = []
    turns = 0

    print(f"  [USER] {user_message}")
    print()

    while turns < max_turns:
        turns += 1
        print(f"  --- Turn {turns} ---")

        # Step 1: Send to model
        response = chat(messages, tools=tools)

        # Step 2: Add assistant message to history
        # IMPORTANT: Must include tool_calls if present, or the API will error
        assistant_msg = {
            "role": "assistant",
            "content": response.choices[0].message.content or "",
        }
        if response.choices[0].message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.choices[0].message.tool_calls
            ]
        messages.append(assistant_msg)

        # Show any text the model included
        text = extract_text(response)
        if text:
            print(f"  [MODEL] {text}")

        # Step 3: Check if model wants tools or is done
        if not wants_tools(response):
            print()
            print(f"  [DONE] Model finished after {turns} turn(s)")
            break

        # Step 4: Execute tool calls
        tool_calls = extract_tool_calls(response)
        all_tool_calls.extend(tool_calls)
        tool_results = execute_tool_calls(tool_calls)

        # Step 5: Add tool results to conversation history
        # Each tool result must reference the correct tool_call_id
        for result in tool_results:
            messages.append(result)

        print()

    # Extract final answer
    final_response = extract_text(response)

    return {
        "messages": messages,
        "final_response": final_response,
        "turns": turns,
        "tool_calls_made": all_tool_calls,
    }


# ---------------------------------------------------------------------------
# Save conversation log
# ---------------------------------------------------------------------------
def save_log(conversation_result, user_message, filepath=None):
    """
    Save a formatted conversation log to file.

    Args:
        conversation_result: Dict from run_conversation().
        user_message: Original user request.
        filepath: Optional path. Auto-generated if None.

    Returns:
        Path to the saved log file.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)

    if filepath is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(LOGS_DIR, f"tool_use_{timestamp}.txt")

    sep = "=" * 70
    lines = []

    lines.append(sep)
    lines.append("  TOOL USE — CONVERSATION LOG")
    lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Model: {MODEL}")
    lines.append(f"  Turns: {conversation_result['turns']}")
    lines.append(sep)
    lines.append("")

    # Explain the flow
    lines.append("  HOW TOOL CALLING WORKS:")
    lines.append("-" * 70)
    lines.append("")
    lines.append("  1. User sends a message along with tool schemas")
    lines.append("  2. Model decides if it needs tools to answer")
    lines.append("  3. If yes: model returns tool_calls (function name + JSON args)")
    lines.append("  4. Your code executes the functions and sends results back")
    lines.append("  5. Model uses tool results to give a final answer")
    lines.append("  6. Loop continues until model stops requesting tools")
    lines.append("")
    lines.append("  OpenAI-compatible format:")
    lines.append('    Request:  tools=[{"type": "function", "function": {...}}]')
    lines.append("    Response: message.tool_calls = [{id, function: {name, arguments}}]")
    lines.append('    Result:   {"role": "tool", "tool_call_id": "...", "content": "..."}')
    lines.append("")
    lines.append("  TOOLS AVAILABLE:")
    lines.append("  - get_current_datetime: returns current date/time")
    lines.append("  - add_duration_to_datetime: adds days/hours/minutes to a datetime")
    lines.append("  - set_reminder: records a reminder with message + target time")
    lines.append("")

    # Full message trace
    lines.append(sep)
    lines.append("  FULL CONVERSATION TRACE")
    lines.append(sep)
    lines.append("")

    for i, msg in enumerate(conversation_result["messages"]):
        role = msg["role"].upper()

        if role == "USER":
            lines.append(f"  [{i+1}] USER MESSAGE:")
            lines.append(f"      {msg['content']}")

        elif role == "ASSISTANT":
            lines.append(f"  [{i+1}] ASSISTANT MESSAGE:")
            if msg.get("content"):
                lines.append(f"      Text: {msg['content']}")
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    func = tc["function"]
                    lines.append(f"      Tool Call: {func['name']}({func['arguments']})")

        elif role == "TOOL":
            lines.append(f"  [{i+1}] TOOL RESULT:")
            content = msg.get("content", "")
            # Try to pretty-print JSON
            try:
                parsed = json.loads(content)
                lines.append(f"      {json.dumps(parsed, indent=6)}")
            except (json.JSONDecodeError, TypeError):
                lines.append(f"      {content}")

        lines.append("")

    # Final answer
    lines.append(sep)
    lines.append("  FINAL ANSWER")
    lines.append(sep)
    lines.append("")
    lines.append(f"  {conversation_result['final_response']}")
    lines.append("")

    # Reminders set
    reminders = get_all_reminders()
    if reminders:
        lines.append(sep)
        lines.append("  REMINDERS SET THIS SESSION")
        lines.append(sep)
        lines.append("")
        for i, r in enumerate(reminders, 1):
            lines.append(f"  {i}. \"{r['text']}\"")
            lines.append(f"     When: {r['datetime']}")
            lines.append(f"     Set at: {r['set_at']}")
            lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath
