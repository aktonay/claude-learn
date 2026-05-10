#!/bin/bash
# ============================================================
# ACCESSIBILITY QUICK SCAN
# Scans frontend files for common a11y anti-patterns.
# Output is a plain text summary — only output enters context.
# ============================================================

echo "=== Accessibility Quick Scan ==="
echo ""

# Count total frontend files to scan
FILES=$(find . -type f \( -name "*.tsx" -o -name "*.jsx" -o -name "*.html" -o -name "*.vue" -o -name "*.svelte" \) 2>/dev/null | grep -v node_modules | grep -v dist)
TOTAL=$(echo "$FILES" | grep -c .)
echo "Files to scan: $TOTAL"
echo ""

# Check 1: Images without alt text
IMAGES=$(grep -rn '<img' $FILES 2>/dev/null | grep -v 'alt=' | wc -l)
echo "[HIGH] Images missing alt text: $IMAGES"

# Check 2: Inputs without labels
INPUTS=$(grep -rn '<input' $FILES 2>/dev/null | grep -v 'aria-label' | grep -v 'id=' | wc -l)
echo "[HIGH] Inputs without labels: $INPUTS"

# Check 3: Empty or vague links
LINKS=$(grep -rn '<a[^>]*> *</a>\|<a[^>]*>click here</a>\|<a[^>]*>read more</a>' $FILES 2>/dev/null | wc -l)
echo "[HIGH] Empty or vague links: $LINKS"

# Check 4: Click handlers without keyboard support
CLICK_NO_KEY=$(grep -rn 'onClick' $FILES 2>/dev/null | grep -v 'onKeyDown\|onKeyPress\|onKeyUp' | wc -l)
echo "[MEDIUM] Click handlers without keyboard events: $CLICK_NO_KEY"

# Check 5: outline:none without replacement focus style
OUTLINE=$(grep -rn 'outline.*none' $FILES 2>/dev/null | wc -l)
echo "[MEDIUM] outline:none without focus replacement: $OUTLINE"

echo ""
echo "=== Scan Complete ==="
