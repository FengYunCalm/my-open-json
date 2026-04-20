---
name: using-git-worktrees
description: Use when branch work needs an isolated workspace so you can explore or implement changes without disturbing the current worktree.
---

# Using Git Worktrees

## Overview

Git worktrees are useful when isolation matters: you can keep your current workspace stable while opening a second branch in a separate directory.

## When to Use

Use a worktree when:
- the current workspace is busy or dirty
- you need to compare branches side by side
- the task is risky enough that isolation improves safety

You usually do not need one for tiny, local, low-risk edits.

## Workflow

1. Choose a worktree location using the repo's existing convention if one exists.
2. If the worktree will live inside the repo, verify that the directory is ignored.
3. Create the worktree and branch.
4. Run only the setup steps the project actually needs.
5. Check a clean baseline before major implementation work when that baseline matters.

## Safety Notes

- If the intended in-repo worktree path is not ignored, stop and fix that first instead of creating a noisy worktree.
- Do not assume the user wants a project-local worktree if the repo already prefers a global one.
- Do not auto-commit unrelated `.gitignore` changes without user approval.

## Output Format

```markdown
## Worktree Ready

**Path:**
**Branch:**
**Setup performed:**
**Baseline verification:**
**Notes / blockers:**
```

## Common Checks

- existing `.worktrees/` or `worktrees/` directory
- repo documentation or project rules for preferred location
- project-local ignore status when applicable

## Related Skills

- `executing-plans`
- `finishing-a-development-branch`
