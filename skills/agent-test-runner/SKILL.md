---
name: agent-test-runner
description: Use when the user wants tests discovered, run, or summarized, including targeted test runs, coverage checks, and lightweight performance-oriented test passes.
---

# Agent Test Runner

## Overview

This skill helps choose the right test scope, run the relevant commands, and explain the outcome clearly. It is for test execution and result reporting first, not for broad root-cause analysis across the system.

## Mode Selection

Use **run mode** when the goal is to execute a relevant test set.

Use **diagnose mode** when tests are already failing and the user wants the failure output summarized or narrowed to the most relevant failing scope.

Use **coverage mode** when the user explicitly wants coverage numbers or reports.

Use **performance mode** when the user wants timing or slow-test insight from a test run.

## Workflow

1. Detect the stack and test framework.
2. Choose the smallest command that matches the user's intent.
3. Prefer project-native or project-local entrypoints before global commands.
4. If the needed tool is missing, report the environment limitation clearly and name the next best runnable command or setup step.
5. Run the tests.
6. Summarize pass/fail status, key failures, and next action.
7. Add coverage or performance detail only when the chosen mode needs it.

## Command Selection Order

Prefer commands in this order:
1. repo-native scripts or documented test commands
2. project-local toolchains such as `uv run`, `.venv/bin/pytest`, `python -m pytest`, `npm test --`, `pnpm test`, `npx vitest`, or `npm exec jest`
3. bare global commands only when they are clearly available

This keeps test execution aligned with the repo instead of assuming the machine has the right tools globally installed.

If the failure now looks like a deeper product or cross-component bug, hand off to `systematic-debugging` rather than stretching this skill into full root-cause analysis.

For browser-level UI verification, screenshots, or Playwright-driven local webapp testing, hand off to `webapp-testing` instead of stretching this skill into end-to-end browser automation.

## Output Format

```markdown
## Test Result

**Mode:** run | diagnose | coverage | performance
**Command:**
**Scope:**
**Outcome:**
**Key failures or observations:**
**Next action:**
```

## Why Smallest-Scope First

Targeted runs shorten the feedback loop and make failure analysis cleaner. Run a broader suite only when the claim you need to prove is broader.

## Reference

Read `references/test-commands.md` for common test command patterns by stack.
