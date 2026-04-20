---
name: using-superpowers
description: Use when starting a session or switching to a new task and one or more installed skills may materially improve the workflow, accuracy, or output quality.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

# Using Superpowers

## Overview

Installed skills are valuable when they add a better workflow, sharper output format, or domain-specific judgment. The main mistake this skill prevents is charging into work with generic habits when a better local skill already exists.

## How to Use It

Before deep analysis or implementation:
1. Identify the user's real goal.
2. Ask whether a skill would materially help with planning, debugging, testing, review, design, research, or a domain-specific workflow.
3. If yes, load the smallest relevant set of skills early.
4. If no, continue normally instead of forcing a skill.

## Priority

Follow instructions in this order:
1. User instructions
2. Project rules such as `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md`
3. Loaded skills
4. Default assistant behavior

If project rules and a skill disagree, follow the project rules.

## When a Skill Is Worth Loading

Load a skill when at least one of these is true:
- the task matches a known workflow such as debugging, TDD, review, or planning
- the task is domain-specific enough that a skill has better rules than generic reasoning
- the output format matters and a skill defines a reliable structure
- the task is risky enough that a disciplined workflow reduces avoidable mistakes

## When Not to Force It

Skip extra skill loading when:
- the task is trivial and no skill adds material value
- a previously loaded skill already covers the current step
- the user explicitly wants a direct answer or a narrow one-step action

## Red Flags

These thoughts usually mean you should at least check for a relevant skill:

| Thought | Better response |
|---------|-----------------|
| "I'll just start and see" | Check whether a workflow skill would reduce rework first. |
| "This is probably too simple for a skill" | Simple requests can still benefit from the right structure. |
| "I already know this skill" | Reload only if needed, but don't rely on stale memory when the skill is central. |
| "I need more context before I decide" | Often the skill is what tells you how to gather that context. |

## Skill Order of Operations

When several skills could apply, prefer this order:
1. Process skills such as planning, debugging, or verification
2. Implementation or domain skills such as frontend, React, relay, or graph workflows

## Examples

**Example 1**

User: "This failing test is weird. Can you figure it out?"

Response pattern: load `systematic-debugging` before proposing fixes.

**Example 2**

User: "We need a new settings flow for this feature."

Response pattern: load `brainstorming` before implementation if requirements or design choices are still open.
