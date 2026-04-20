---
name: brainstorming
description: Use when a feature, behavior change, or design request is still ambiguous enough that scope, constraints, or implementation direction should be clarified before editing code.
---

# Brainstorming

## Overview

This skill turns a vague request into a decision the user can actually approve. The goal is not paperwork for its own sake. The goal is to avoid building the wrong thing, missing constraints, or locking into a weak design too early.

## Mode Selection

Use **light mode** when:
- the change is small
- there are only a few real unknowns
- a short written summary is enough

Use **full mode** when:
- the request spans multiple files or subsystems
- there are architectural tradeoffs
- failure modes, data flow, or UX direction still need deliberate choices

## Workflow

1. Read the minimum project context needed to understand the request.
2. Ask focused questions about purpose, constraints, and success criteria.
3. Offer 2 to 3 approaches when there is a meaningful tradeoff.
4. Recommend one approach and explain why.
5. Summarize the decision in a compact design note.
6. If implementation needs multiple concrete steps, hand off to `writing-plans`.
7. If the main deliverable is a formal proposal, spec, RFC, or decision document, hand off to `doc-coauthoring` instead of forcing everything into an implementation-plan shape.
8. If the clarified problem is specifically about designing or implementing an MCP server, hand off to `mcp-builder` once the direction is clear.

## Light-Mode Output

Use this when a brief design summary is enough:

```markdown
## Design Summary

**Goal:**
**Constraints:**
**Recommended approach:**
**Open questions:**
```

## Full-Mode Output

Use this when the request needs a fuller design pass:

```markdown
## Design Summary

**Problem:**
**Scope:**
**Constraints:**
**Options considered:**
**Recommended approach:**
**Risks / edge cases:**
**Verification approach:**
```

## Good Habits

- Keep questions sequential and focused.
- Scale the process to the task. A small request may only need a few paragraphs.
- Explain tradeoffs in plain language.
- Capture the reasoning in a place that matches the repo's existing documentation habits.

## Red Flags

Pause and clarify before implementation when:
- the user request could reasonably mean more than one thing
- success criteria are still fuzzy
- you are making architectural decisions on the user's behalf
- the request mixes several independent features that should be split

## Visual Companion

If the discussion is about layouts, diagrams, or visual structure, offer a visual companion once. Do that only when seeing the design would help more than reading about it.

## Example

User: "Add a real-time collaboration panel."

Good response pattern:
1. Clarify whether they need presence, live cursors, or shared editing.
2. Compare a lightweight presence panel with a full collaborative editor.
3. Recommend the smallest option that fits the user's actual goal.
