---
name: doc-coauthoring
description: Use when the user wants to co-author documentation, proposals, technical specs, RFCs, decision docs, or similar structured writing and would benefit from a guided drafting workflow.
---

# Doc Co-Authoring

## Overview

This skill helps turn scattered context into a document that another reader can actually use. It is for writing the document itself, not just polishing prose after the draft already exists.

## Mode Selection

Use **new-draft mode** when the user is starting from notes, ideas, or partial structure.

Use **revision mode** when the user already has a draft and wants to improve it section by section.

Use **reader-check mode** when the draft is mostly complete and the goal is to find missing context, weak structure, or unclear assumptions.

## Workflow

### Stage 1: Gather Context
1. Identify the document type, audience, and desired outcome.
2. Ask for constraints such as required format, template, deadline, or stakeholders.
3. Pull context from files or links only if the current environment can actually access them.
4. If external access is unavailable, ask the user to paste or summarize the relevant material.

### Stage 2: Draft the Document
1. Decide whether the document should live in chat or in a repo-local file.
2. If a file is needed, choose a repo-local markdown path that fits the project.
3. Create a scaffold with the main sections first.
4. Fill the document section by section, keeping each section tied to the user goal and audience.
5. Use the available file-writing and file-editing tools in the current environment instead of assuming artifact-specific tools exist.

### Stage 3: Review for Readers
1. Re-read the draft as if the reader has less context than the author.
2. Look for buried conclusions, missing assumptions, weak transitions, and undefined terms.
3. If wording needs polish, use `bmad-editorial-review-prose`.
4. If structure needs cuts or reordering, use `bmad-editorial-review-structure`.

## Output Format

```markdown
## Document Progress

**Mode:**
**Document type:**
**Audience:**
**Draft location:**
**Current section:**
**Open questions:**
**Next step:**
```

## Good Habits

- Keep the writer and reader goals explicit.
- Prefer markdown files unless the user or repo clearly needs another format.
- Work section by section instead of rewriting the whole document on every pass.
- If a template exists, follow it. If not, propose a practical structure instead of inventing ceremony.

## Boundaries

- Use `brainstorming` before this skill when the problem or direction is still ambiguous.
- Use `writing-plans` when the deliverable should be an implementation plan rather than a proposal or narrative document.
- Use the two `bmad-editorial-review-*` skills after this one when the draft exists and needs editorial refinement rather than co-authoring.
