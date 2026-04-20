---
name: test-driven-development
description: Use when implementing or fixing behavior where an automated failing test can define the intended outcome before code is changed.
---

# Test-Driven Development

## Overview

TDD is useful because it defines success before implementation bias appears. The point is not ritual. The point is to prove that the test can catch the problem before the code is written.

## When to Use

Use TDD for:
- new behavior
- bug fixes
- refactors that should preserve behavior
- regression coverage for previously broken paths

Usually skip it or simplify it for:
- throwaway prototypes
- generated code
- pure configuration or documentation edits

## The Core Loop

1. **Red**: write one focused test that describes the intended behavior.
2. **Verify red**: run it and make sure it fails for the expected reason.
3. **Green**: write the smallest implementation that makes it pass.
4. **Verify green**: rerun the test and the nearby suite.
5. **Refactor**: improve structure without changing behavior.

## Why Order Matters

Writing the test first reduces three common mistakes:
- testing what you happened to build instead of what was required
- missing edge cases because they were never named up front
- shipping a test that passes immediately but proves very little

## Practical Rules

- Keep each test about one behavior.
- Prefer real behavior over mock-only assertions.
- When fixing a bug, start with the smallest reproducible failing test.
- If a test is hard to write, treat that as a design signal, not just a testing inconvenience.

## Output Checklist

Before claiming a TDD cycle is complete, confirm:
- the new test failed first
- the failure matched the intended gap
- the minimal implementation now passes
- nearby tests still pass

## Example

```typescript
test('rejects empty email', async () => {
  const result = await submitForm({ email: '' });
  expect(result.error).toBe('Email required');
});
```

Then run it, watch it fail, implement the smallest fix, and rerun it.

## Red Flags

Slow down when you catch yourself thinking:
- "I'll add tests after"
- "manual testing is enough here"
- "this is too small to need a test"
- "I'll keep the implementation as reference while I write the test"

Those are usually signs that implementation bias has already taken over.

## Related Reference

For mock-related pitfalls, read `@testing-anti-patterns.md`.
