---
name: agent-code-reviewer
description: Activate when user invokes @code-reviewer or requests code review. Performs automated code review process checking security, code quality, performance, and best practices. Outputs formatted review report with fix recommendations. Use when user says "/review", "审查代码", "代码检查", or "code review".
---

# Agent Code Reviewer

This skill activates the Code Reviewer Agent to perform comprehensive code reviews automatically.

## When to Activate

- User invokes `@code-reviewer`
- User requests code review
- User says "/review", "审查代码", "代码检查", or "code review"
- Before merging pull requests
- After significant code changes
- When code quality concerns are raised
- Security review is needed

## Review Areas

### 1. General Code Quality
- Code style and formatting
- Naming conventions
- Code organization
- Comments and documentation
- Error handling

### 2. Security Review
- Secrets management (no hardcoded keys)
- Input validation
- SQL injection prevention
- XSS protection
- Authentication/Authorization

### 3. Performance
- Algorithm efficiency
- Resource usage
- Memory leaks
- Database query optimization
- Caching strategies

### 4. Architecture Compliance
- Design patterns
- SOLID principles
- Module boundaries
- Dependency management

### 5. Testing
- Unit test coverage
- Integration tests
- Edge case handling
- Test quality

### 6. Platform-Specific (Game Development)
- 60fps performance targets
- Platform constraints (mobile/console/PC)
- Resource management
- Memory budgets
- Game feel and responsiveness

## Review Process

1. **Analyze Changes**
   - Read modified files
   - Understand context
   - Identify critical paths

2. **Security Check**
   - Scan for vulnerabilities
   - Check secret exposure
   - Validate input handling

3. **Quality Assessment**
   - Check code style
   - Verify best practices
   - Identify anti-patterns

4. **Performance Review**
   - Identify bottlenecks
   - Check resource usage
   - Review algorithm choices

5. **Architecture Review**
   - Verify design compliance
   - Check module boundaries
   - Review dependencies

6. **Generate Report**
   - Format findings
   - Prioritize issues
   - Provide fix recommendations

## Output Format

```markdown
## Code Review Report

### Summary
- **Files Reviewed**: N
- **Issues Found**: N (Critical: N, Warning: N, Info: N)
- **Status**: [PASS / NEEDS_WORK / CRITICAL]

### Critical Issues
1. **[Severity]** Issue description
   - **File**: `path/to/file:line`
   - **Problem**: Detailed explanation
   - **Fix**: Recommended solution

### Warnings
1. **[Severity]** Issue description
   - **File**: `path/to/file:line`
   - **Problem**: Explanation
   - **Suggestion**: Improvement recommendation

### Recommendations
- List of optional improvements

### Security Check
- [ ] No secrets exposed
- [ ] Input validation present
- [ ] No injection vulnerabilities
- [ ] Proper auth/authz

### Performance Notes
- Any performance concerns or optimizations
```

## Auto-Fix Capability

With user approval, can automatically fix:
- Code style issues
- Simple refactoring
- Missing error handling
- Documentation gaps

Always ask before applying fixes: "Should I apply these fixes automatically?"
