"""
Multi-Turn Chatbot Exercise
===========================
Demonstrates how to maintain conversation context across multiple turns.
Claude (and all LLMs) are STATELESS — they remember nothing between requests.
To have a real conversation, YOU must send the full message history every time.

This chatbot uses the ZAI API (OpenAI-compatible endpoint).

Pattern:
  1. User types input
  2. Add user message to history
  3. Send ENTIRE history to the API
  4. Add assistant response to history
  5. Print response
  6. Save full conversation to a formatted .txt file on exit
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Setup: Load API key from .env and configure the client
# .env lives in the PROJECT ROOT — we go up two levels from this script
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# The ZAI API uses an OpenAI-compatible interface
# We point base_url to the ZAI endpoint instead of OpenAI's default
client = OpenAI(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url=os.getenv("ZAI_BASE_URL"),
)

# Available models: glm-4.5, glm-4.5-air, glm-4.6, glm-4.7, glm-5, glm-5-turbo, glm-5.1
# Using glm-4.5-air — fast and lightweight for exercises
MODEL = "glm-4.5-air"

# Folder where conversation logs get saved
# Lives inside this exercise folder, keeps everything organized
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")


# ---------------------------------------------------------------------------
# Helper Function 1: Add a USER message to the conversation
# ---------------------------------------------------------------------------
# Every message needs a "role" so the API knows who said it.
# "user" = the human, "assistant" = the AI
def add_user_message(messages, text):
    """Append a user message to the conversation history."""
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


# ---------------------------------------------------------------------------
# Helper Function 2: Add an ASSISTANT message to the conversation
# ---------------------------------------------------------------------------
# After the API responds, we store that response as an "assistant" message.
# This is what lets the API "remember" what it said earlier.
def add_assistant_message(messages, text):
    """Append an assistant (AI) message to the conversation history."""
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)


# ---------------------------------------------------------------------------
# Helper Function 3: Send the FULL conversation to the API and get a response
# ---------------------------------------------------------------------------
# Key concept: we send the ENTIRE messages list every time, not just the latest.
# This is how stateless APIs achieve "memory" — you replay the whole conversation.
def chat(messages):
    """Send the full conversation history to the API and return the response text."""
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1000,
        messages=messages,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Helper Function 4: Save the full conversation to a formatted .txt file
# ---------------------------------------------------------------------------
# Each conversation gets its own file named with timestamp: 2026-05-11_22-30-45.txt
# This way you can review past conversations anytime
def save_conversation(messages):
    """Save the full conversation to a timestamped .txt file in logs/ folder."""
    # Create logs directory if it doesn't exist
    os.makedirs(LOGS_DIR, exist_ok=True)

    # Generate filename from current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"conversation_{timestamp}.txt"
    filepath = os.path.join(LOGS_DIR, filename)

    # Build the formatted text content
    separator = "=" * 70
    lines = []
    lines.append(separator)
    lines.append(f"  CONVERSATION LOG")
    lines.append(f"  Date:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Model:  {MODEL}")
    lines.append(f"  API:    ZAI (OpenAI-compatible)")
    lines.append(f"  Turns:  {len(messages) // 2}")
    lines.append(f"  Messages: {len(messages)}")
    lines.append(separator)
    lines.append("")

    # Write each message with clear role labels
    for i, msg in enumerate(messages):
        role = msg["role"].upper()

        # Visual distinction: USER has >>> prefix, ASSISTANT has empty
        if msg["role"] == "user":
            lines.append(f"--- Turn {(i // 2) + 1} ---")
            lines.append(f">>> USER:")
        else:
            lines.append(f"    ASSISTANT:")

        lines.append("")
        lines.append(msg["content"])
        lines.append("")
        lines.append("-" * 70)
        lines.append("")

    # Add a summary at the bottom showing what the API received each turn
    lines.append("")
    lines.append(separator)
    lines.append("  HOW MULTI-TURN WORKED (what was sent to the API each turn)")
    lines.append(separator)
    lines.append("")

    # Show the growing message list for each turn
    for turn in range(len(messages) // 2):
        start = 0
        end = (turn + 1) * 2
        lines.append(f"  Turn {turn + 1}: API received {end} messages:")
        for j in range(end):
            role_tag = messages[j]["role"].upper()
            preview = messages[j]["content"][:80]
            if len(messages[j]["content"]) > 80:
                preview += "..."
            lines.append(f"    [{j+1}] {role_tag}: {preview}")
        lines.append("")

    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


# ---------------------------------------------------------------------------
# Main Chatbot Loop
# ---------------------------------------------------------------------------
def main():
    # Start with an empty conversation — no history yet
    messages = []

    print("=" * 60)
    print("  Multi-Turn Chatbot (type 'quit' to exit)")
    print("  API: ZAI (OpenAI-compatible)")
    print("  Model:", MODEL)
    print("=" * 60)
    print()

    while True:
        # Step 1: Prompt the user for input
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        # Exit condition
        if user_input.strip().lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        # Skip empty input
        if not user_input.strip():
            continue

        # Step 2: Add the user's message to conversation history
        add_user_message(messages, user_input)

        # Step 3: Send the ENTIRE conversation history to the API
        #         (not just the latest message — ALL of them)
        answer = chat(messages)

        # Step 4: Add the assistant's response to history
        #         This is crucial — without this, the next turn won't
        #         know what the assistant already said
        add_assistant_message(messages, answer)

        # Step 5: Print the response
        print(f"\nAssistant: {answer}\n")

    # Save the conversation to a formatted .txt file
    if messages:
        saved_path = save_conversation(messages)
        print(f"\n  Conversation saved to: {saved_path}")
    else:
        print("\n  No messages to save.")


if __name__ == "__main__":
    main()
