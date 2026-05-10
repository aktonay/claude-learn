#!/bin/bash
# ============================================================
# SKILL VALIDATOR
# Scans .claude/skills/ for structural problems.
# Run this FIRST before debugging anything — catches 90% of issues.
#
# Usage: bash scripts/validate-skills.sh [path-to-skills-dir]
# Default path: .claude/skills/ (relative to current directory)
# ============================================================

# --- Configuration ---
# Allow custom skills path via argument, default to .claude/skills/
SKILLS_DIR="${1:-.claude/skills}"
ERRORS=0
WARNINGS=0
PASSED=0

echo "============================================================"
echo "  SKILL VALIDATOR — Structural Checks"
echo "  Scanning: $SKILLS_DIR"
echo "============================================================"
echo ""

# --- Check: Does the skills directory exist? ---
if [ ! -d "$SKILLS_DIR" ]; then
    echo "[FAIL] Skills directory not found: $SKILLS_DIR"
    echo "       Create it with: mkdir -p $SKILLS_DIR"
    echo ""
    echo "============================================================"
    echo "  RESULT: BLOCKED — no skills directory"
    echo "============================================================"
    exit 1
fi

# --- Iterate over each skill directory ---
# Each skill should be in .claude/skills/<skill-name>/SKILL.md
for SKILL_PATH in "$SKILLS_DIR"/*/; do

    # Get the skill name from the directory name
    SKILL_NAME=$(basename "$SKILL_PATH")
    echo "--- Validating: $SKILL_NAME ---"

    # -------------------------------------------------------
    # CHECK 1: SKILL.md file exists and is named correctly
    # The file MUST be named exactly "SKILL.md" — not skill.md, Skills.md, etc.
    # -------------------------------------------------------
    if [ ! -f "$SKILL_PATH/SKILL.md" ]; then
        echo "  [FAIL] SKILL.md not found at: $SKILL_PATH/SKILL.md"
        echo "         File must be named exactly 'SKILL.md' (uppercase SKILL, lowercase md)"
        echo "         Check for: skill.md, Skills.md, SKILL.MD (all wrong)"
        ERRORS=$((ERRORS + 1))
        echo ""
        continue
    fi
    PASSED=$((PASSED + 1))

    # -------------------------------------------------------
    # CHECK 2: Frontmatter exists (dashed boundaries)
    # SKILL.md must have --- at the start and after metadata
    # -------------------------------------------------------
    FIRST_LINE=$(head -n 1 "$SKILL_PATH/SKILL.md")
    if [ "$FIRST_LINE" != "---" ]; then
        echo "  [FAIL] SKILL.md must start with '---' frontmatter delimiter"
        ERRORS=$((ERRORS + 1))
    else
        PASSED=$((PASSED + 1))
    fi

    # -------------------------------------------------------
    # CHECK 3: Required frontmatter fields (name, description)
    # These are the two mandatory fields — skill won't load without them
    # -------------------------------------------------------
    # Extract the frontmatter block (everything between the two --- lines)
    FRONTMATTER=$(sed -n '/^---$/,/^---$/p' "$SKILL_PATH/SKILL.md" | head -n -1 | tail -n +2)

    # Check for 'name' field
    NAME_FOUND=$(echo "$FRONTMATTER" | grep -c "^name:")
    if [ "$NAME_FOUND" -eq 0 ]; then
        echo "  [FAIL] Missing required field: 'name' in frontmatter"
        ERRORS=$((ERRORS + 1))
    else
        # Validate name format: lowercase letters, numbers, hyphens only, max 64 chars
        NAME_VALUE=$(echo "$FRONTMATTER" | grep "^name:" | sed 's/^name: *//')
        NAME_LEN=${#NAME_VALUE}
        if [ "$NAME_LEN" -gt 64 ]; then
            echo "  [FAIL] 'name' exceeds 64 characters (currently $NAME_LEN chars)"
            ERRORS=$((ERRORS + 1))
        elif echo "$NAME_VALUE" | grep -qE '[A-Z_ ]'; then
            echo "  [FAIL] 'name' must be lowercase with hyphens only (no uppercase, spaces, underscores): '$NAME_VALUE'"
            ERRORS=$((ERRORS + 1))
        else
            PASSED=$((PASSED + 1))
        fi
    fi

    # Check for 'description' field
    DESC_FOUND=$(echo "$FRONTMATTER" | grep -c "^description:")
    if [ "$DESC_FOUND" -eq 0 ]; then
        echo "  [FAIL] Missing required field: 'description' in frontmatter"
        ERRORS=$((ERRORS + 1))
    else
        # Validate description length: max 1024 characters
        DESC_VALUE=$(echo "$FRONTMATTER" | grep "^description:" | sed 's/^description: *//')
        DESC_LEN=${#DESC_VALUE}
        if [ "$DESC_LEN" -gt 1024 ]; then
            echo "  [FAIL] 'description' exceeds 1024 characters (currently $DESC_LEN chars)"
            ERRORS=$((ERRORS + 1))
        elif [ "$DESC_LEN" -lt 20 ]; then
            echo "  [WARN] 'description' is very short ($DESC_LEN chars) — may not trigger reliably"
            echo "         Add trigger phrases like 'Use when the user asks about X, Y, or Z'"
            WARNINGS=$((WARNINGS + 1))
        else
            PASSED=$((PASSED + 1))
        fi
    fi

    # -------------------------------------------------------
    # CHECK 4: Directory name matches skill name
    # Mismatches cause confusion and potential loading issues
    # -------------------------------------------------------
    if [ "$NAME_FOUND" -gt 0 ]; then
        NAME_VALUE=$(echo "$FRONTMATTER" | grep "^name:" | sed 's/^name: *//')
        if [ "$NAME_VALUE" != "$SKILL_NAME" ]; then
            echo "  [WARN] Directory name '$SKILL_NAME' doesn't match skill name '$NAME_VALUE'"
            echo "         This won't break anything but is a best practice"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi

    # -------------------------------------------------------
    # CHECK 5: SKILL.md file size — keep under 500 lines
    # Large files waste context tokens when loaded
    # -------------------------------------------------------
    LINE_COUNT=$(wc -l < "$SKILL_PATH/SKILL.md")
    if [ "$LINE_COUNT" -gt 500 ]; then
        echo "  [WARN] SKILL.md is $LINE_COUNT lines — recommended max is 500"
        echo "         Move detailed content to references/ directory (progressive disclosure)"
        WARNINGS=$((WARNINGS + 1))
    else
        PASSED=$((PASSED + 1))
    fi

    # -------------------------------------------------------
    # CHECK 6: Scripts have execute permission
    # Scripts without +x will fail when Claude tries to run them
    # -------------------------------------------------------
    if [ -d "$SKILL_PATH/scripts" ]; then
        for SCRIPT in "$SKILL_PATH/scripts"/*; do
            if [ -f "$SCRIPT" ]; then
                if [ ! -x "$SCRIPT" ]; then
                    echo "  [WARN] Script not executable: $(basename "$SCRIPT")"
                    echo "         Fix: chmod +x $SCRIPT"
                    WARNINGS=$((WARNINGS + 1))
                fi
            fi
        done
    fi

    # -------------------------------------------------------
    # CHECK 7: Description quality — does it answer WHAT and WHEN?
    # Poor descriptions are the #1 cause of skills not triggering
    # -------------------------------------------------------
    if [ "$DESC_FOUND" -gt 0 ]; then
        DESC_VALUE=$(echo "$FRONTMATTER" | grep "^description:" | sed 's/^description: *//')
        # Check if description mentions when to use the skill
        if ! echo "$DESC_VALUE" | grep -qiE 'use when|triggers? on|activate|for when|useful for'; then
            echo "  [WARN] Description doesn't include trigger phrases (when to use)"
            echo "         Add: 'Use when the user asks about...'"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi

    echo "  [OK] $SKILL_NAME passed basic validation"
    echo ""
done

# --- Final Summary ---
echo "============================================================"
echo "  VALIDATION COMPLETE"
echo "  Passed: $PASSED  |  Warnings: $WARNINGS  |  Errors: $ERRORS"
echo "============================================================"

# Exit with error code if any errors found
if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo "  Fix ERRORS first — these will prevent the skill from loading."
    echo "  WARNINGS are best practices — fix when possible."
    exit 1
else
    if [ "$WARNINGS" -gt 0 ]; then
        echo ""
        echo "  No blocking errors, but review warnings for best results."
    fi
    exit 0
fi
