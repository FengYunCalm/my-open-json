---
name: code-locator
description: Use when you need to locate an implementation, definition, call site, entry point, or related module in a codebase, including requests like where is this implemented, who calls this, 定位代码, 查找功能, or 代码在哪.
---

# Code Locator

## Overview

This skill helps turn a vague "where is this?" request into a focused search strategy. The key is to choose the right search mode before scanning the repo.

## Mode Selection

Use **module mode** for modules, subsystems, or directories.

Use **symbol mode** for functions, classes, methods, exported names, or constants.

Use **feature mode** for concepts, behaviors, or entry points.

Use **pattern mode** for wildcard-like file searches.

## Workflow

1. Identify what the user is really asking for.
2. Pick the search mode.
3. Search definitions, usages, and nearby files in that order.
4. Return the most relevant locations, not a raw dump.

## Output Format

```markdown
## Code Location Result

**Search target:**
**Primary matches:**
**Definitions / entry points:**
**Related files:**
**Tests or examples:**
```

## Reference

Read `references/locating-patterns.md` for common search starting points by project type.

## Example

User: "谁在调用 `create_party`?"

Good result: definition, key call sites, related header or interface file, and the nearest test or usage example.
