# Issues

## 2026-05-11 Start
No active blocker yet. Sensitive provider/API fields in `opencode.json` are out of scope and must not be copied into docs/evidence.

## 2026-05-11 Pre-Task-1 Workspace State
`git status --short` shows existing uncommitted changes before Task 1 implementation delegation, including EvoMemory/plugin files plus unrelated files (`tool-forced-eval*`, `skills/ai-player`, `oh-my-openagent*`, `AGENTS.md`, `package.json`). Treat these as existing user/parallel work. Implementation agents must inspect current contents and preserve unrelated changes; no reset, checkout, broad rewrite, or cleanup of files outside the task scope.

## 2026-05-12 Task 1 Verification Rejection
Atlas code review found `plugins/tests/evomemory_replay_runner.mjs` does not support the plan QA commands with `--case positive-preference` and `--case negative-current-code`. Current parser only accepts `--summary` and `--fixtures`, so Task 1 is not executable as planned even though the all-case replay command exists. Fix must preserve the all-case summary behavior and add deterministic single-case support/evidence.

## 2026-05-12 Task 3 Initial Delegation Incomplete
The first Task 3 delegation returned without modifying Task 3 target files and without creating `.sisyphus/evidence/task-3-namespace.json` or `.sisyphus/evidence/task-3-legacy-compat.json`. Treat Task 3 as not started for implementation purposes. The returned output did not expose a concrete reusable Task 3 session id, so the next implementation attempt must be a fresh focused delegation.

## 2026-05-12 Task 8 Delegation Blocker
Task 8 was delegated multiple times, including preferred session `[redacted-session-id]`, but only `mcp/evomemory/context/retention_service.py` received partial audit-event changes. Required retention tests, plugin maintenance fail-open test, `.sisyphus/evidence/task-8-retention-dry-run.json`, `.sisyphus/evidence/task-8-maintenance-fail-open.json`, and Task 8 notepad closeout were still missing on verification. Leave Task 8 unchecked and continue independent Task 9; return to Task 8 before Task 10/final wave.

## 2026-05-12 Task 8 Reuse Session Failure
Preferred reuse session `[redacted-session-id]` repeatedly returned completion summaries without actually creating the missing Task 8 evidence files, maintenance fail-open plugin test, or Task 8 notepad closeout. It also left weak retention assertions in place (`protected_*` only checked as lists, rollback fields asserted absent). Treat the reuse session as unreliable for Task 8 follow-up and switch to a fresh focused implementation session.

## 2026-05-12 Task 8 Exact Regression Retry Failure
Regression-fix session `[redacted-session-id]` was given the exact broken line in `mcp/evomemory/context/retention_service.py` and the exact replacement logic, but verification showed the file still contained `if not normalized_dry_run and normalized_safe and purgeable_ids:`. Targeted and full EvoMemory pytest continued to fail on `test_retention_can_purge_old_current_drawers_when_safe_mode_is_disabled`. Treat this session as unreliable for further Task 8 fixes.

## 2026-05-12 Task 10 Verification Rejection
Task 10 initial delivery from session `[redacted-session-id]` is incomplete and partially inaccurate. Atlas verification found `.sisyphus/evidence/task-10-final-replay.json` still contains the old fake comparison shape (`before` mirrors current metrics, `after` is null) instead of a truthful Task 1 baseline vs final comparison. `.sisyphus/evidence/task-10-docs-safety.txt` incorrectly claims no session IDs were present, but the replay evidence still includes synthetic `session_id` and `directory` fields from fixtures. `learnings.md` also lacks a Task 10 closeout section. Reuse the same session and fix these exact gaps before Task 10 can be accepted.

## 2026-05-12 Task 10 Reuse Session Failed Again
After Atlas resumed `[redacted-session-id]` with explicit instructions, verification still found no effective fix: rerunning `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/task-10-final-replay.json` continued to emit placeholder comparison data (`before=current`, `after=null`), `task-10-docs-safety.txt` still falsely claimed no `session_id` matches, and `learnings.md` still had no Task 10 closeout section. Any solution that depends on post-processing the JSON after the replay command is invalid, because the required gate command overwrites the summary file. Task 10 now requires a fresh focused session that makes the replay runner itself write truthful comparison output.

## 2026-05-12 Task 10 Final Doc Drift
Fresh session `[redacted-session-id]` successfully fixed the replay runner and docs-safety evidence, but Atlas verification found one remaining documentation inconsistency: `mcp/evomemory/README.md` still says the replay summary `after` field must be populated manually or by post-processor, which is no longer true after the runner fix. Atlas also reran the required replay gate command, so the current `task-10-final-replay.json` latency values changed slightly; the Task 10 closeout in `learnings.md` should reflect the current verified evidence or clearly say it references the latest rerun. Fix only these final consistency issues.
