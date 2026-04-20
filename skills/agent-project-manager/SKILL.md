---
name: agent-project-manager
description: Use when the user wants help tracking project status, todos, milestones, or progress reports in a repo that already uses project-tracking files.
---

# Agent Project Manager

## Overview

This skill helps maintain project state without inventing process that the repo does not already use. It works best when the project already has files such as `PROGRESS.md`, `TODO.md`, milestone docs, or other tracking artifacts.

## Mode Selection

Use **status mode** when the user wants a current snapshot.

Use **todo mode** when the user wants tasks added, updated, reprioritized, or marked done.

Use **report mode** when the user wants a structured progress summary for a period or milestone.

## Workflow

1. Identify which tracking files the repo already uses.
2. Read only the files relevant to the requested PM task.
3. Update status, todos, or reports in the repo's existing format.
4. Summarize what changed and what still needs attention.

## Output Format

```markdown
## Project Management Update

**Mode:** status | todo | report
**Files touched:**
**Key updates:**
**Open blockers:**
**Next recommended step:**
```

## Good Habits

- Respect the repo's existing tracking structure.
- Ask before creating tracking files that do not already exist.
- Prefer concise, factual updates over dashboard theater.

## Templates

For reusable report shapes, read `references/templates.md`.
