---
name: evomemory
description: Use when a task depends on prior decisions, stable project memory, or recording feedback into EvoMemory.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  category: memory
---

# EvoMemory

Use this skill when the request references prior decisions, preferences, project rules, or when a retrieved memory needs confirmation or correction.

## When to use
- The user asks what was decided earlier, what the project prefers, or what should be remembered.
- You need stable context from past sessions.
- A retrieved memory is useful, wrong, or stale and should be reinforced or corrected.

## Workflow
1. Use `evomemory_search_context` for historical context tied to the current task.
2. Use `evomemory_query_beliefs` for stable facts, `evomemory_query_genes` for project rules, and `evomemory_query_capsules` for grouped policy.
3. If a memory is clearly helpful, confirmed, or wrong, record feedback with `evomemory_record_feedback`.
   - `success` = strongly helpful
   - `confirm` = correct or useful
   - `reject` = not useful or misleading
   - `correct` = explicitly wrong and should be weakened
4. If you need to inspect prior feedback, use `evomemory_list_feedback`.
5. If the memory set needs consolidation, use `evomemory_run_revision` or `evomemory_run_maintenance` only when it meaningfully changes quality.

## Rules
- Keep retrieved memory small and task-relevant.
- Prefer evidence from current code or session over older memory when they conflict.
- Do not call memory tools for tiny chatter or purely local, self-contained questions.
- Never invent target ids; query the relevant belief/gene/capsule tool first.

## Quick cues
- “what did we decide earlier” → `evomemory_search_context`
- “remember this preference” → `evomemory_record_feedback`
- “is this memory still correct?” → `evomemory_query_beliefs` + `evomemory_record_feedback`
