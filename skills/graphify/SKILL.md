---
name: graphify
description: Use when the user explicitly invokes `/graphify` or asks you to run graphify to build, update, or query a persistent knowledge graph for a codebase or mixed document corpus.
trigger: /graphify
---

# Graphify

## Overview

Graphify is for graph-shaped understanding: building a persistent graph from code or documents, updating that graph over time, and querying it later. It is not a generic code-search replacement.

This is a manual command-style skill. Prefer it when the user explicitly asks for `/graphify` or graphify-specific operations, not as a generic auto-trigger replacement for ordinary code search.

## Mode Selection

Use **build mode** to create graph output for a repo or corpus, or to fully refresh it.

Use **update mode** for incremental refreshes of existing graph output.

Use **query mode** to ask graph questions, trace paths, or explain nodes.

Use **watch mode** when the user explicitly wants continuous graph maintenance.

Use **add mode** when the user wants to ingest a URL into the corpus.

For **update**, **query**, or **watch** mode, expect an existing graphify corpus such as `graphify-out/`. If it does not exist yet, start with **build mode** instead of pretending the graph already exists.

## Workflow

1. Confirm that graphify is relevant to the current project or corpus.
2. Choose the mode that matches the user's intent.
3. Run only that mode.
4. Report the resulting artifacts and any warnings.

## Output Format

```markdown
## Graphify Result

**Mode:**
**Target path or source:**
**Artifacts produced or updated:**
**Warnings / limits:**
**Suggested next query or follow-up:**
```

## References

- `references/commands.md` for command-entry patterns
- `references/outputs.md` for common artifacts and what to report back

## Notes

- Use this only when graphify is installed and the user explicitly wants graph-based understanding.
- `graphify-out/` is not required for **build mode**.
- `graphify-out/` or an equivalent graph corpus is expected for **update**, **query**, and **watch** mode.
- For ordinary code search, use the normal repo search tools instead.
