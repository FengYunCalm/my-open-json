---
name: dispatching-parallel-agents
description: Use when two or more tasks are independent enough to investigate or execute in parallel without shared state or conflicting file edits.
---

# Dispatching Parallel Agents

## Overview

Parallel agents help when several problems are truly separate. The win comes from isolation and speed, not from throwing agents at loosely understood work.

## When to Use

Use this skill when:
- there are multiple independent failures or subproblems
- each task can be understood with its own context bundle
- parallel work will not collide on the same files or state

Do not use it when the tasks are tightly coupled or one root cause may explain them all.

## Workflow

1. Split the work into independent domains.
2. Give each agent a focused task with only the context it needs.
3. State the expected return format before dispatch.
4. Run the agents in parallel.
5. Review results together and integrate only the non-conflicting changes.

## Recommended Agent Return Format

Ask each agent to return:
- root cause or task outcome
- files changed or inspected
- verification performed
- remaining risks or blockers

## Example

If three unrelated test files fail for different reasons, dispatch one agent per file instead of one agent for all three.

## Red Flags

Avoid parallel dispatch when:
- two agents would edit the same file
- the tasks need a shared mental model of the system
- you have not yet proved the failures are independent
