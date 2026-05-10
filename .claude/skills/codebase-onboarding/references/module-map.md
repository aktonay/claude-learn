# Module Map

## Where to Add Things

| What you're adding        | Where to put it                  |
|---------------------------|----------------------------------|
| New UI component          | `src/components/`                |
| New page/route            | `src/pages/` or `src/routes/`   |
| New API endpoint          | `src/api/`                       |
| New utility function      | `src/utils/`                     |
| New test                  | Mirror the source path in `tests/` |
| New configuration         | `config/`                        |
| New shared type/interface | `src/types/`                     |

## Module Dependencies

- Components depend on utils and types — never on API directly
- API modules depend on types only
- Pages depend on components and API modules
