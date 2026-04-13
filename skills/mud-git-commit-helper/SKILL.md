---
name: mud-git-commit-helper
description: |
  XiaKeXing MUD Git commit assistant. Generates Chinese commit messages following project conventions.
  
  Use when: committing code changes, generating commit messages, or organizing git history for the MUD project.
  
  Trigger phrases: "鎻愪氦", "commit", "鐢熸垚鎻愪氦", "git commit"
---

# MUD Git Commit Helper

## Local Integration Note

- Use this only for XiaKeXing or similar MUD repos that want Chinese commit messages.
- Do not use it as a generic git commit skill outside that context.


## Overview

Generates Chinese commit messages following XiaKeXing MUD project conventions.

## Commit Types

| Type | Chinese | When to Use |
|------|---------|-------------|
| `娣诲姞` | Add | New features or files |
| `淇` | Fix | Bug fixes |
| `浼樺寲` | Optimize | Performance improvements |
| `閲嶆瀯` | Refactor | Code restructuring |
| `鍒犻櫎` | Remove | Deleted code or files |
| `鏂囨。` | Docs | Documentation updates |

## Commit Message Format

```
{绫诲瀷}: {鎻忚堪}

绫诲瀷: 娣诲姞/淇/浼樺寲/閲嶆瀯/鍒犻櫎/鏂囨。
```

## Examples

```bash
# Adding new feature
git commit -m "娣诲姞: 鐢ㄦ埛璁よ瘉妯″潡"

# Bug fix
git commit -m "淇: 鐧诲綍瓒呮椂闂"

# Performance optimization
git commit -m "浼樺寲: 鏁版嵁搴撴煡璇㈡€ц兘"

# Refactoring
git commit -m "閲嶆瀯: 鎴樻枟绯荤粺鏋舵瀯"

# Documentation
git commit -m "鏂囨。: 鏇存柊API璇存槑"
```

## Module Detection

The helper automatically detects modified modules:

| Module | Path Pattern |
|--------|--------------|
| `combat` | `core/daemon/combatd.c`, `core/framework/combat.c` |
| `dbase` | `core/framework/data.c` |
| `protocol` | `core/framework/xk_protocol*.c` |
| `commands` | `game/commands/**/*.c` |
| `daemon` | `core/daemon/*.c` |
| `entity` | `core/entity/*.c` |
| `client` | `client/**/*.kt` |

## Workflow

1. Analyze `git diff` changes
2. Detect modified modules
3. Determine commit type
4. Generate Chinese message
5. Execute `git commit`

## Quick Commands

```bash
# Standard commit process
skill: mud-git-commit-helper

# Or manually:
git add <files>
git commit -m "绫诲瀷: 鎻忚堪"
```


