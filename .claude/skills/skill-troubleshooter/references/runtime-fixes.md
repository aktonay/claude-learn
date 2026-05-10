# Runtime Fix Guide
# Fixes for: Skill loads successfully but fails during execution.

## Problem: Script Permission Denied

# Scripts referenced in SKILL.md need execute permission.
# Claude can't run them without chmod +x.

### Fix: Make Scripts Executable

# Check permissions:
ls -la .claude/skills/<skill-name>/scripts/

# Fix all scripts at once:
chmod +x .claude/skills/<skill-name>/scripts/*.sh

# Verify:
ls -la .claude/skills/<skill-name>/scripts/
# Should show: -rwxr-xr-x (executable)

## Problem: Path Separator Issues (Windows)

# On Windows, backslashes in paths cause problems in bash scripts.
# Always use forward slashes — they work on ALL platforms.

### Fix: Use Forward Slashes Everywhere

# BAD — backslashes (breaks on bash):
# Run `scripts\detect-stack.sh`

# GOOD — forward slashes (works everywhere):
# Run `scripts/detect-stack.sh`

# Also check any hardcoded paths in your scripts:
# BAD:  DIR="skills\\my-skill\\scripts"
# GOOD: DIR="skills/my-skill/scripts"

## Problem: Missing Dependencies

# Skill scripts that use external tools (jq, curl, python, etc.)
# will fail if the dependency isn't installed.

### Fix: Document and Check Dependencies

# Add dependency info to your SKILL.md so Claude knows what's needed:
# Dependencies: jq (for JSON parsing), curl (for API calls)

# Check if a dependency exists before using it:
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is required but not installed"
    echo "Install with: brew install jq (macOS) or apt install jq (Linux)"
    exit 1
fi

## Problem: Script Uses Wrong Working Directory

# When Claude runs a script, the working directory might not be
# what you expect — it's usually the project root, not the skill directory.

### Fix: Use Absolute Paths or Detect Skill Location

# Option 1: Navigate to script directory first
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Option 2: Reference files relative to script location
REFERENCES="$SCRIPT_DIR/../references/file.md"

## Problem: Frontmatter YAML Syntax Errors

# Special characters in frontmatter values can break YAML parsing.
# Colons, quotes, and brackets are the usual suspects.

### Fix: Quote Frontmatter Values

# BAD — unquoted string with special characters:
# description: Use this for "reviewing" code: bugs, style & more.

# GOOD — wrapped in quotes:
# description: "Use this for reviewing code: bugs, style, and more."

## Problem: Skill Content Too Large

# Very large SKILL.md files can consume too much context.
# Claude might truncate or struggle with extremely long skill content.

### Fix: Use Progressive Disclosure

# Keep SKILL.md under 500 lines.
# Move detailed content to references/ files.
# Load them only when needed with explicit instructions:
# "If the user asks about X, read references/x-guide.md"
