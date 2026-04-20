---
name: verification-before-completion
description: Use when you are about to report success, close work, commit, or open a PR and need fresh evidence for claims about correctness or completion.
---

# Verification Before Completion

## Overview

This skill exists to stop evidence-free success claims. Verification should match the claim being made: a unit test is not the same as a full build, and a linter result is not proof that a bug is fixed.

## Workflow

1. Identify the claim.
2. Pick the smallest fresh command or check that can actually prove that claim.
3. Run it now, not from memory.
4. Read the output and exit status.
5. State the result together with the evidence.

## Choosing Verification Scope

Use a **targeted check** when the claim is narrow:
- a specific bug reproduction
- one endpoint
- one component behavior

Use a **broader check** when the claim is broad:
- "all tests pass"
- "the build succeeds"
- "ready to merge"

## Claim-to-Evidence Examples

| Claim | Strong evidence |
|------|-----------------|
| Bug fixed | Reproduction now passes for the original failing case |
| Tests pass | Fresh test output with zero failures |
| Build succeeds | Fresh build output with exit code 0 |
| Ready for PR | Relevant verification plus a clean understanding of remaining risks |

## Output Format

```markdown
## Verification

**Claim:**
**Command / check:**
**Observed result:**
**Conclusion:**
**Remaining risk:**
```

## Red Flags

Do not claim success based on:
- a previous run
- partial evidence
- confidence without output
- "should work now"
- a delegated agent saying it finished

## Why This Matters

False completion creates rework, weakens trust, and makes later debugging harder. Fresh evidence is cheaper than undoing a confident but wrong claim.
