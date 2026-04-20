---
name: bmad-editorial-review-structure
description: Use when a document needs cuts, reordering, or simplification while preserving meaning, including requests to reorganize, trim, or improve document flow.
---

# Editorial Review - Structure

## Overview

This skill reviews how information is organized, not whether the underlying ideas are correct. Use it before copy-editing when the document may be in the wrong order, too long, or too repetitive.

## Mode Selection

Use **tutorial mode** for guides and walkthroughs.

Use **reference mode** for API docs, cheat sheets, or structured reference material.

Use **concept mode** for explanations, architecture docs, and overviews.

Use **pyramid mode** for proposals, reports, and decision documents where the conclusion should lead.

## Workflow

1. Identify the document's purpose and audience.
2. Choose the structural mode that best fits the document.
3. Map sections and look for burying, repetition, and misplaced detail.
4. Recommend cuts, moves, merges, or preserves in priority order.

## Output Format

```markdown
## Document Summary
- **Purpose:**
- **Audience:**
- **Structure mode:**

## Recommendations
1. **CUT / MOVE / MERGE / CONDENSE / PRESERVE** - section name
   - Rationale:
   - Impact:

## Summary
- Estimated reduction or tradeoff:
```

If there are no substantive structural issues, say so explicitly.

## Good Habits

- Preserve meaning while improving order and density.
- Treat comprehension aids as useful unless they are clearly wasteful.
- Recommend rather than silently rewriting structure.

## Related Skills

- Use `doc-coauthoring` when the user needs help creating the document itself rather than only restructuring an existing draft.
