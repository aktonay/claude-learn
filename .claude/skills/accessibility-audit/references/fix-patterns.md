# Accessibility Fix Patterns

# Copy-paste fix patterns for the most common issues found during audits.
# Use this when the user asks HOW to fix a specific accessibility problem.

## Missing Alt Text

# BAD: <img src="logo.png">
# GOOD:
<img src="logo.png" alt="Company logo">

# BAD: <img src="decorative-line.png">
# GOOD (decorative — hidden from screen readers):
<img src="decorative-line.png" alt="" role="presentation">

## Missing Form Labels

# BAD: <input type="email" placeholder="Email">
# GOOD — using explicit label:
<label for="email">Email address</label>
<input type="email" id="email">

# GOOD — using aria-label when visible label isn't possible:
<input type="search" aria-label="Search products">

## Empty or Vague Links

# BAD: <a href="/details">Click here</a>
# BAD: <a href="/details">Read more</a>
# GOOD:
<a href="/details">Read the full quarterly report</a>

## Missing Focus Styles

# BAD: removes focus indicator entirely
*:focus { outline: none; }

# GOOD — custom focus ring with sufficient contrast
*:focus-visible {
  outline: 2px solid #005fcc;
  outline-offset: 2px;
}

## Keyboard-Inaccessible Custom Widgets

# BAD: div acting as button with no keyboard support
<div onclick="handleClick()">Submit</div>

# GOOD — use native elements, or add keyboard + ARIA:
<div
  role="button"
  tabindex="0"
  onclick="handleClick()"
  onkeydown="if(event.key==='Enter')handleClick()"
>
  Submit
</div>

## Skip Navigation Link

# Add as the first element in <body>
<a href="#main-content" class="skip-link">Skip to main content</a>

# CSS — visible only on focus
.skip-link {
  position: absolute;
  left: -9999px;
  top: auto;
}
.skip-link:focus {
  position: static;
  left: 0;
}

## ARIA on Static Content

# BAD: unnecessary ARIA on elements that already have semantics
<div role="button" ...> — just use <button>
<div role="heading" aria-level="2"> — just use <h2>
<div role="list"><div role="listitem"> — just use <ul><li>

# Rule of thumb: if HTML has a semantic element for it, use the element instead of ARIA
