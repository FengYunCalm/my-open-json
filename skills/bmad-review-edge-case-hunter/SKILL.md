---
name: bmad-review-edge-case-hunter
description: Use when code, specs, or diffs need structured edge-case analysis focused only on missing handling for branches and boundary conditions.
---

# Edge Case Hunter Review

## Overview

This skill is a path-and-boundary review, not a general code-quality review. It focuses on what is not handled yet: missing guards, unbounded inputs, unchecked states, and branches that reach bad outcomes.

## Mode Selection

Use **diff mode** when reviewing a patch and you want analysis near the changed hunks.

Use **file mode** when the whole provided file is the scope.

Use **function mode** when one function or snippet is the unit of review.

## Workflow

1. Define the scope from the provided diff, file, or function.
2. Walk reachable branches and boundaries within that scope.
3. Keep only missing handling.
4. Output the findings as the required JSON array.

## Output Format

Return only this JSON structure:

```json
[
  {
    "location": "file:start-end",
    "trigger_condition": "short condition",
    "guard_snippet": "minimal closing guard",
    "potential_consequence": "short consequence"
  }
]
```

Use `[]` when nothing material is missing.

## Why This Narrow Scope Helps

Keeping the review limited to branches and boundary handling prevents the skill from drifting into general commentary. That makes the findings sharper and easier to act on.
