---
name: vercel-composition-patterns
description: Use when React or Next.js component APIs are getting awkward, especially with boolean prop proliferation, compound component needs, context design, or reusable component architecture.
license: MIT
metadata:
  author: vercel
  version: '1.0.0'
---

# React Composition Patterns

## Overview

This skill helps restructure React component APIs so they scale cleanly. The core idea is to replace hidden conditional behavior with clearer composition boundaries.

## Symptom Routing

If the problem is **too many boolean props**, start with:
- `rules/architecture-avoid-boolean-props.md`

If the problem is **shared state across composed pieces**, start with:
- `rules/architecture-compound-components.md`
- `rules/state-context-interface.md`

If the problem is **variant explosion**, start with:
- `rules/patterns-explicit-variants.md`

If the task is **React 19 specific**, check the `react19-` rules only when the codebase is actually on React 19.

## Workflow

1. Identify the API or architecture smell.
2. Pick the smallest relevant rule group.
3. Apply the rule to the real component shape in this repo.
4. Prefer explicit variants and composition over hidden mode switches.

## Rule Groups

- `architecture-` for component boundaries and boolean-prop problems
- `state-` for provider and context design
- `patterns-` for implementation choices such as variants or children composition
- `react19-` for React 19 specific guidance

## Output Format

```markdown
## Composition Recommendation

**Problem:**
**Rule group used:**
**Recommended API shape:**
**Tradeoffs:**
```

## Notes

- Use only for React or Next.js component architecture work.
- Read only the rule files needed for the current symptom.
