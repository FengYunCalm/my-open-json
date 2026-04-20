---
name: refactor
description: Use when existing code needs maintainability improvements without intentionally changing user-visible behavior, such as extracting logic, simplifying structure, or tightening types.
license: MIT
---

# Refactor

## Overview

Refactoring improves structure without changing intended behavior. The goal is clarity and maintainability, not a hidden rewrite.

## Mode Selection

Use **rename mode** when names hide intent.

Use **extract mode** when one block of logic deserves its own function, object, or module.

Use **decompose mode** when a file or class owns too many responsibilities.

Use **type-safety mode** when domain meaning or API contracts are too loose.

Use **structural split mode** when related changes keep colliding because boundaries are weak.

## Workflow

1. Identify the smell or maintenance pain.
2. Confirm that the task is still behavior-preserving.
3. Pick the smallest refactor mode that addresses the issue.
4. Make focused changes and verify after each meaningful step.
5. Stop before the refactor turns into an unrequested redesign.

## Output Format

```markdown
## Refactor Summary

**Problem addressed:**
**Refactor mode:**
**Main files:**
**Behavior-preserving check:**
**Verification:**
```

## References

- `references/code-smells.md`
- `references/refactor-patterns.md`

## Example

If a handler both validates input, queries the database, formats output, and sends notifications, start with `extract mode` or `decompose mode` instead of redesigning the entire subsystem.
