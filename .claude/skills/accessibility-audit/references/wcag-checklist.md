# WCAG 2.1 AA Success Criteria Checklist

# Quick reference for the most commonly violated WCAG 2.1 AA criteria.
# Use this when the user asks about specific rules or compliance requirements.

## Level A (Minimum)

### 1.1.1 Non-text Content (Level A)
- All `<img>` must have `alt` attribute
- Decorative images use `alt=""` with `role="presentation"`
- Complex images need long descriptions

### 1.3.1 Info and Relationships (Level A)
- Use semantic HTML (`<header>`, `<nav>`, `<main>`, `<footer>`)
- Form inputs must have associated `<label>` elements
- Data tables must use `<th>` with `scope` attributes
- Lists must use `<ul>`, `<ol>`, `<dl>` markup

### 1.4.1 Use of Color (Level A)
- Don't use color alone to convey information
- Error states need text/icons, not just red borders

### 2.1.1 Keyboard (Level A)
- All interactive elements must be keyboard operable
- No keyboard traps
- Custom widgets need keyboard event handlers

### 2.4.1 Bypass Blocks (Level A)
- Provide skip navigation link as first focusable element
- Example: `<a href="#main-content" class="skip-link">Skip to main content</a>`

### 2.4.2 Page Titled (Level A)
- Every page must have a descriptive `<title>`

### 3.3.1 Error Identification (Level A)
- Form errors must be clearly identified in text
- Error messages must be associated with the relevant field

## Level AA (Standard Target)

### 1.4.3 Contrast (Level AA)
- Normal text: minimum 4.5:1 contrast ratio
- Large text (18px+ bold or 24px+): minimum 3:1 ratio
- UI components and graphics: minimum 3:1 ratio

### 1.4.11 Non-text Contrast (Level AA)
- Buttons, form fields, focus indicators need 3:1 contrast against background

### 2.4.3 Focus Order (Level AA)
- Tab order must follow a logical sequence
- Use DOM order, not visual order

### 2.4.7 Focus Visible (Level AA)
- Every focusable element must have a visible focus indicator
- Never use `outline: none` without a replacement

### 3.1.2 Language of Parts (Level AA)
- Content in a different language needs `lang` attribute on the element
- Example: `<blockquote lang="fr">`

### 4.1.2 Name, Role, Value (Level AA)
- Custom widgets must expose correct ARIA roles
- Interactive elements must have accessible names
- State changes must be announced (aria-expanded, aria-checked)
