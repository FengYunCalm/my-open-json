---
name: finishing-a-development-branch
description: Use when implementation on a branch is done and the next step is deciding whether to merge, open a PR, keep the branch, or discard it.
---

# Finishing a Development Branch

## Overview

This skill helps close out branch work in a predictable way. The key is to verify the current state first, then present clear next-step options without hiding destructive actions.

## When to Use

Use when implementation on a branch is effectively done and the next question is whether to merge, open a PR, keep the branch, or discard it.

## Boundaries

- Do not use while feature work is still in progress.
- Do not use for ordinary commit or PR creation if branch-completion decisions are not the main task.

## Workflow

1. Run the relevant verification first.
2. Identify the likely base branch.
3. Present the default next-step options.
4. Execute the user's chosen path.
5. Clean up the worktree only when that choice actually calls for cleanup.

## Default Options

Present these as the normal options unless project context suggests otherwise:
1. merge locally
2. push and create a pull request
3. keep the branch as-is
4. discard the branch and its work

## Safety Rules

- Never offer a "done" message before fresh verification.
- Treat discard as destructive and require explicit confirmation.
- Clean up a worktree only when the chosen path makes that safe.
- If a PR path should keep the worktree available for follow-up, say so.

## Output Format

```markdown
## Branch Completion Options

**Current branch:**
**Likely base:**
**Verification run:**
**Suggested next step:**
**Available options:**
```

## Example

```markdown
## Branch Completion Options

**Current branch:** `feature/audit-filters`
**Likely base:** `main`
**Verification run:** `npm test -- audit`
**Suggested next step:** create a pull request
**Available options:** merge locally / create PR / keep branch / discard
```
