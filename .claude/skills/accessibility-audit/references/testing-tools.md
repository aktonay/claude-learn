# Accessibility Testing Tools

# Recommended tools for automated and manual accessibility testing.
# Use this when the user asks about tooling or wants to set up testing.

## Automated Testing

### Lighthouse (built into Chrome DevTools)
# Runs audits for accessibility, performance, SEO
# Scores 0-100; target 90+ for accessibility
# CLI: npx lighthouse http://localhost:3000 --only-categories=accessibility

### axe-core (by Deque)
# Industry-standard accessibility testing engine
# Integrates with Jest, Vitest, Cypress, Playwright
# Install: npm install @axe-core/playwright
# Example:
#   import { AxeBuilder } from '@axe-core/playwright';
#   const results = await new AxeBuilder({ page }).analyze();

### eslint-plugin-jsx-a11y
# Catches accessibility issues in JSX at lint time
# Install: npm install eslint-plugin-jsx-a11y
# Catches: missing alt, missing labels, click-without-key, etc.

## Manual Testing

### Screen Readers
# - macOS: VoiceOver (built-in, Cmd+F5 to toggle)
# - Windows: NVDA (free, https://www.nvaccess.org/)
# - Mobile: TalkBack (Android), VoiceOver (iOS)

### Keyboard Testing
# Tab through the entire page — can you reach every interactive element?
# Can you activate buttons/links with Enter/Space?
# Can you close modals with Escape?
# Is the focus order logical?

### Browser Extensions
# - axe DevTools (Chrome/Firefox) — one-click audit of current page
# - Accessibility Insights (Microsoft) — guided manual testing

## CI/CD Integration

# Run axe-core in your test suite as a gate:
# - Block PRs that introduce new HIGH severity issues
# - Track accessibility score over time in CI reports
# - Use Lighthouse CI for periodic full-page audits
