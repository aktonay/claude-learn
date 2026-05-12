"""
Tool Functions & Schemas
========================
Three tool functions that extend the model's capabilities:

1. get_current_datetime()  — model doesn't know exact current time
2. add_duration_to_datetime() — model struggles with date arithmetic
3. set_reminder() — model has no built-in reminder mechanism

Each tool has:
  - A Python function (the actual implementation)
  - A JSON schema (tells the model HOW to call it)

On OpenAI-compatible APIs, tool schemas use the format:
  {
    "type": "function",
    "function": {
      "name": "...",
      "description": "...",
      "parameters": {
        "type": "object",
        "properties": {...},
        "required": [...]
      }
    }
  }

The model reads the schema and decides WHEN to call each tool.
It returns a tool_calls list with function name + JSON arguments.
Your code then executes the function and sends results back.

This is the "bridge" between what the model knows from training
and what it needs from the real world (current time, date math, actions).
"""

import json
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Tool 1: Get Current Date/Time
# ---------------------------------------------------------------------------
# The model knows today's date from its training cutoff context, but NOT the
# exact current time. This tool gives it precise, real-time information.
#
# Why: If a user says "remind me in 5 minutes", the model needs to know
# the EXACT current time to calculate when the reminder should fire.

def get_current_datetime(date_format="%Y-%m-%d %H:%M:%S"):
    """
    Returns the current date and time formatted according to the given format.

    Args:
        date_format: A Python strftime format string.
                     Default: "%Y-%m-%d %H:%M:%S" → "2026-05-12 20:30:45"
                     Examples:
                       "%H:%M"       → "20:30"
                       "%Y-%m-%d"    → "2026-05-12"
                       "%A, %B %d"   → "Monday, May 12"

    Returns:
        String with the formatted current date/time.
    """
    if not date_format:
        raise ValueError("date_format cannot be empty")
    return datetime.now().strftime(date_format)


# Schema: tells the model this tool exists and how to use it
# - name: matches the function name exactly
# - description: WHEN to use it + what it returns (3-4 sentences)
# - parameters: JSON Schema format for arguments
get_current_datetime_schema = {
    "type": "function",
    "function": {
        "name": "get_current_datetime",
        "description": (
            "Returns the current date and time. "
            "Use this when you need to know the exact current date or time. "
            "Accepts an optional date_format string using Python strftime codes. "
            "Returns a formatted string with the current date/time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date_format": {
                    "type": "string",
                    "description": (
                        "A Python strftime format string for the output. "
                        "Default: '%Y-%m-%d %H:%M:%S'. "
                        "Examples: '%H:%M' for time only, '%Y-%m-%d' for date only."
                    ),
                    "default": "%Y-%m-%d %H:%M:%S",
                }
            },
            "required": [],
        },
    },
}


# ---------------------------------------------------------------------------
# Tool 2: Add Duration to Date/Time
# ---------------------------------------------------------------------------
# The model can do simple date math ("3 days after Monday = Thursday"),
# but struggles with complex calculations like "177 days from Jan 1, 2050".
# This tool gives it reliable date arithmetic.
#
# Why: User says "remind me in 2 weeks" → model needs to:
#   1. Call get_current_datetime() to get "2026-05-12 20:30:45"
#   2. Call add_duration_to_datetime("2026-05-12 20:30:45", days=14)
#      to get "2026-05-26 20:30:45"

def add_duration_to_datetime(
    start_datetime,
    days=0,
    hours=0,
    minutes=0,
    seconds=0,
    date_format="%Y-%m-%d %H:%M:%S",
):
    """
    Adds a time duration to a given datetime string.

    Args:
        start_datetime: A datetime string (must match date_format).
        days: Number of days to add (default 0).
        hours: Number of hours to add (default 0).
        minutes: Number of minutes to add (default 0).
        seconds: Number of seconds to add (default 0).
        date_format: Format of start_datetime and the output.

    Returns:
        String with the resulting datetime, formatted.
    """
    if not start_datetime:
        raise ValueError("start_datetime cannot be empty")
    dt = datetime.strptime(start_datetime, date_format)
    result = dt + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return result.strftime(date_format)


add_duration_to_datetime_schema = {
    "type": "function",
    "function": {
        "name": "add_duration_to_datetime",
        "description": (
            "Adds a time duration (days, hours, minutes, seconds) to a datetime string. "
            "Use this when you need to calculate a future date/time from a known start point. "
            "The start_datetime must match the provided date_format. "
            "Returns the resulting datetime as a formatted string."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_datetime": {
                    "type": "string",
                    "description": (
                        "The starting datetime string. Must match date_format. "
                        "Example: '2026-05-12 20:30:45'"
                    ),
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to add. Default: 0.",
                    "default": 0,
                },
                "hours": {
                    "type": "integer",
                    "description": "Number of hours to add. Default: 0.",
                    "default": 0,
                },
                "minutes": {
                    "type": "integer",
                    "description": "Number of minutes to add. Default: 0.",
                    "default": 0,
                },
                "seconds": {
                    "type": "integer",
                    "description": "Number of seconds to add. Default: 0.",
                    "default": 0,
                },
                "date_format": {
                    "type": "string",
                    "description": "strftime format for parsing start_datetime and formatting output.",
                    "default": "%Y-%m-%d %H:%M:%S",
                },
            },
            "required": ["start_datetime"],
        },
    },
}


# ---------------------------------------------------------------------------
# Tool 3: Set Reminder
# ---------------------------------------------------------------------------
# The model has no built-in way to "set a reminder" — it can only generate
# text. This tool gives it the ability to record a reminder that persists
# (in our case, saved to a list that gets logged to file).
#
# Why: User says "remind me about my doctor's appointment next Thursday" →
#   1. Model calls get_current_datetime()
#   2. Model calls add_duration_to_datetime() to calculate the date
#   3. Model calls set_reminder() with the calculated date + message

# In-memory store for reminders set during this session
_reminders = []


def set_reminder(reminder_text, reminder_datetime, date_format="%Y-%m-%d %H:%M:%S"):
    """
    Sets a reminder with a message and a target datetime.

    Args:
        reminder_text: What to remind about (e.g., "Doctor's appointment").
        reminder_datetime: When to trigger the reminder (must match date_format).
        date_format: Format of reminder_datetime.

    Returns:
        Dict confirming the reminder was set, with parsed datetime.
    """
    if not reminder_text:
        raise ValueError("reminder_text cannot be empty")
    if not reminder_datetime:
        raise ValueError("reminder_datetime cannot be empty")

    # Validate the datetime string by parsing it
    parsed_dt = datetime.strptime(reminder_datetime, date_format)

    reminder = {
        "text": reminder_text,
        "datetime": reminder_datetime,
        "parsed_datetime": parsed_dt.isoformat(),
        "set_at": datetime.now().isoformat(),
    }
    _reminders.append(reminder)

    return {
        "status": "reminder_set",
        "reminder": reminder,
        "total_reminders": len(_reminders),
    }


set_reminder_schema = {
    "type": "function",
    "function": {
        "name": "set_reminder",
        "description": (
            "Sets a reminder with a descriptive text and a target datetime. "
            "Use this when the user wants to be reminded about something at a specific time. "
            "The reminder_datetime must be a valid datetime string matching date_format. "
            "Returns a confirmation with the reminder details."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reminder_text": {
                    "type": "string",
                    "description": (
                        "What the reminder is about. "
                        "Example: 'Doctor appointment', 'Team meeting', 'Call mom'"
                    ),
                },
                "reminder_datetime": {
                    "type": "string",
                    "description": (
                        "When the reminder should trigger. "
                        "Must match date_format. "
                        "Example: '2026-05-26 14:00:00'"
                    ),
                },
                "date_format": {
                    "type": "string",
                    "description": "strftime format of reminder_datetime.",
                    "default": "%Y-%m-%d %H:%M:%S",
                },
            },
            "required": ["reminder_text", "reminder_datetime"],
        },
    },
}


# ---------------------------------------------------------------------------
# Tool Router — maps tool name → function call
# ---------------------------------------------------------------------------
# When the model returns tool_calls, each call has a function name and args.
# This function dispatches to the right Python function.
#
# Pattern: add new tools by adding an elif branch here.
# The model never sees this function — it's your server-side routing logic.

def run_tool(tool_name, tool_input):
    """
    Route a tool call to the correct function.

    Args:
        tool_name: Name of the tool the model wants to call.
        tool_input: Dict of arguments from the model's tool_calls.

    Returns:
        Whatever the tool function returns (usually a string or dict).
    """
    if tool_name == "get_current_datetime":
        return get_current_datetime(**tool_input)
    elif tool_name == "add_duration_to_datetime":
        return add_duration_to_datetime(**tool_input)
    elif tool_name == "set_reminder":
        return set_reminder(**tool_input)
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# ---------------------------------------------------------------------------
# All schemas in one list — pass this to the API call
# ---------------------------------------------------------------------------
ALL_TOOL_SCHEMAS = [
    get_current_datetime_schema,
    add_duration_to_datetime_schema,
    set_reminder_schema,
]


# ---------------------------------------------------------------------------
# Access reminders (for logging after the session)
# ---------------------------------------------------------------------------
def get_all_reminders():
    """Return all reminders set during this session."""
    return list(_reminders)


def clear_reminders():
    """Clear all reminders (useful between test runs)."""
    _reminders.clear()
