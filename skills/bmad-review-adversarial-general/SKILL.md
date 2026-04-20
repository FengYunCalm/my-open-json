---
name: bmad-review-adversarial-general
description: Use when reviewing a diff, spec, plan, or document with an intentionally skeptical lens focused on hidden risks, weak assumptions, and missing safeguards.
---

# Adversarial Review

## Overview

This skill reviews with healthy skepticism. The point is to surface the problems that a friendly or surface-level review may miss, especially missing assumptions, hidden risks, and weak reasoning.

## Mode Selection

Use **diff mode** for code changes.

Use **spec mode** for requirements, plans, or designs.

Use **document mode** for prose artifacts that may hide risky assumptions.

## Workflow

1. Identify the artifact type and scope.
2. Look for missing assumptions, unsafe defaults, weak reasoning, and likely regressions.
3. Report only material findings.
4. If nothing serious is found, say so and name the remaining blind spots.

## Output Format

```markdown
## Findings

1. **Severity:**
   **Location:**
   **Issue:**
   **Why it matters:**
   **Suggested next check:**
```

## Notes

- Do not invent findings to satisfy a quota.
- A clean review is allowed if the artifact truly holds up.
