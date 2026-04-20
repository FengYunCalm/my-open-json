---
name: team-core
description: Use when the user wants to start or manage a relay-backed workflow team from the current session and relay team tools are available.
license: MIT
compatibility: opencode
metadata:
  audience: operators
  workflow: team-runtime
---

# Team Core Skill

## Overview

This skill starts or manages a relay-backed workflow team while keeping the current session as manager. It is for real team orchestration, not generic planning.

## Mode Selection

Use **start mode** when the user wants a new workflow team for a concrete task.

Use **status mode** when the team already exists and the user wants readiness, blockers, or progress.

Use **intervention mode** when the manager needs to redirect or unblock workers.

## Workflow

1. Determine whether the request is start, status, or intervention.
2. Call the matching relay team tool.
3. Report the actual room, run, and worker state.
4. Keep all follow-up coordination on the relay tool surface.

## Output Format

```markdown
## Team Status

**Mode:** start | status | intervention
**Room code:**
**Run ID:**
**Workers:**
**Current blockers or next steps:**
```

## Good Habits

- Keep the current session as manager.
- Do not fabricate room codes, aliases, or worker states.
- Do not fall back to compatibility-path tools unless the user explicitly needs that path.
