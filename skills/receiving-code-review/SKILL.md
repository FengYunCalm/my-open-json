---
name: receiving-code-review
description: Use when review feedback arrives and you need to evaluate it technically before changing code, especially when suggestions are unclear, incomplete, or possibly wrong for the current codebase.
---

# Receiving Code Review

## Overview

The point of review reception is to understand the feedback, verify it against the actual codebase, and then respond with action or reasoned pushback. The goal is technical clarity, not social performance.

## Mode Selection

Use **clarify mode** when feedback is ambiguous or underspecified.

Use **apply mode** when the feedback is clear and looks technically sound.

Use **pushback mode** when the suggestion may be wrong, incomplete, or in conflict with existing decisions.

## Workflow

1. Read all feedback without reacting to individual items too early.
2. Restate the technical change being requested.
3. Verify the suggestion against the codebase and constraints.
4. Choose clarify, apply, or pushback mode.
5. Implement one item at a time and verify each meaningful change.

## Response Templates

### Clarify Mode

```markdown
I understand items A and B. I need clarification on item C before I change anything because it affects implementation direction.
```

### Apply Mode

```markdown
Verified the issue in `path/to/file`. Updating it now and I will report the exact change after verification.
```

### Pushback Mode

```markdown
I checked this against the current codebase and I do not think the suggested change is correct here because ___. Would you like me to investigate an alternative?
```

## Good Habits

- Prefer technical acknowledgment over empty praise.
- Do not implement feedback you do not understand.
- Use code, tests, and existing project decisions as evidence when pushing back.

## GitHub Note

When replying to inline review comments on GitHub, reply in the thread rather than as a top-level PR comment.
