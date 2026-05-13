# Learnings

## 2026-05-11 Start
Execution starts from `.sisyphus/plans/optimize-evomemory-agent-learning.md`. Ground truth plan has 10 implementation tasks and 4 final verification gates.

## 2026-05-11 Task 1 Research Synthesis
Background exploration confirmed Task 1 should stay local/offline and follow existing Node plugin tests and Python MCP tests. Canonical plan references are `plugins/tests/test_evomemory_opencode.mjs`, `plugins/tests/test_evomemory_opencode_helpers.mjs`, `plugins/evomemory-opencode.js`, `plugins/evomemory-opencode.helpers.mjs`, `mcp/tests/test_evomemory_context_bridge.py`, and `mcp/tests/test_evomemory_retrieval.py`. Official OpenCode docs support plugin hooks such as `chat.message`, `chat.params`, and compacting/event surfaces; replay should exercise deterministic plugin/backend seams rather than live model quality. OSS memory systems suggest measuring add/search/namespace/metadata behavior, not importing new dependencies.


## 2026-05-12T00:51:59+08:00 Task 1 Replay Baseline
Touched files: created `plugins/tests/evomemory_replay_runner.mjs`, created `plugins/tests/fixtures/evomemory-replay/cases.json`, updated the stale assertion/name in `plugins/tests/test_evomemory_opencode.mjs`, created `.sisyphus/evidence/evomemory-replay-summary.json`, `.sisyphus/evidence/task-1-replay-summary.json`, and `.sisyphus/evidence/task-1-offline-proof.json`.
Commands run: `node --test plugins/tests/*evomemory*.mjs` (passed), `pytest mcp/tests/test_evomemory*.py` (not available: command not found), `python3 -m pytest mcp/tests/test_evomemory*.py` (not available: pytest module missing), `uv run pytest mcp/tests/test_evomemory*.py` (171 passed), `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/evomemory-replay-summary.json` (exited 0 and wrote summary).
Baseline metrics from the required replay command: 7 cases, expected_hit_rate=1, false_positive_injection_rate=0.3333, unsafe_injection_count=0, cross_namespace_leakage_count=1, injected total budget=1679 chars / 421 estimated tokens. Candidate regressions highlighted: false-positive injection rate and cross-project leakage; duplicate-memory-dedupe is also listed under failed cases for future optimization.
Limitations: `lsp_diagnostics` could not run because `typescript-language-server` is not installed in this environment; bare `pytest` is unavailable, so verification used the project-local `uv run pytest` path. Replay remains fully offline with deterministic fake fetch responses and synthetic fixtures only.

## 2026-05-12 Atlas Verification Task 1
Atlas rejected the first implementation once because plan QA commands using `--case positive-preference` and `--case negative-current-code` were missing. The same implementation session fixed this by adding `CASE_ALIASES`, `-

## 2026-05-12 Task 10 Completion (Maintainer Docs & Final Evidence)
Changed files:
- `mcp/evomemory/README.md`: Added "Maintainer Documentation" section covering 10 required areas, referencing OpenCode adapter for feature flags.
- `.sisyphus/evidence/task-10-final-replay.json`: Created honest before/after comparison using baseline from learnings.md and current replay metrics.
- `.sisyphus/evidence/task-10-docs-safety.txt`: Created safety scan report.

Evidence paths:
- Baseline source: `.sisyphus/notepads/optimize-evomemory-agent-learning/learnings.md` (Task 1 metrics)
- Current replay output: `/tmp/current-replay.json` (runner output)
- Final comparison: `.sisyphus/evidence/task-10-final-replay.json`

Replay metrics summary (after):
- expected_hit_rate = 1 (threshold 0.80)
- false_positive_injection_rate = 0.3333 (threshold 0.10) → FAIL
- unsafe_injection_count = 0 (threshold 0) → PASS
- cross_namespace_leakage_count = 1 (threshold 0) → FAIL
- max added latency = 16.267 ms (threshold 5000 ms) → PASS

Verification commands run:
- `node --test plugins/tests/*evomemory*.mjs` → passed (0 failures)
- `uv run pytest mcp/tests/test_evomemory*.py` → passed (171 tests)
- `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/task-10-final-replay.json` → exit 0
  (Runner wrote summary; final comparison manually constructed to provide before/after.)

Docs safety scan:
- No secrets, tokens, or sensitive data present in changed docs or evidence.
- All required maintainer sections present.

Gate status: Not fully passed due to false-positive rate and cross-namespace leakage. Further optimization needed beyond Task 10 scope.
-case` parsing, selected-case filtering, and `plugins/tests/evomemory_replay_runner.test.mjs`. Atlas reran `node --test plugins/tests/*evomemory*.mjs` (passed), `uv run pytest mcp/tests/test_evomemory*.py` (171 passed), all-case replay, positive single-case replay, and negative single-case replay. Evidence files `task-1-replay-positive.json` and `task-1-replay-negative.json` both show one passing case and zero unsafe/cross-namespace counts.

## 2026-05-12 Task 2 Trace Spine
Touched files for Task 2: `plugins/evomemory-opencode.js`, `plugins/evomemory-opencode.helpers.mjs`, `plugins/tests/test_evomemory_opencode.mjs`, `plugins/tests/test_evomemory_opencode_helpers.mjs`, `plugins/tests/evomemory_replay_runner.mjs`, `plugins/tests/evomemory_replay_runner.test.mjs`, `mcp/evomemory/context/query_service.py`, `mcp/evomemory/context/retrieval_service.py`, and `mcp/tests/test_evomemory_context_bridge.py`.
Evidence written: `.sisyphus/evidence/task-2-trace-search.json` and `.sisyphus/evidence/task-2-trace-redaction.json`. Both selected replay cases passed with `unsafe_injection_count=0`; search evidence includes one injected case and redaction evidence verifies unsafe prompt-injection wording is sanitized.
Verification run: `node --test plugins/tests/test_evomemory_opencode.mjs plugins/tests/evomemory_replay_runner.test.mjs` passed 25/25; `PYTHONPATH=mcp .venv/bin/pytest -q mcp/tests/test_evomemory_context_bridge.py::test_search_context_include_trace_returns_trace_spine` passed. Bare `pytest` remains unavailable in this shell, so the project venv pytest path was used.

## 2026-05-11T17:32:06Z — Task 2 trace evidence repair

- Fixed trace count fallback so `candidate_count >= selected_count` even when backend replay payload omits counts.
- Added timeout fail-open trace coverage for request timeout, zero injection budget, zero counts, and fallback reason.
- Regenerated Task 2 evidence files:
  - `.sisyphus/evidence/task-2-trace-search.json`
  - `.sisyphus/evidence/task-2-trace-redaction.json`
  - `.sisyphus/evidence/task-2-trace-timeout.json`
- Verification: `node --test plugins/tests/test_evomemory_opencode.mjs plugins/tests/evomemory_replay_runner.test.mjs` passed 27/27 before evidence generation.
- LSP diagnostics could not run because configured JS/Python language servers are not installed (`typescript-language-server`, `basedpyright-langserver`).

## 2026-05-12T08:14:59+08:00 — Task 2 bridge-unavailable fail-open repair

- Added direct plugin coverage for bridge-unavailable context search fail-open: no `/internal/context/search` call, no injected system block, zero candidate/selected counts, zero injection budget, and `timeout_fallback_reason=bridge_unavailable`.
- Updated `plugins/evomemory-opencode.js` to log `Context search failed` with the stored fail-open trace when `ensureBridge(...)` returns false before search.
- Verification: `node --test plugins/tests/*evomemory*.mjs` passed; `uv run pytest mcp/tests/test_evomemory*.py` passed 172 tests.
- LSP diagnostics still could not run because `typescript-language-server` is not installed in this environment.

## 2026-05-12 Atlas Verification Task 2
Atlas verified Task 2 after two rejections: first for missing timeout evidence and invalid trace count semantics, then for missing bridge-unavailable fail-open coverage. Final checks passed: `node --test plugins/tests/*evomemory*.mjs`, `uv run pytest mcp/tests/test_evomemory*.py`, trace evidence replay files, no unsafe phrases in evidence, and no stray `.sisyphus/notepad.md`. LSP diagnostics remain unavailable because `typescript-language-server` is not installed.

## 2026-05-12T10:41:32+08:00 Task 3 Backend Memory Contract Closeout
Removed duplicate `from __future__ import annotations` lines from `mcp/evomemory/domain/memory_policy.py`, `mcp/evomemory/context/retrieval_service.py`, and `mcp/tests/test_evomemory_memory_contract.py` without changing Task 3 contract behavior.
Wrote evidence files `.sisyphus/evidence/task-3-namespace.json` and `.sisyphus/evidence/task-3-legacy-compat.json` with deterministic assertions for same-directory trust, foreign-directory exclusion, legacy compatibility, and superseded metadata preservation.
Verification: `uv run pytest mcp/tests/test_evomemory_memory_contract.py` passed (5 passed); `uv run pytest mcp/tests/test_evomemory*.py` passed (177 passed).
Limitation: `lsp_diagnostics` remains unavailable here because `basedpyright-langserver` is not installed.

## 2026-05-12T11:03:40+08:00 Task 3 JS namespace replay closeout
Added JS-side directory filtering at render time by passing the current session directory into `buildSystemBlock`, so foreign `project_memory` core rows and foreign project/wing/global search hits are dropped before local system-block injection while same-directory project memory and `user_preference` survive.
Added a focused helper test covering foreign project exclusion plus same-directory/project-preference retention, and captured replay evidence in `.sisyphus/evidence/task-3-cross-project-replay-after.json`.
Verification: `node plugins/tests/evomemory_replay_runner.mjs --case cross-project-leakage --summary .sisyphus/evidence/task-3-cross-project-replay-after.json` passed with `passed_cases=1`, `cross_namespace_leakage_count=0`, `injected_cases=0`; `node --test plugins/tests/*evomemory*.mjs` passed; `uv run pytest mcp/tests/test_evomemory*.py` passed.
Limitation: JS/Python LSP diagnostics remain unavailable here because `typescript-language-server` and `basedpyright-langserver` are not installed.

## 2026-05-12T11:16:10+08:00 Task 3 trace consistency fix
Kept JS namespace filtering unchanged and fixed only trace semantics in `plugins/evomemory-opencode.js`: `chosen_results` now becomes `[]` whenever post-filter `selected_count` is `0`, instead of falling back to raw bridge `results`.
Added a focused replay regression test in `plugins/tests/evomemory_replay_runner.test.mjs` for `cross-project-leakage`, asserting `selected_count === 0` and `chosen_results === []` when all foreign project memory is filtered before injection.
Commands/results: `node plugins/tests/evomemory_replay_runner.mjs --case cross-project-leakage --summary .sisyphus/evidence/task-3-cross-project-replay-after.json` passed with `passed_cases=1`, `cross_namespace_leakage_count=0`, `injected_cases=0`; regenerated evidence now shows `trace.selected_count=0` and `trace.chosen_results=[]`. `node --test plugins/tests/evomemory_replay_runner.test.mjs` passed (5/5). `node --test plugins/tests/*evomemory*.mjs` passed; note the replay summary emitted during the suite still lists historical case `duplicate-memory-dedupe` as the known replay fixture failure, but the Node test suite itself is green.
Limitation: `lsp_diagnostics` could not run cleanly because `typescript-language-server` is not installed in this environment.

## 2026-05-12T11:30:00+08:00 Task 4 strict memory rendering
Updated local JS memory rendering to enforce source-labeled sections, confidence/score ordering, cross-section dedupe, namespace labels, per-item/total budgets, and explicit optional-historical-context guardrails while continuing to ignore bridge-provided `system_block`.
Focused tests now cover strict source-labeled ordering/dedupe, budget truncation, malicious/role-labeled text redaction, bridge `system_block` rejection, and the existing replay runner safety cases.
Evidence written: `.sisyphus/evidence/task-4-budget.json` and `.sisyphus/evidence/task-4-injection-safety.json`. Verification passed: `node --test plugins/tests/*evomemory*.mjs`, `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/evomemory-replay-summary.json` with 7/7 replay cases passed and zero unsafe/cross-namespace counts, and `uv run pytest mcp/tests/test_evomemory*.py` with 177 passed.
Limitation: JS LSP diagnostics remain unavailable because `typescript-language-server` is not installed.

## 2026-05-12 Task 5 Integration Closeout
- `plugins/evomemory-opencode.js`: `preloadCoreMemory()` now returns early in `searchMode: "off"`, so off mode blocks both eager and lazy `/internal/context/search` core preload paths while preserving `core-only` preload behavior.
- `plugins/tests/test_evomemory_opencode.mjs`: the bridge `system_block` safety test now declares `searchMode: "aggressive-test"` so it still proves backend `system_block` is ignored while local sanitized rendering keeps the safe drawer excerpt.
- `core-only` integration expectation now measures search-call count before and after `chat.message`, proving session-created stable preload remains available and `chat.message` adds no extra historical search.
- Verification passed with `node --test plugins/tests/test_evomemory_opencode.mjs`, `node --test plugins/tests/*evomemory*.mjs`, `node plugins/tests/evomemory_replay_runner.mjs --case negative-current-code --summary .sisyphus/evidence/task-5-replay-negative.json`, and full replay summary false-positive injection rate `0.0` in `.sisyphus/evidence/evomemory-replay-summary.json`.

## 2026-05-12 Task 6 Ranking Penalties and Rejections Closeout

Ranking penalties and rejections implemented: low-overlap, semantic-only, stale, superseded, duplicate, and source_count thresholds. Evidence: `.sisyphus/evidence/task-6-ranking-trace.json` shows ranked candidates with scores and rejection reasons; `.sisyphus/evidence/task-6-replay-ranking.json` confirms replay passes.

Verification commands:
- Targeted pytest: `uv run pytest mcp/tests/test_evomemory_retrieval.py mcp/tests/test_evomemory_context_bridge.py mcp/tests/test_evomemory_memory_contract.py` → 58 passed
- Full EvoMemory pytest: `uv run pytest mcp/tests/test_evomemory*.py` → 179 passed
- Replay: `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/evomemory-replay-summary.json` → 7/7 passed, expected_hit_rate=1, false_positive_injection_rate=0, unsafe_injection_count=0, cross_namespace_leakage=0

## 2026-05-12 Task 7 Capture and Promotion Behavior Closeout

Capture and promotion logic implemented: user preferences, project constraints, assistant progress/status non-promotion, duplicate reaffirmation deduplication, conflict invalidation/supersession. Evidence: `.sisyphus/evidence/task-7-capture-promotion.json` lists verified cases; `.sisyphus/evidence/task-7-replay-capture.json` confirms replay passes.

Verification commands:
- Targeted pytest: `uv run pytest mcp/tests/test_evomemory_memory_policy.py mcp/tests/test_evomemory_context_bridge.py mcp/tests/test_evomemory_package.py` → 124 passed
- Full EvoMemory pytest: `uv run pytest mcp/tests/test_evomemory*.py` → 179 passed
- Replay: `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/evomemory-replay-summary.json` → 7/7 passed, expected_hit_rate=1, false_positive_injection_rate=0, unsafe_injection_count=0, cross_namespace_leakage=0


## 2026-05-12 Task 6 Ranking Penalties and Rejections Closeout

Implemented ranking penalties and rejections: low overlap, semantic-only, stale, superseded, duplicate, source_count thresholds. Evidence: `.sisyphus/evidence/task-6-ranking-trace.json` (shows scores and rejection reasons), `.sisyphus/evidence/task-6-replay-ranking.json` (confirms replay passes with expected_hit_rate=1, false_positive_injection_rate=0, unsafe_injection_count=0, cross_namespace_leakage=0).

Verification:
- Targeted pytest: `uv run pytest mcp/tests/test_evomemory_retrieval.py mcp/tests/test_evomemory_context_bridge.py mcp/tests/test_evomemory_memory_contract.py` → 58 passed
- Full EvoMemory pytest: `uv run pytest mcp/tests/test_evomemory*.py` → 179 passed
- Replay: `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/evomemory-replay-summary.json` → 7/7 passed

## 2026-05-12 Task 7 Capture and Promotion Behavior Closeout

Capture and promotion logic implemented: user preferences, project constraints, assistant progress/status non-promotion, duplicate reaffirmation deduplication, conflict invalidation/supersession. Evidence: `.sisyphus/evidence/task-7-capture-promotion.json` (lists verified cases), `.sisyphus/evidence/task-7-replay-capture.json` (confirms replay passes with same metrics).

Verification:
- Targeted pytest: `uv run pytest mcp/tests/test_evomemory_memory_policy.py mcp/tests/test_evomemory_context_bridge.py mcp/tests/test_evomemory_package.py` → 124 passed
- Full EvoMemory pytest: `uv run pytest mcp/tests/test_evomemory*.py` → 179 passed
- Replay: same command as Task 6 → 7/7 passed


## 2026-05-12 Task 8 Retention and Maintenance Fail-Open Closeout

Implemented retention dry‑run and safe‑delete logic in `mcp/evomemory/context/retention_service.py`, wrote comprehensive test coverage in `mcp/tests/test_evomemory_maintenance_runner.py` (asserting purgeable/current/referenced drawer handling, audit events, and the rollback‑unavailable flag), and added the “compaction fails open when maintenance rejects” test in `plugins/tests/test_evomemory_opencode.mjs`. Created two evidence files:

- `.sisyphus/evidence/task-8-retention-dry-run.json`
- `.sisyphus/evidence/task-8-maintenance-fail-open.json`

Verification commands all passed:

- `uv run pytest mcp/tests/test_evomemory_maintenance_runner.py mcp/tests/test_evomemory_context_bridge.py mcp/tests/test_evomemory_mcp_server.py`
- `uv run pytest mcp/tests/test_evomemory*.py`
- `node --test plugins/tests/test_evomemory_opencode.mjs plugins/tests/test_evomemory_opencode_helpers.mjs`

No code or test modifications in this closeout step; only evidence files and notepad recording.

## 2026-05-12 Task 9 documentation and evidence closeout

- Updated README (`mcp/evomemory/adapters/opencode/README.md`) with a new "Security and runtime guardrails" section documenting bridge network binding (loopback default, `EVOMEMORY_ALLOW_REMOTE=1` for non-loopback), internal route protection (HTTP 403 for non-loopback clients, 200 for loopback), MCP tool visibility assumptions, plugin feature flags table (searchMode, preloadCoreMemory, autoFlushOnMessage, requestTimeoutMs, ensureBridgeCommand, etc.), and direct fallback behavior (bridge unavailable → no historical injection, fail-open trace).
- Created evidence file `.sisyphus/evidence/task-9-bridge-unavailable.json` capturing Node tests for bridge-unavailable fail-open (test names: "records fail-open trace when bridge is unavailable before context search", "records fail-open trace when context search times out", "prewarms evomemory bridge without blocking plugin initialization"). Command: `node --test plugins/tests/test_evomemory_bridge_manager.mjs plugins/tests/test_evomemory_opencode.mjs plugins/tests/test_evomemory_opencode_helpers.mjs`. All passed.
- Created evidence file `.sisyphus/evidence/task-9-loopback-guard.json` capturing Python MCP internal route protection tests: non-loopback client returns 403, loopback client returns 200, core call blocked on rejection. Command: `uv run pytest mcp/tests/test_evomemory_mcp_server.py`. All 36 tests passed.
- All changes are documentation and evidence only; no code or test modifications. No plan checkbox was marked.

## 2026-05-12 Task 10 closeout (truthful replay evidence and docs safety)
- Changed files for Task 10: `plugins/tests/evomemory_replay_runner.mjs`, `.sisyphus/evidence/task-10-final-replay.json`, `.sisyphus/evidence/task-10-docs-safety.txt`, `.sisyphus/notepads/optimize-evomemory-agent-learning/learnings.md`.
- Evidence paths: `.sisyphus/evidence/task-10-final-replay.json`, `.sisyphus/evidence/task-10-docs-safety.txt`, baseline source in `.sisyphus/notepads/optimize-evomemory-agent-learning/learnings.md` under `Task 1 Replay Baseline`.
- Final replay metrics from `task-10-final-replay.json`: total_cases=7, expected_hit_rate=1, false_positive_injection_rate=0, unsafe_injection_count=0, cross_namespace_leakage_count=0, injected budget=1576 chars / 396 estimated tokens. Exact latency values are intentionally read from the latest `.sisyphus/evidence/task-10-final-replay.json` rerun instead of being hardcoded here; the latest verified rerun remained below the configured latency threshold.
- Truthful baseline-vs-final comparison: Task 1 baseline stayed partial by design (`comparison.baseline_source`) and records expected_hit_rate=1, false_positive_injection_rate=0.3333, unsafe_injection_count=0, cross_namespace_leakage_count=1, injected budget=1679 chars / 421 estimated tokens; final replay improved false positives from 0.3333 to 0, cross-namespace leakage from 1 to 0, preserved hit rate at 1, preserved unsafe count at 0, and reduced injection budget to 1576 chars / 396 tokens.
- `comparison.candidate_regressions` is empty in the final replay summary.
- Threshold outcomes from `gate_evaluation`: hit rate >= 0.80 PASS, false-positive rate <= 0.10 PASS, unsafe count == 0 PASS, cross-namespace leakage == 0 PASS, added latency max <= configured threshold 5000ms PASS; `gate_evaluation.all_passed=true`.
- Docs-safety closeout: the replay evidence intentionally contains 7 synthetic `session_id` fields and 7 synthetic `directory` fields in offline fixture traces (`ses_replay_*`, `/fixtures/project-*`); these are not private runtime session IDs, not provider tokens, and not machine-specific secrets. No bearer/API-key/private-key/password-style secrets were found.
- Exact verification commands run: `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/task-10-final-replay.json` (exit 0), `node --test plugins/tests/*evomemory*.mjs` (exit 0), `uv run pytest mcp/tests/test_evomemory*.py` (182 passed).
