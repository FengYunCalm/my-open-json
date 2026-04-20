---
name: project-init
description: Use when starting work in an unfamiliar project and you need a quick read on repo type, key files, tracking artifacts, and current status.
---

# Project Init

## Overview

This skill gives you a fast, trustworthy starting snapshot of a project. It is useful when you need context before planning or implementation, especially in a repo you have not touched recently.

## Mode Selection

Use **quick scan** when you only need repo type, framework, and key entry points.

Use **tracked-project scan** when the repo also uses files such as `PROGRESS.md`, `TODO.md`, or similar status artifacts.

## Workflow

1. Identify the repo type and dominant tech stack.
2. Read the highest-signal files first, such as `README`, config files, and project rules.
3. Read tracking files only if they actually exist.
4. Summarize current state without inventing missing structure.

## Output Format

```markdown
## Project Snapshot

**Project type:**
**Key technologies:**
**Important files:**
**Tracking artifacts found:**
**Current focus / status:**
**Open questions:**
```

## Notes

- Do not assume every project has progress logs.
- Do not create missing tracking files unless the user asks.
- Use this skill when context is missing, not as a ritual before every task.
