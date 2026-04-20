---
name: skill-creator
description: Use when the user wants to create, revise, evaluate, or benchmark a skill, including trigger tuning, eval design, iterative improvement, and skill performance comparison.
---

# Skill Creator

## Overview

This skill is for building and improving skills in the current OpenCode environment. The goal is not just to write a `SKILL.md`, but to tighten the trigger, structure the skill well, and verify that it behaves better after revision. Default to manual review and manual trigger analysis in this environment. The bundled `run_eval` and `run_loop` automation is optional legacy tooling for setups that already provide the external `claude` CLI.

## Mode Selection

Use **draft mode** when creating a new skill from scratch.

Use **revision mode** when a skill already exists and needs rewriting or cleanup.

Use **evaluation mode** when the skill exists and the main task is running or improving evals.

Use **description-tuning mode** when the skill works but the trigger wording needs improvement. In this environment, that usually means manual trigger analysis rather than a fully automated loop.

## Workflow

### 1. Capture Intent
1. Clarify what the skill should do.
2. Clarify when it should trigger.
3. Clarify the expected output shape.
4. Decide whether the skill needs objective evals, qualitative review, or both.

### 2. Draft or Revise the Skill
1. Keep `SKILL.md` compact and readable.
2. Put trigger conditions in the frontmatter description.
3. Move heavy reference material to `references/`, reusable automation to `scripts/`, and bundled assets to `assets/`.
4. Explain why important rules exist instead of relying only on blunt commands.

### 3. Choose Evaluation Depth
1. Skip benchmarking when the user only wants a draft, rewrite, or trigger discussion.
2. Use a light first pass for most revisions: save 2 to 3 realistic prompts to `evals/evals.json`, then inspect outputs manually or with a few targeted assertions.
3. Use a full benchmark only when the user explicitly wants performance comparison, the trigger wording changed materially, or qualitative review is not enough.
4. Keep benchmark artifacts in a sibling workspace such as `<skill-name>-workspace/iteration-N/`, not inside the active skill directory.
5. Add files to evals only when the task actually needs file context.

### 4. Run Evaluations
1. For each eval, run the skill-enabled case and a baseline case when a baseline actually answers the user's question.
2. Save outputs in a consistent per-eval directory structure.
3. Draft assertions and write `eval_metadata.json` for each eval.
4. Grade each run using `agents/grader.md`.
5. Aggregate results from the skill directory with `python -m scripts.aggregate_benchmark <benchmark-dir> --skill-name <name>` when the directory layout matches the aggregator's expectations.
6. Treat `run_eval` and `run_loop` as optional external tooling, not part of the default workflow.

### 5. Review and Iterate
1. Compare outputs, not just scores.
2. Fix the trigger, structure, or supporting resources based on what actually failed.
3. Repeat until the user is satisfied or improvements stop paying off.

## OpenCode Notes

- Use the available file tools in this environment to read, write, and edit skill files.
- Use subagents when they materially improve eval speed or grading.
- Run module-based helpers from the skill directory when they are actually relevant: `python -m scripts.aggregate_benchmark` and `python -m scripts.generate_report` are environment-local.
- `python eval-viewer/generate_review.py` also runs from the skill directory and does not need the module form.
- `run_eval`, `improve_description`, and `run_loop` depend on the external `claude` CLI and are not part of the default OpenCode workflow here. Use them only in environments that already provide that CLI.
- `quick_validate.py` is safe to use without extra dependencies.
- If you generate an HTML review page, run `python eval-viewer/generate_review.py <workspace> --skill-name <name> --benchmark <benchmark.json>` from the skill directory. Prefer `--static <output.html>` when browser launching is unavailable.
- Do not assume tools such as `present_files` or `/skill-test` exist.
- Do not promise a fully automated benchmark or trigger-tuning loop in this environment.

## Description Tuning

When tuning a skill description:
1. Create realistic should-trigger and should-not-trigger prompts.
2. Do manual trigger analysis by comparing the current description against the eval set and tightening the wording.
3. Only use the bundled `run_eval` / `run_loop` automation in a different environment that already provides the external `claude` CLI.

## Output Format

```markdown
## Skill Revision Summary

**Mode:**
**Goal:**
**Main edits:**
**Eval plan or benchmark status:**
**Open risks / next iteration ideas:**
```

## Key Resources

- `references/schemas.md`
- `agents/grader.md`
- `agents/analyzer.md`
- `scripts/aggregate_benchmark.py` via `python -m scripts.aggregate_benchmark`
- `scripts/generate_report.py` via `python -m scripts.generate_report`
- `eval-viewer/generate_review.py` via `python eval-viewer/generate_review.py`
- `scripts/run_eval.py`, `scripts/improve_description.py`, and `scripts/run_loop.py` only for external environments that already provide the `claude` CLI

## Boundaries

- Use this skill instead of `writing-skills`; it is the active replacement.
- If the user only wants to discuss whether a skill is needed, `brainstorming` may come first.
- If the user only wants to locate or understand an existing skill, `find-skills` may be enough.
