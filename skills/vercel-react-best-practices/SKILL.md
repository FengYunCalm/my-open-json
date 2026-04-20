---
name: vercel-react-best-practices
description: Use when React or Next.js work involves performance, rendering, data fetching, bundle size, hydration, or server-client boundary decisions.
license: MIT
metadata:
  author: vercel
  version: "1.0.0"
---

# Vercel React Best Practices

## Overview

This skill helps choose the right React or Next.js optimization rule based on the actual bottleneck. It is most useful when the task is about speed, rendering behavior, or data-flow efficiency rather than generic component design.

## Symptom Routing

If the problem is **waterfalls or slow data loading**, start with `async-` or `server-` rules.

If the problem is **bundle size**, start with `bundle-` rules.

If the problem is **rerenders or effect churn**, start with `rerender-` rules.

If the problem is **hydration, SVG, or long-list rendering**, start with `rendering-` rules.

If the problem is **general hot-path JavaScript cost**, start with `js-` rules.

## Workflow

1. Identify the performance symptom, not just the file type.
2. Pick the matching rule group.
3. Read only the specific rule files needed.
4. Apply the recommendation and re-check the tradeoff it targets.

## Rule Groups

- `async-` and `server-` for fetch ordering and server efficiency
- `bundle-` for bundle weight and lazy loading
- `client-` for client data fetching and browser-side behavior
- `rerender-` for state and effect churn
- `rendering-` for hydration and render-path costs
- `js-` for lower-level hot-path optimizations
- `advanced-` for narrower edge cases

## Output Format

```markdown
## React / Next Optimization Recommendation

**Observed symptom:**
**Rule group used:**
**Recommended change:**
**Expected benefit:**
**Tradeoff / follow-up check:**
```

## Notes

- Use only for React or Next.js work.
- Prefer the smallest rule group that matches the symptom.
