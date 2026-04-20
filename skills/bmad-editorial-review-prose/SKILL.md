---
name: bmad-editorial-review-prose
description: Use when prose needs copy-editing for clarity, readability, or precision, including requests to polish wording, improve expression, or make text easier for humans or LLMs to understand.
---

# Editorial Review - Prose

## Overview

This skill reviews wording, not ideas. It is for passages that are basically correct in meaning but could communicate more clearly.

## Mode Selection

Use **human-reader mode** when the priority is readability, flow, and natural phrasing.

Use **llm-reader mode** when the priority is precision, explicit references, and consistent terminology.

## Workflow

1. Validate that the text is substantial enough to review.
2. Identify the audience and whether human-reader or llm-reader mode fits better.
3. Look only for issues that hurt comprehension.
4. Suggest the smallest fix that improves clarity.

## Output Format

| Original Text | Revised Text | Why the change helps |
|---------------|--------------|----------------------|
| ... | ... | ... |

If there are no material prose issues, output `No editorial issues identified`.

## Good Habits

- Preserve the author's intent and voice.
- Skip code blocks and structural markup.
- Do not rewrite for taste alone.
- When unsure, phrase the revision as a suggestion rather than a certainty.

## Related Skills

- Use `doc-coauthoring` when the user is still drafting the full document or needs a structured writing workflow.
