# Conventions

## Code Style

- Use consistent naming: `camelCase` for variables/functions, `PascalCase` for components/types
- One export per file (default export = file name)
- Group imports: external → internal → types

## File Organization

- Keep files under 300 lines
- Co-locate tests with source or mirror in `tests/`
- Use `index` files for public API of a module

## Git Conventions

- Branch naming: `feature/`, `fix/`, `chore/`
- Commit messages: present tense, imperative mood
- Squash merge preferred

## Testing

- Unit tests for utilities and pure functions
- Integration tests for API endpoints
- Component tests for UI with rendering
