---
name: executing-plans
description: Use when you have a written implementation plan and need to execute it task-by-task, either inline or with subagents.
---

# Executing Plans

## Local Integration Note

- This skill assumes a written plan already exists.
- In this environment, `TodoWrite` maps to `todowrite`, and plan files should use repo-local docs paths instead of assuming `docs/superpowers/`.
- If the plan exists only in chat, save it to a project-local file before execution or ask the user where it should live.

## Overview

Execute an existing implementation plan after reviewing it critically. This skill supports two modes:

- **Inline mode**: execute tasks directly in the current session.
- **Subagent mode**: dispatch a fresh implementer per task, then review for spec compliance and code quality before moving on.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## Mode Selection

Use **inline mode** when:
- tasks are tightly coupled
- you need to stay hands-on in one session
- subagents are unavailable

Use **subagent mode** when:
- tasks are mostly independent
- you want stronger isolation and review loops
- the session has subagent support

If subagent mode is unavailable, fall back to inline mode instead of stopping.

## The Process

### Step 1: Load and Review Plan
1. Read the saved plan file once.
2. Review critically for gaps, contradictions, missing file paths, or unclear verification steps.
3. If concerns exist, raise them with your human partner before starting.
4. If the plan is usable, create `TodoWrite` items for its tasks.

### Step 2: Execute Tasks

For each task, mark it `in_progress`, finish it fully, then mark it `completed`.

#### Inline Mode
1. Follow each plan step exactly.
2. Run the listed verifications.
3. Stop and ask if the plan is blocked by missing context, missing dependencies, or repeated failures.

#### Subagent Mode
1. Extract the full task text plus only the context needed for that task.
2. Dispatch the implementer using `./implementer-prompt.md`.
3. If the implementer asks questions, answer them before work continues.
4. After implementation, dispatch `./spec-reviewer-prompt.md`.
5. Fix every spec gap before code quality review starts.
6. Dispatch `./code-quality-reviewer-prompt.md`.
7. Fix every quality issue, then re-review until approved.
8. Only then mark the task complete.

### Step 3: Complete Development

After all tasks are complete and verified:
- announce: "I'm using the finishing-a-development-branch skill to complete this work."
- use `finishing-a-development-branch`
- follow that skill to verify tests, present options, and execute the chosen path

## When to Stop and Ask for Help

Stop immediately when:
- the plan has critical gaps
- a task is blocked by missing dependency or missing context
- verification fails repeatedly
- the requested work would start from `main` or `master` without explicit consent

Ask for clarification instead of guessing.

## Red Flags

Never:
- skip plan review
- skip verification
- start on `main` or `master` without explicit consent
- let subagent code review begin before spec compliance review
- move to the next task with open review findings
- make a subagent reread the whole plan when you can provide the exact task text

## Supporting Prompts

Subagent mode uses:
- `./implementer-prompt.md`
- `./spec-reviewer-prompt.md`
- `./code-quality-reviewer-prompt.md`

## Integration

This skill works with:
- `using-git-worktrees` - set up isolated workspace before starting
- `writing-plans` - creates the plan this skill executes
- `test-driven-development` - implement each task with failing tests first
- `finishing-a-development-branch` - complete development after all tasks
