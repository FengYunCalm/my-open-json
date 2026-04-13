---
name: code-check
description: Check code compliance with project standards including LPC/Vue/Mobile coding conventions, quality metrics, and performance. Use when user asks to "check code", "检查规范", "代码规范检查".
---

# Code Check Skill

This skill performs comprehensive code checks against project standards, including coding conventions, quality metrics, and performance analysis.

## When to Activate

- User requests code quality check
- Before committing code
- User says "/check", "检查规范", or "代码规范检查"
- Code review preparation

## Check Categories

### 1. LPC Code Standards

#### Naming Conventions
- [ ] File names: lowercase with underscores (e.g., `combat_system.c`)
- [ ] Function names: lowercase with underscores (e.g., `calculate_damage()`)
- [ ] Variable names: descriptive and consistent
- [ ] Constants: uppercase with underscores

#### Inheritance
- [ ] Correct inheritance hierarchy
- [ ] Proper parent class usage
- [ ] No circular dependencies

#### Memory Management
- [ ] `new` and `destruct` are paired
- [ ] No memory leaks
- [ ] Proper resource cleanup

#### SQL Safety
- [ ] Use parameterized queries
- [ ] No string concatenation in SQL
- [ ] Input sanitization present

#### Documentation
- [ ] Function comments present
- [ ] Complex logic explained
- [ ] Public APIs documented

### 2. Code Quality Metrics

#### Function Length
- [ ] Functions under 200 lines
- [ ] Single responsibility principle
- [ ] Logical code grouping

#### Nesting Depth
- [ ] Maximum 4 levels of nesting
- [ ] Early returns used appropriately
- [ ] Helper functions for complex logic

#### Cyclomatic Complexity
- [ ] Complexity under 10 per function
- [ ] Switch statements have default case
- [ ] Boolean logic is clear

#### Code Redundancy
- [ ] No dead code
- [ ] No duplicate code blocks
- [ ] Common logic extracted to functions

### 3. Performance Checks

#### Database Queries
- [ ] Queries are optimized
- [ ] Proper indexing utilized
- [ ] No N+1 query problems
- [ ] Pagination for large datasets

#### Caching Strategy
- [ ] Appropriate caching implemented
- [ ] Cache invalidation logic
- [ ] No over-caching

#### Memory Usage
- [ ] No memory leaks
- [ ] Large objects properly managed
- [ ] Temporary files cleaned up

### 4. Vue/Frontend Standards

#### Component Structure
- [ ] Single File Components (.vue)
- [ ] Props properly typed
- [ ] Events properly documented

#### API Usage
- [ ] Consistent API call patterns
- [ ] Error handling implemented
- [ ] Loading states managed

#### Styling
- [ ] Scoped styles used
- [ ] Consistent naming conventions
- [ ] Responsive design considered

### 5. Mobile Standards

#### Component Library
- [ ] Platform components used correctly
- [ ] Consistent UI patterns
- [ ] Accessibility considered

#### Styling
- [ ] Responsive units (rpx for wechat)
- [ ] Platform-specific adaptations
- [ ] Touch targets appropriate size

## Execution Workflow

### 1. Gather Files
```bash
# Get modified files
git diff --name-only

# Get all source files
find . -name "*.c" -o -name "*.vue" -o -name "*.js" -o -name "*.ts"
```

### 2. Run Checks
Analyze each file against standards:
- Naming conventions
- Code structure
- Security patterns
- Performance indicators

### 3. Generate Report

#### Output Format
```
📋 Code Check Report

✅ Passed: 15 files
⚠️  Warnings: 3 files
❌ Errors: 1 file

─────────────────────────────

✅ modules/chat/chat.c
   - Naming: Pass
   - Quality: Pass
   - Security: Pass
   - Performance: Pass

⚠️  modules/combat/fight.c
   - Line 120: Use likeCast() instead of like()
   - Line 250: Function too long (210 lines)
   - Suggestion: Split into smaller functions

❌ modules/user/login.c
   - Line 89: SQL injection risk
   - Fix: Use parameterized queries
```

## Fix Suggestions

### SQL Injection Example
**Problem:**
```c
// DANGEROUS
string query = "SELECT * FROM users WHERE name = '" + name + "'";
```

**Fix:**
```c
// SAFE
string query = "SELECT * FROM users WHERE name = ?";
db_query(query, ({ name }));
```

### Function Length Example
**Problem:**
```c
void complex_function() {
    // 300+ lines of code
}
```

**Fix:**
```c
void step_one() { /* ... */ }
void step_two() { /* ... */ }
void step_three() { /* ... */ }

void complex_function() {
    step_one();
    step_two();
    step_three();
}
```

## Usage Commands

```bash
# Direct command
/check

# With target
/check combat.c
/check modules/

# Natural language
"检查代码规范"
"代码质量检查"
"检查我的代码"
```

## Severity Levels

| Level | Description | Action Required |
|-------|-------------|-----------------|
| 🔴 Error | Security risk or broken functionality | Must fix before commit |
| 🟡 Warning | Code smell or potential issue | Should fix |
| 🟢 Info | Suggestion for improvement | Optional |

## Pre-Commit Checklist

Run this skill before committing:
- [ ] All new files checked
- [ ] No errors present
- [ ] Critical warnings addressed
- [ ] Security checks passed
- [ ] Performance acceptable

---

**Remember**: Code checks prevent bugs and maintain consistency. Address all errors and seriously consider all warnings before committing code.
