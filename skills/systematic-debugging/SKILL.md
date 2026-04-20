---
name: systematic-debugging
description: Use when a bug, failing test, or unexpected behavior needs root-cause analysis before choosing a fix, especially when the issue may cross components or the correct fix is not yet clear.
---

# Systematic Debugging

## Overview

The fastest-looking fix is often the slowest overall if it is based on guesswork. This skill keeps debugging grounded in evidence so that the chosen fix actually addresses the source of the problem.

Use this skill for root-cause analysis. If the user's main goal is just to choose a test command, run tests, collect coverage, or summarize raw test output, use `agent-test-runner` instead.

## Mode Selection

Use **single-component mode** when the failure is local to one file, function, or test.

Use **multi-component mode** when the issue crosses boundaries such as:
- API to service to database
- CI to build to signing
- UI to backend to cache

## The Four Phases

### 1. Investigate the Failure
- read the actual error message
- reproduce the issue reliably if possible
- check recent changes that could explain it
- gather evidence before proposing a fix

### 2. Compare Against Working Patterns
- find similar code that already works
- identify meaningful differences
- confirm assumptions about dependencies and configuration

### 3. Form and Test a Hypothesis
- state the most likely root cause
- test one variable at a time
- update the hypothesis when evidence disagrees

### 4. Implement and Verify
- add the smallest failing reproduction you can automate
- fix the root cause, not the symptom
- rerun the targeted verification and relevant nearby checks

## Why This Order Helps

This workflow lowers two expensive failure modes:
- stacking random fixes until the problem gets harder to reason about
- patching symptoms in a way that hides the real architectural weakness

## Output Format

```markdown
## Debugging Summary

**Symptom:**
**Evidence gathered:**
**Likely root cause:**
**Fix chosen:**
**Verification:**
**Remaining risks / unknowns:**
```

## Multi-Component Guidance

When the bug crosses boundaries, log or inspect data at each boundary first. The point is to learn where the signal turns bad, not to guess which layer is guilty.

## Red Flags

Pause and restart the evidence-gathering phase if you catch yourself thinking:
- "I'll just try one quick fix"
- "It's probably X"
- "Let's change three things and rerun"
- "I don't fully understand it, but this seems plausible"

## Supporting References

- `root-cause-tracing.md`
- `defense-in-depth.md`
- `condition-based-waiting.md`

## Related Skills

- `test-driven-development`
- `verification-before-completion`
