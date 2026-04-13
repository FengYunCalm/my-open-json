---
name: agent-project-manager
description: Activate when user invokes @project-manager or requests project management tasks. Maintains project status in PROGRESS.md, manages todo items, tracks project statistics, and generates progress reports.
---

# Agent Project Manager

## Local Integration Note

- This skill assumes the target project actually uses progress tracking files such as PROGRESS.md or TODO.md.
- If those files do not exist, ask before creating or modifying them.


This skill activates the Project Manager Agent to manage project progress, todo items, and generate reports.

## When to Activate

- User invokes `@project-manager`
- User requests project status update
- User asks to add/manage todo items
- User requests progress report
- Project milestone tracking needed
- Task prioritization required

## Core Functions

### 1. Project Status Management

Maintain `.system/PROGRESS.md` with:
- Daily work logs
- Module development progress
- Important milestones
- Blockers and dependencies

**PROGRESS.md Structure:**
```markdown
# Project Progress

## Overview
- Start Date: 2024-01-01
- Current Sprint: Sprint 12
- Overall Progress: 68%

## Milestones
| Milestone | Status | Date | Progress |
|-----------|--------|------|----------|
| Core System | 鉁?Done | Jan 15 | 100% |
| Combat Module | 馃攧 In Progress | Feb 28 | 75% |
| Economy System | 鈴?Pending | Mar 15 | 0% |

## Module Progress
| Module | Progress | Status | Notes |
|--------|----------|--------|-------|
| chat | 100% | 鉁?Done | Fully tested |
| combat | 75% | 馃攧 WIP | Damage calc remaining |
| economy | 30% | 馃攧 WIP | Currency system done |

## Work Log
### 2024-02-07
- 鉁?Refactored combat damage calculation
- 鉁?Added critical hit mechanics
- 馃攧 Working on combat state machine

## Blockers
- None currently
```

### 2. Todo Management

Maintain todo list with:
- Task descriptions
- Priority levels
- Status tracking
- Tags and labels
- Time estimates

**Todo Format:**
```markdown
## Todo List

### 馃敶 High Priority
- [ ] Fix combat damage overflow bug (Est: 2h)
  - Tags: #bug #combat #critical
  - Created: 2024-02-07
  
- [ ] Implement player inventory (Est: 1d)
  - Tags: #feature #economy
  - Created: 2024-02-06

### 馃煛 Medium Priority
- [ ] Optimize database queries (Est: 4h)
  - Tags: #optimization #performance
  - Created: 2024-02-05

### 馃煝 Low Priority
- [ ] Update documentation (Est: 2h)
  - Tags: #documentation
  - Created: 2024-02-04
```

### 3. Progress Statistics

Track and calculate:
- Completion percentage
- Task statistics
- Code change metrics
- Time consumption analysis

**Statistics Dashboard:**
```markdown
## 馃搳 Project Statistics

### Task Overview
| Status | Count | Percentage |
|--------|-------|------------|
| Completed | 35 | 70% |
| In Progress | 8 | 16% |
| Pending | 7 | 14% |
| **Total** | **50** | **100%** |

### This Week
- Files Modified: 24
- Lines Added: +1,250
- Lines Removed: -340
- Net Change: +910

### Time Tracking
| Activity | Time Spent |
|----------|------------|
| Development | 32h |
| Bug Fixes | 8h |
| Documentation | 4h |
| Code Review | 6h |
```

### 4. Progress Report Generation

Generate structured reports:

```markdown
## 馃搳 椤圭洰杩涘害鎶ュ憡

### 鐢熸垚鏃堕棿
2024-02-07 15:30:00

### 姒傝
- 鎬讳换鍔℃暟: 50
- 宸插畬鎴? 35 (70%)
- 杩涜涓? 8 (16%)
- 寰呭紑濮? 7 (14%)

### 鏈懆瀹屾垚 鉁?
- 鉁?combat妯″潡閲嶆瀯瀹屾垚
- 鉁?chat绯荤粺鎬ц兘浼樺寲
- 鉁?鏂板party缁勯槦鍔熻兘
- 鉁?淇3涓櫥褰曠浉鍏砨ug

### 杩涜涓?馃攧
| 浠诲姟 | 杩涘害 | 璐熻矗浜?| ETA |
|------|------|--------|-----|
| economy绯荤粺鍗囩骇 | 60% | - | 2澶?|
| quest绯荤粺閲嶆瀯 | 30% | - | 5澶?|

### 寰呭姙 鈴?
- 鈴?skill绯荤粺浼樺寲
- 鈴?faction闃佃惀鍔熻兘寮€鍙?
- 鈴?鏁版嵁搴撹縼绉?

### 椋庨櫓涓庨樆濉?
| 椋庨櫓 | 绾у埆 | 缂撹В鎺柦 |
|------|------|----------|
| economy寤舵湡 | 馃煛 涓?| 澧炲姞寮€鍙戣祫婧?|

### 涓嬪懆璁″垝
1. 瀹屾垚economy绯荤粺鍗囩骇
2. 寮€濮媠kill绯荤粺浼樺寲
3. 杩涜鍏ㄦā鍧楅泦鎴愭祴璇?
```

## Usage Examples

### Example 1: Update Project Status
```
User: @project-manager 鏇存柊鐘舵€?

AI: [婵€娲?project-manager 浠ｇ悊]

馃摑 鏇存柊椤圭洰鐘舵€?..

馃攳 妫€娴嬪埌鍙樻洿:
- 淇敼鏂囦欢: 8涓?
- 娑夊強妯″潡: combat, chat
- 浠诲姟绫诲瀷: 浼樺寲

鉁?宸叉洿鏂?PROGRESS.md
- 宸ヤ綔鏃ュ織: 閲嶆瀯combat鎴樻枟閫昏緫
- 杩涘害鏇存柊: combat妯″潡 80% 鈫?95%
- 寰呭姙鏇存柊: 瀹屾垚combat浼樺寲浠诲姟
```

### Example 2: Add Todo Item
```
User: @project-manager 娣诲姞寰呭姙 浼樺寲skill绯荤粺

AI: [婵€娲?project-manager 浠ｇ悊]

馃搵 娣诲姞寰呭姙浜嬮」...

鉁?宸叉坊鍔犲埌寰呭姙娓呭崟
- 浠诲姟: 浼樺寲skill绯荤粺
- 浼樺厛绾? 涓?
- 鏍囩: #optimization #skill
- 棰勪及: 2澶?
```

### Example 3: Generate Report
```
User: @project-manager 鐢熸垚鎶ュ憡

AI: [婵€娲?project-manager 浠ｇ悊]

馃搳 鐢熸垚杩涘害鎶ュ憡...

[杈撳嚭瀹屾暣椤圭洰杩涘害鎶ュ憡]
```

### Example 4: Mark Task Complete
```
User: @project-manager 瀹屾垚浠诲姟 combat妯″潡閲嶆瀯

AI: 
鉁?鏇存柊浠诲姟鐘舵€?
- 浠诲姟: combat妯″潡閲嶆瀯
- 鐘舵€? 宸插畬鎴?鈫?宸插綊妗?
- 杩涘害: 100%
- 鑰楁椂: 3澶?

馃搳 椤圭洰鏁翠綋杩涘害: 68% 鈫?72%
```

## Task Lifecycle

```
寰呭紑濮?(Pending) 
      鈫?
杩涜涓?(In Progress) 
      鈫?
宸插畬鎴?(Completed) 
      鈫?
宸插綊妗?(Archived)
```

Each stage supports:
- Priority assignment
- Tag/label management
- Time estimation
- Progress tracking

## Priority System

| Priority | Indicator | Description |
|----------|-----------|-------------|
| 馃敶 High | Critical | Emergency bugs, core features |
| 馃煛 Medium | Normal | Optimizations, new features |
| 馃煝 Low | Optional | Documentation, nice-to-have |

## Tag System

Common tags:
- `#bug` - Bug fixes
- `#feature` - New features
- `#optimization` - Performance improvements
- `#refactor` - Code refactoring
- `#documentation` - Documentation updates
- `#test` - Testing related
- `#security` - Security issues
- `#ui` - UI/UX changes

## Output Formats

All outputs use structured markdown for:
- AI readability
- Report generation
- Tool integration
- Export capabilities

## Notes

- Project-specific conventions are respected
- Sensitive paths are redacted in outputs
- Mixed Chinese/English support
- Integration with git for change detection
- Automatic progress calculation


