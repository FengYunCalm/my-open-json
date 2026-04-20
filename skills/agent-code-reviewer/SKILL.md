---
name: agent-code-reviewer
description: Use when reviewing code or diffs for bugs, regressions, security issues, performance risks, or project-standard violations, including requests like /review, /check, 审查代码, 代码检查, or 代码规范检查.
---

# Agent Code Reviewer

## Overview

This skill is the unified entry point for code review and standards checking. It is most useful when the user wants findings, risks, and missing tests surfaced in a structured way.

## Mode Selection

Use **full review** when the user wants a normal review of correctness, security, performance, and tests.

Use **standards-focused review** when the main concern is style, structure, conventions, or project rules.

Use **risk-focused review** when the main concern is bugs, regressions, or security.

## Workflow

1. Read the changed files and enough local context.
2. Identify user-visible behavior and risky paths.
3. Review for correctness, security, standards, performance, architecture, and tests.
4. Report findings in severity order with file and line references.

## Output Format

```markdown
## Findings

1. **High** `path/to/file:123`
   Problem summary.
   Why it matters.
   Recommended fix.

## Open Questions
- ...

## Residual Risks
- ...

## Summary
- ...
```

## Notes

- Keep standards findings in the same report instead of switching to a second review skill.
- If no findings are present, say so explicitly and note any verification gaps.
