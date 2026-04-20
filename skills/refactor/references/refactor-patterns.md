# Refactor Patterns

## Common Operations

| Operation | Use when |
|----------|----------|
| Rename | names hide intent |
| Extract function | one block does a distinct job |
| Extract type/object | related values travel together |
| Split module | one file owns unrelated responsibilities |
| Add type/domain object | primitives hide domain meaning |
| Replace nested conditionals | guard clauses improve readability |

## Guidance

- Prefer the smallest change that improves readability or maintainability.
- Preserve behavior unless the user explicitly asked for a behavior change.
- Verify after each meaningful step.
