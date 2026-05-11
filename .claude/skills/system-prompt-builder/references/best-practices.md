# System Prompt Best Practices
# Guidelines for writing effective system prompts.

## Rule 1: Be Specific About Role

# BAD: "You are helpful."
# GOOD: "You are a senior Python engineer who writes clean, idiomatic code."

# The more specific the role, the more consistent the behavior.

## Rule 2: Define WHAT to Do Before What NOT to Do

# Start with positive instructions (what the AI should do),
# then add constraints (what it shouldn't do).

# BAD: "Don't give long answers. Don't use jargon."
# GOOD:
#   "Respond in 2-3 sentences maximum. Use plain language a beginner can understand."

## Rule 3: Use the 4-Dimension Framework

# Every system prompt should cover:
# 1. ROLE — who is the AI? (engineer, tutor, reviewer, writer)
# 2. BEHAVIOR — what should it always do?
# 3. CONSTRAINTS — what should it never do?
# 4. STYLE — how should responses be formatted?

# Missing any dimension leads to inconsistent behavior.

## Rule 4: Keep It Under 500 Words

# System prompts consume tokens on EVERY request.
# Longer prompts = higher cost and slower responses.
# Keep it focused — if it's getting long, split into multiple prompts.

## Rule 5: Test With Edge Cases

# After writing a prompt, test with:
# - A question the prompt SHOULD handle well
# - A question that TEMPTS the AI to break the rules
# - A question OUTSIDE the prompt's scope (see how it handles off-topic)

## Rule 6: Iterate Based on Results

# If the AI:
# - Gives answers too directly → add "never give direct answers" to constraints
# - Is too verbose → add "respond in under N sentences" to style
# - Goes off-topic → add "only discuss topics related to X" to constraints
# - Uses wrong format → add explicit format example to style

## Rule 7: Store Prompts in Files, Not Code

# Hardcoding prompts in code makes them hard to update.
# Store in .claude/system-prompts/<project>.md files:
# - Version controlled with git
# - Easy for non-developers to review and edit
# - Can be loaded at runtime from the file system

## Common Mistakes

# 1. Too vague: "Be helpful" — doesn't change behavior
# 2. Too long: 1000+ word prompts — wastes tokens, confuses the AI
# 3. Contradictory: "Be concise" + "Explain everything" — AI can't follow both
# 4. Missing constraints: only says what to do, not what NOT to do
# 5. No style guidance: AI picks random format each time
