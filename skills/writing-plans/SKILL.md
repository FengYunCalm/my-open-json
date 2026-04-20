---
name: writing-plans
description: Use when requirements are stable enough that the next step is a concrete implementation plan with files, tasks, and verification steps.
---

# Writing Plans

## Overview

This skill converts an approved direction into an execution plan. A good plan reduces guesswork, shows what files matter, and makes verification explicit before coding begins.

## Mode Selection

Use a **light plan** when:
- the task is small
- only a few files are involved
- one short checklist is enough

Use a **detailed plan** when:
- the work spans multiple components
- ordering matters
- there are meaningful risks, migrations, or test requirements

## What a Good Plan Includes

- the goal in one sentence
- the main files or directories involved
- task order
- verification commands or checks
- known risks, assumptions, or blockers

## Save Location

Unless the repo already has a planning convention or the user asked for a different location, save the plan to a repo-local path such as `docs/plans/YYYY-MM-DD-<topic>.md`.

If the user wants an in-chat-only draft, say that explicitly, because `executing-plans` works best when it can read a saved plan file.

## Recommended Template

```markdown
# [Feature Name] Implementation Plan

**Goal:**
**Scope:**
**Key files:**
**Verification:**

## Tasks
1. ...
2. ...
3. ...

## Risks / Open Questions
- ...
```

## Detailed Plan Additions

When the task is larger, also include:
- file-by-file responsibilities
- sequencing constraints
- migration or rollout notes
- targeted test coverage expectations

## Workflow

1. Re-read the approved design or clarified requirements.
2. Identify the smallest file set that can deliver the change.
3. Break the work into tasks that can be verified independently.
4. Write verification steps next to the tasks they prove.
5. Call out risky assumptions instead of hiding them.
6. Save the plan where the project expects plan artifacts. If the repo has no convention, use a repo-local fallback such as `docs/plans/YYYY-MM-DD-<topic>.md`.

## Handoff

After writing the plan, return the saved plan path. Execution can then continue through `executing-plans` in either:
- **subagent mode** for mostly independent tasks
- **inline mode** for tightly coupled or hands-on execution

## Example

```markdown
# Add Audit Log Filter Plan

**Goal:** Add server-side filtering for audit log entries by actor and date range.
**Scope:** API handler, query builder, UI filter form, tests.
**Key files:** `src/api/audit.ts`, `src/db/audit-query.ts`, `src/ui/AuditFilters.tsx`
**Verification:** targeted API test, UI test, smoke test in browser

## Tasks
1. Extend API input validation for actor and date range.
2. Update query builder to apply filters safely.
3. Add UI controls and wire them into the request.
4. Add regression tests for combined filters.
```
