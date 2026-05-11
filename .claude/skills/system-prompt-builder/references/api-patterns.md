# System Prompt API Patterns
# How to use system prompts programmatically with different APIs.

## Pattern 1: OpenAI-Compatible API (ZAI, OpenAI, etc.)

# System prompt goes as the FIRST message in the messages array with role "system".
# This is the most common pattern for OpenAI-compatible endpoints.

```python
from openai import OpenAI

client = OpenAI(api_key="...", base_url="...")

messages = [
    {"role": "system", "content": "You are a patient math tutor."},
    {"role": "user", "content": "How do I solve 5x + 2 = 3?"},
]

response = client.chat.completions.create(
    model="glm-4.5-air",
    max_tokens=1000,
    messages=messages,
)
```

## Pattern 2: Anthropic Claude API

# System prompt is a SEPARATE parameter, NOT in the messages array.
# This is the original pattern from the lesson.

```python
import anthropic

client = anthropic.Anthropic(api_key="...")

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    system="You are a patient math tutor.",  # separate parameter
    messages=[
        {"role": "user", "content": "How do I solve 5x + 2 = 3?"},
    ],
)
```

## Pattern 3: Loading System Prompt from File

# Store prompts in files so they're easy to update without touching code.

```python
import os

def load_system_prompt(project_name):
    """Load a system prompt from .claude/system-prompts/<name>.md"""
    prompt_path = f".claude/system-prompts/{project_name}.md"

    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    return None

# Usage:
system = load_system_prompt("math-tutor")
if system:
    messages.insert(0, {"role": "system", "content": system})
```

## Pattern 4: Flexible Chat Function (works with or without system prompt)

# The most reusable pattern — accepts system prompt as optional parameter.

```python
def chat(messages, system_prompt=None):
    """Send messages with optional system prompt (OpenAI-compatible)."""
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
```

## Key Difference Between APIs

# | API              | System prompt location  | Example                    |
# |------------------|------------------------|----------------------------|
# | OpenAI / ZAI     | First message (role: "system") | messages=[{"role":"system",...}, ...] |
# | Anthropic Claude | Separate parameter     | system="...", messages=[...]        |
#
# Always check which API you're using — the pattern is different!
