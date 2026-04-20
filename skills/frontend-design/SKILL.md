---
name: frontend-design
description: Use when building or restyling a web page or UI component where visual direction, polish, and production-grade frontend implementation matter more than generic defaults.
license: Complete terms in LICENSE.txt
---

# Frontend Design

## Overview

This skill helps produce frontend work that feels intentionally designed rather than template-generated. The key is to choose a clear visual direction first, then implement it with enough restraint or richness to make the direction believable.

Use this skill for actual UI implementation. If the problem is mainly React component API design, use `vercel-composition-patterns`. If the problem is mainly performance, rendering, hydration, or bundle behavior, use `vercel-react-best-practices`.

## Mode Selection

Use **new page mode** for a fresh page, landing page, dashboard, or flow.

Use **existing-system mode** when the repo already has a design language that must be respected.

Use **component polish mode** when the task is focused on a smaller UI surface that still needs stronger visual character.

## Workflow

1. Identify audience, purpose, constraints, and technical stack.
2. Choose a strong aesthetic direction.
3. Define the visual system: typography, color, spacing, motion, and background treatment.
4. Implement the UI so the code supports that direction cleanly.
5. Verify the result still works on desktop and mobile.

## Design Guidance

- Prefer a memorable direction over safe sameness.
- Use typography and spacing as primary design tools, not only color.
- Match motion complexity to the concept; not every screen needs heavy animation.
- If the project already has a strong design system, adapt to it instead of replacing it.
- Avoid generic AI aesthetics such as timid palettes, overused fonts, predictable centered layouts, and interchangeable component patterns.
- Choose a bold conceptual direction and execute it precisely; intentional minimalism and intentional maximalism are both valid.

## Output Format

```markdown
## Frontend Design Direction

**Mode:**
**Aesthetic direction:**
**Key visual decisions:**
**Implementation notes:**
**Responsive / accessibility notes:**
```

## Examples

**Example 1:** A marketing landing page may justify a bold visual concept and strong motion moments.

**Example 2:** An internal dashboard may still be distinctive, but usually needs more restraint and denser information handling.

## Related Skills

- Use `webapp-testing` after implementation when the user wants browser-level verification of an interactive UI.
- Use `vercel-composition-patterns` for component API and composition problems.
- Use `vercel-react-best-practices` for React and Next.js performance or rendering bottlenecks.
