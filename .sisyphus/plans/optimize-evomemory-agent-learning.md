# Optimize EvoMemory Agent Learning

## TL;DR
> **Summary**: Build a measurable, safer, full-chain EvoMemory improvement loop so OpenCode agents can reliably reuse project/user history without turning memory into noisy prompt pollution. The plan prioritizes replay evaluation first, then retrieval/injection safety, then capture/promotion, and finally long-term maintenance.
> **Deliverables**:
> - Replay benchmark fixtures and scoring for “agent gets smarter over time”.
> - Hardened memory schema, namespace, provenance, confidence, and stale/TTL handling.
> - Safer injection contract with strict budget, source labeling, dedupe, and “memory is not instruction” isolation.
> - Improved search trigger, preload, hybrid ranking, capture, promotion, retention, bridge failure handling, and documentation.
> **Effort**: Large
> **Parallel**: YES - 2 implementation waves + final verification wave
> **Critical Path**: Task 1 → Task 2 → Tasks 3-8 → Task 10 → Final Verification

## Context
### Original Request
User wants to optimize the local `evomemory` OpenCode plugin because it does not yet feel like “the agent becomes smarter the more it is used”. User explicitly requested using GitHub to reference similar projects and learning official OpenCode docs because this is an OpenCode plugin.

### Interview Summary
- Optimization priority: cover all dimensions, ordered by importance rather than choosing only one.
- Scope: full-chain optimization across OpenCode JS plugin layer, Python MCP/bridge backend, and tests/replay harness.
- Validation preference: replay tests are the primary acceptance mechanism.
- No implementation in this planning phase.

### Research Summary
- OpenCode official docs confirm plugin hooks including `chat.message`, `chat.params`, `event`, `permission.ask`, `tool.execute.before`, `tool.execute.after`, `experimental.session.compacting`, `config`, and `tool`. `config`/`tool` hooks are initialization-time surfaces; `experimental.session.compacting` is useful but must not be the correctness-critical path.
- OpenCode MCP integration is configured in `opencode.json` under `mcp` with local/remote modes, permissions, and timeouts. MCP tools may be broadly visible unless explicitly constrained.
- Local EvoMemory code has the core change points in `plugins/evomemory-opencode.js`, `plugins/evomemory-opencode.helpers.mjs`, `plugins/evomemory-bridge-manager.mjs`, `mcp/evomemory/context/*.py`, `mcp/evomemory/domain/memory_policy.py`, `mcp/evomemory/belief/*`, `mcp/evomemory/governance/*`, `mcp/evomemory/runtime/orchestrator.py`, and existing JS/Python tests.
- GitHub/OSS patterns to borrow: mem0-style fact extraction + metadata filters + async writes; Letta-style core/recall/archival separation and controlled memory edits; LangGraph namespace/profile/collection memory; OpenMemory-style MCP boundary. Do not copy heavy architecture or enable unbounded self-editing memory.

### Metis Review (gaps addressed)
- “Smarter over time” must be measurable: replay score, expected memory hit rate, false-positive recall rate, injection token budget, p95 latency, and regression threshold.
- Memory must have namespace isolation, provenance, confidence, conflict handling, and stale/TTL policy.
- Writes must be async, bounded, idempotent, and replay-verifiable.
- Retention/revision/maintenance must be dry-run-able, auditable, and reversible.
- Every hook must specify fail-open vs fail-closed behavior.

### Oracle Review (gaps addressed)
- Replay/eval must come before subjective tuning.
- Prompt injection and wrong memory injection are higher risk than missing recall.
- `experimental.session.compacting` must stay optional/maintenance-oriented.
- Over-searching every message is a high-priority risk because it amplifies latency, noise, privacy exposure, and bad recall.
- Cross-project/user/session namespace isolation is required before aggressive recall.

## Work Objectives
### Core Objective
Make EvoMemory measurably improve agent behavior over time by safely capturing durable facts/preferences/project decisions, retrieving the right memories at the right time, injecting them with provenance and strict boundaries, and continuously validating the loop with replay tests.

### Deliverables
- Replay benchmark harness and fixtures under plugin/MCP tests.
- Memory policy changes for namespace, provenance, confidence, conflict, TTL/stale, and promotion.
- Retrieval trigger/ranking improvements with traceable reasons.
- Safer system block rendering and injection budget enforcement.
- Bridge/MCP failure handling, timeouts, feature flags, and config guardrails.
- Maintenance/revision/retention dry-run and audit improvements.
- Documentation for intended memory behavior, evaluation workflow, and rollback knobs.

### Definition of Done (verifiable conditions with commands)
- `node --test plugins/tests/*evomemory*.mjs` exits 0.
- `pytest mcp/tests/test_evomemory*.py` exits 0.
- Replay benchmark command added by Task 1 exits 0 and writes `.sisyphus/evidence/evomemory-replay-summary.json`.
- Canonical replay command after Task 1: `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/evomemory-replay-summary.json`.
- Replay metrics meet thresholds defined in Task 1: expected-memory hit rate ≥ 0.80, false-positive injection rate ≤ 0.10, prompt-injection unsafe content rate = 0, p95 search+inject added latency ≤ configured threshold, and no cross-namespace leakage.
- Bridge unavailable and MCP timeout scenarios fail open for the chat path: no unhandled exception and no blocking of user message handling.

### Must Have
- Preserve current OpenCode plugin boundaries; use supported hooks only.
- Keep memory optional historical context, never executable instruction.
- Use same-project/session/user namespace by default; cross-namespace recall must be explicitly filtered and trace-labeled.
- Every injected memory must show source/provenance, tier/scope, confidence or score, and reason summary when available.
- All schema/storage changes must be backward-compatible or include migration backup and rollback evidence.
- No raw API key/provider secret copying into docs, plans, fixtures, or evidence.

### Must NOT Have
- No rewrite of the whole memory system.
- No new heavy external service dependency unless explicitly justified by failing replay metrics.
- No unconditional transcript hoarding as long-term memory.
- No unbounded model self-editing memory.
- No reliance on `experimental.session.compacting` for correctness.
- No memory injection that can override current user/developer/system instructions.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after with replay-first baseline; add failing/guardrail tests before behavior changes inside each task.
- Frameworks: Node built-in test runner for plugin layer; pytest for Python MCP/backend.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Tasks 1-5 — replay harness, metrics/trace, schema/namespace, injection contract, trigger/preload policy. These are foundation tasks; Task 1 is the shared benchmark baseline and Task 2 provides common trace fields.

Wave 2: Tasks 6-10 — retrieval scoring, capture/extraction/promotion, maintenance/retention, bridge/config resilience, final replay/docs gate. Task 10 depends on Tasks 1-9.

### Dependency Matrix
| Task | Blocks | Blocked By |
|------|--------|------------|
| 1 Replay benchmark | 2,3,4,5,6,7,8,9,10 | None |
| 2 Observability/trace | 4,5,6,7,8,10 | 1 |
| 3 Schema/namespace | 4,5,6,7,8,10 | 1 |
| 4 Injection contract | 10 | 1,2,3 |
| 5 Trigger/preload policy | 6,10 | 1,2,3 |
| 6 Retrieval scoring | 10 | 1,2,3,5 |
| 7 Capture/extraction/promotion | 8,10 | 1,2,3 |
| 8 Maintenance/revision/retention | 10 | 1,2,3,7 |
| 9 Bridge/config resilience | 10 | 1,2 |
| 10 End-to-end replay gate/docs | Final Verification | 1,2,3,4,5,6,7,8,9 |

### Agent Dispatch Summary
| Wave | Task Count | Categories |
|------|------------|------------|
| Wave 1 | 5 | unspecified-high, deep, quick |
| Wave 2 | 5 | unspecified-high, deep, writing |
| Final | 4 | oracle, unspecified-high, deep |

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. Build replay benchmark baseline for “agent gets smarter over time”

  **What to do**: Create canonical replay runner `plugins/tests/evomemory_replay_runner.mjs` and fixture set `plugins/tests/fixtures/evomemory-replay/*.json` that can run without manual judgment. Include positive cases where prior user preference/project decision must be recalled, negative cases where no memory should be injected, prompt-injection memory cases, bridge-timeout cases, duplicate-memory cases, and cross-project leakage cases. The runner command must be `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/evomemory-replay-summary.json`. The harness must execute the plugin/backend path enough to measure capture/search/injection behavior, then write `.sisyphus/evidence/evomemory-replay-summary.json` with metrics: expected hit rate, false-positive injection rate, unsafe injection count, cross-namespace leakage count, added latency, injected character/token budget, and failed cases.
  **Must NOT do**: Do not rely on subjective “answer quality” only. Do not include real provider API keys or live private transcript content in fixtures. Do not make this depend on external network access.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: requires test harness design across JS plugin and Python backend.
  - Skills: [`agent-test-runner`] - needed to discover and integrate current Node/pytest patterns.
  - Omitted: [`webapp-testing`] - no browser UI verification required.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2,3,4,5,6,7,8,9,10 | Blocked By: None

  **References**:
  - Pattern: `plugins/tests/test_evomemory_opencode.mjs` - plugin integration tests with fake fetch/client and safety assertions.
  - Pattern: `plugins/tests/test_evomemory_opencode_helpers.mjs` - helper-level trigger/render assertions.
  - Pattern: `mcp/tests/test_evomemory_context_bridge.py` - fake backend and bridge-level test structure.
  - Pattern: `mcp/tests/test_evomemory_retrieval.py` - retrieval behavior tests.
  - API/Type: `plugins/evomemory-opencode.js:339` - exported plugin factory accepts test dependencies.
  - External: `https://github.com/mem0ai/mem0` - use the idea of measurable add/search operations with metadata filters, not the dependency.
  - External: `https://github.com/langchain-ai/langgraph` - use namespace/profile/collection replay ideas, not a runtime dependency.

  **Acceptance Criteria**:
  - [ ] `node --test plugins/tests/*evomemory*.mjs` exits 0.
  - [ ] `pytest mcp/tests/test_evomemory*.py` exits 0.
  - [ ] `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/evomemory-replay-summary.json` exists and exits 0 without network access.
  - [ ] `.sisyphus/evidence/evomemory-replay-summary.json` contains baseline metrics and individual case results.
  - [ ] Baseline thresholds are encoded in the harness but initially allow current failures to be reported without hiding them.

  **QA Scenarios**:
  ```
  Scenario: Positive memory recall replay
    Tool: Bash
    Steps: Run `node plugins/tests/evomemory_replay_runner.mjs --case positive-preference --summary .sisyphus/evidence/task-1-replay-positive.json` with a fixture containing prior preference "response_language=zh-cn" and a later task requiring a response-language decision.
    Expected: Summary JSON records expected hit=true, injected item includes provenance and namespace, unsafe_count=0.
    Evidence: .sisyphus/evidence/task-1-replay-positive.json

  Scenario: Negative no-memory replay
    Tool: Bash
    Steps: Run `node plugins/tests/evomemory_replay_runner.mjs --case negative-current-code --summary .sisyphus/evidence/task-1-replay-negative.json` with a small-talk or unrelated current-code prompt and a populated memory store.
    Expected: Summary JSON records no injected context or only safe core memory allowed by policy; false_positive=false.
    Evidence: .sisyphus/evidence/task-1-replay-negative.json
  ```

  **Commit**: NO | Message: `test(evomemory): add replay benchmark baseline` | Files: [`plugins/tests/*`, `mcp/tests/*`, optional replay fixture files]

- [x] 2. Add trace and metric spine for search, capture, injection, and maintenance

  **What to do**: Add a consistent trace object emitted by plugin/backend paths and consumed by the replay harness. Trace fields must include session_id, normalized directory/wing, namespace, trigger decision, search type, candidate counts, chosen results, injection budget used, redactions, write/capture decision, maintenance action, latency, timeout/fallback reason, and fail-open/fail-closed status. Keep trace opt-in via existing config flags or a new safe test-only config field.
  **Must NOT do**: Do not log raw secrets, raw provider config, or full private transcript text. Do not make tracing mandatory in normal chat output.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: cross-cutting instrumentation across JS and Python paths.
  - Skills: [`agent-test-runner`] - required to verify trace output in existing tests and replay harness.
  - Omitted: [`frontend-design`] - no UI work.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 4,5,6,7,8,10 | Blocked By: 1

  **References**:
  - Pattern: `plugins/evomemory-opencode.js:410` - `renderBlock` currently centralizes local system block rendering.
  - Pattern: `plugins/evomemory-opencode.js:655` - `chat.message` is the plugin path where search/persist decisions occur.
  - Pattern: `mcp/evomemory/context/query_service.py:127` - backend `search_context` builds payload and optional retrieval trace.
  - Pattern: `mcp/evomemory/context/retrieval_service.py:124` - `_reason_summary` already emits retrieval reasons.
  - Test: `plugins/tests/test_evomemory_opencode.mjs` - fake fetch tests can assert trace payload without live bridge.

  **Acceptance Criteria**:
  - [ ] Replay summary includes trace for every case.
  - [ ] Existing trace config remains default-off for normal use unless already enabled.
  - [ ] Trace redacts dangerous prompt-injection phrases and does not include secrets.
  - [ ] Bridge timeout and bridge unavailable cases record fail-open status.

  **QA Scenarios**:
  ```
  Scenario: Search trace records why memory was injected
    Tool: Bash
    Steps: Run replay case with a known project-memory match and trace enabled.
    Expected: Evidence JSON includes trigger_decision, candidate_count, selected_count, reason_summary, namespace, budget_used.
    Evidence: .sisyphus/evidence/task-2-trace-search.json

  Scenario: Trace redaction protects unsafe memory text
    Tool: Bash
    Steps: Run replay case with memory text containing "ignore previous instructions" and "reveal secrets".
    Expected: Trace and injected block contain redacted markers; unsafe_count=0.
    Evidence: .sisyphus/evidence/task-2-trace-redaction.json
  ```

  **Commit**: NO | Message: `feat(evomemory): add replay trace spine` | Files: [`plugins/evomemory-opencode.js`, `plugins/evomemory-opencode.helpers.mjs`, `mcp/evomemory/context/query_service.py`, tests]

- [x] 3. Harden memory schema, namespace, provenance, confidence, and conflict policy

  **What to do**: Define and enforce a single memory contract across JS/Python outputs: namespace = user/project/session/wing/directory; provenance = source session/message/drawer/filed_at; tier = working_session/user_preference/project_memory; confidence/source_count; valid_from/valid_to; stale/TTL/demotion fields; conflict relationship for superseded facts. Add migration or compatibility logic so existing stored rows still read safely. Long-term memory must never be promoted without namespace and provenance.
  **Must NOT do**: Do not delete existing live memory. Do not silently reinterpret old memory without marking compatibility/default fields. Do not create cross-project recall as default behavior.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: schema and migration decisions affect persistence correctness.
  - Skills: [`systematic-debugging`] - useful for migration/failure-path validation.
  - Omitted: [`refactor`] - behavior change is intentional, not pure refactor.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 4,5,6,7,8,10 | Blocked By: 1

  **References**:
  - Pattern: `mcp/evomemory/context/session_service.py:59` - capture path classifies tier, derives key/value, revises/promotes memory.
  - Pattern: `mcp/evomemory/domain/memory_policy.py:74` - current tier classification is heuristic.
  - Pattern: `mcp/evomemory/belief/service.py:29` - `belief_facts` table includes confidence and supersession fields.
  - Pattern: `mcp/evomemory/governance/service.py:31` - governance tables include score/stale/demotion fields.
  - Pattern: `mcp/evomemory/infrastructure/state/session_state.py:23` - session state table tracks session directory/wing and last saved positions.
  - Test: `mcp/tests/test_evomemory_session_state.py` - persistence/migration tests.

  **Acceptance Criteria**:
  - [ ] Existing tests pass after schema changes.
  - [ ] New tests prove long-term memory without namespace/provenance is rejected or downgraded.
  - [ ] New migration/compatibility tests prove existing records can still be read.
  - [ ] Replay cross-project leakage case records zero leaked items.

  **QA Scenarios**:
  ```
  Scenario: Namespaced project memory is eligible only in same project
    Tool: Bash
    Steps: Run replay with two directories/wings and one project_memory fact saved in only one namespace.
    Expected: Same namespace recalls the fact; different namespace does not inject it.
    Evidence: .sisyphus/evidence/task-3-namespace.json

  Scenario: Legacy memory compatibility
    Tool: Bash
    Steps: Run pytest fixture with a stored record missing new optional fields.
    Expected: Record loads with safe defaults and is not promoted/injected as high-confidence long-term memory until provenance is available.
    Evidence: .sisyphus/evidence/task-3-legacy-compat.json
  ```

  **Commit**: NO | Message: `feat(evomemory): harden memory schema and namespace policy` | Files: [`mcp/evomemory/context/*`, `mcp/evomemory/domain/memory_policy.py`, `mcp/evomemory/belief/*`, `mcp/evomemory/governance/*`, tests]

- [x] 4. Replace system block injection with a strict, source-labeled memory contract

  **What to do**: Update local system block rendering to enforce sections, max items per tier, max chars per section, duplicate removal, confidence/score ordering, source labels, reason summaries, namespace labels, and the explicit guardrail that memory is optional historical context, not instructions. Keep rejecting bridge-provided `system_block` as authoritative. Add tests for truncation, dedupe, source display, score ordering, and redaction.
  **Must NOT do**: Do not increase `maxInjectedChars` by default just to fit more memory. Do not allow memory text to contain raw role labels or hidden prompt instructions. Do not remove current local rendering safety.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: careful prompt contract work across helper rendering and replay safety.
  - Skills: [`test-driven-development`] - add focused failing tests for unsafe injection and budget before implementation.
  - Omitted: [`frontend-design`] - no visual UI.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 10 | Blocked By: 1,2,3

  **References**:
  - Pattern: `plugins/evomemory-opencode.helpers.mjs:230` - `buildSystemBlock` currently renders core/belief/governance/results and filters by score.
  - Pattern: `plugins/tests/test_evomemory_opencode.mjs:46` - existing test verifies local rendering does not trust bridge-provided `system_block`.
  - Pattern: `plugins/tests/test_evomemory_opencode_helpers.mjs` - helper test location for budget/redaction/dedupe cases.
  - External: Letta/MemGPT core memory pattern - borrow explicit core memory sections, not self-editing autonomy.

  **Acceptance Criteria**:
  - [ ] Injected block includes source/tier/scope/reason for every non-core search hit.
  - [ ] Prompt-injection phrases are redacted in both block and trace.
  - [ ] Duplicate memory items are not repeated across core/belief/governance/results sections.
  - [ ] Total injected block length never exceeds configured budget.
  - [ ] Tests prove bridge-provided `system_block` is still ignored.

  **QA Scenarios**:
  ```
  Scenario: Budgeted safe injection
    Tool: Bash
    Steps: Run helper test/replay with many high-score memory items and a small maxInjectedChars.
    Expected: Block stays within budget, preserves header, includes top-ranked sourced items only, and records truncation.
    Evidence: .sisyphus/evidence/task-4-budget.json

  Scenario: Malicious memory cannot become instruction
    Tool: Bash
    Steps: Run plugin integration test with bridge returning malicious system_block and malicious result text.
    Expected: Local block labels text as historical excerpt, redacts dangerous phrases, and does not include raw malicious system_block.
    Evidence: .sisyphus/evidence/task-4-injection-safety.json
  ```

  **Commit**: NO | Message: `fix(evomemory): enforce safe memory injection contract` | Files: [`plugins/evomemory-opencode.helpers.mjs`, `plugins/tests/*evomemory*.mjs`]

- [x] 5. Split search trigger and core-memory preload into explicit policies

  **What to do**: Replace the current near-always-search behavior with a policy that separates: always-safe core memory preload, targeted historical search, current-code prompts that should not need memory, explicit “remember/previous/decision/preference/project context” prompts, and replay-driven negative cases. Add config knobs for `searchMode` or equivalent (`off`, `core-only`, `targeted`, `aggressive-test`) and preserve current behavior only behind an explicit aggressive/test option if needed. Core memory preload must fetch only stable/user/project memory and never include arbitrary search results.
  **Must NOT do**: Do not make `experimental.session.compacting` the primary trigger. Do not block chat when search fails. Do not remove the slash-command/small-talk ignore behavior.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: user-visible behavior and latency/noise tradeoff.
  - Skills: [`test-driven-development`] - trigger policy must be pinned by examples first.
  - Omitted: [`frontend-design`] - no UI.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 6,10 | Blocked By: 1,2,3

  **References**:
  - Pattern: `plugins/evomemory-opencode.helpers.mjs:91` - `shouldSearch` currently returns true for any non-ignored text above min length.
  - Pattern: `plugins/evomemory-opencode.helpers.mjs:24` - history/project/current-code hint regexes.
  - Pattern: `plugins/evomemory-opencode.js:417` - `preloadCoreMemory` uses `/internal/context/search` with query `stable project memory user preference` and drops arbitrary results.
  - Pattern: `plugins/evomemory-opencode.js:655` - `chat.message` performs persist/search decisions.
  - Test: `plugins/tests/test_evomemory_opencode_helpers.mjs:42` - existing tests expect current-code prompts to search; update deliberately with replay-backed expectations.
  - External: mem0 metadata filters - borrow targeted retrieval with filters rather than all-message retrieval.

  **Acceptance Criteria**:
  - [ ] Tests cover at least: explicit history prompt searches, project-learning prompt searches, small talk does not search, slash command does not search, generic current-code prompt does not perform historical search unless explicitly configured.
  - [ ] Core memory preload remains enabled and bounded by stable memory only.
  - [ ] Search failure records cooldown/fail-open and does not block the chat path.
  - [ ] Replay false-positive injection rate is ≤ 0.10.

  **QA Scenarios**:
  ```
  Scenario: Targeted historical search fires for prior-decision prompt
    Tool: Bash
    Steps: Run replay case asking "what did we decide earlier about git commit behavior".
    Expected: Search executes, injects matching project/user memory with source and reason, expected_hit=true.
    Evidence: .sisyphus/evidence/task-5-targeted-search.json

  Scenario: Generic current-code prompt avoids noisy historical search
    Tool: Bash
    Steps: Run replay case asking to explain a specific current file with unrelated memory store populated.
    Expected: Historical search does not inject unrelated memory; trace records trigger_decision=no_context_search or core_only.
    Evidence: .sisyphus/evidence/task-5-negative-current-code.json
  ```

  **Commit**: NO | Message: `fix(evomemory): target memory search triggers` | Files: [`plugins/evomemory-opencode.helpers.mjs`, `plugins/evomemory-opencode.js`, `plugins/evomemory-opencode.config.json`, tests]

- [x] 6. Improve hybrid retrieval ranking and filtering with explainable thresholds

  **What to do**: Tune backend retrieval so selected memories require a meaningful combination of namespace match, tier, key/exact/keyword/semantic evidence, recency, and confidence. Add explicit penalties for stale, low-confidence, cross-scope, duplicated, and low-overlap candidates. Return ranking trace fields consumed by Task 2. Calibrate thresholds against replay fixtures rather than a single hard-coded global score.
  **Must NOT do**: Do not blindly increase semantic weight. Do not return cross-project/global hits unless policy explicitly allows them and trace explains why. Do not hide low-confidence conflicts as if they were confirmed facts.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: ranking changes need careful metric calibration and edge-case handling.
  - Skills: [`systematic-debugging`, `agent-test-runner`] - required for regression and score trace debugging.
  - Omitted: [`frontend-design`] - no UI.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 10 | Blocked By: 1,2,3,5

  **References**:
  - Pattern: `mcp/evomemory/context/retrieval_service.py:8` - tokenization and tier score constants.
  - Pattern: `mcp/evomemory/context/retrieval_service.py:145` - `_score_candidates` combines keyword/key/exact/semantic/tier/recency.
  - Pattern: `mcp/evomemory/context/retrieval_service.py:124` - `_reason_summary` emits current reason strings.
  - Pattern: `mcp/evomemory/context/query_service.py:127` - `search_context` packages results and trace.
  - Test: `mcp/tests/test_evomemory_retrieval.py` - retrieval ranking tests.
  - External: LangGraph long-term memory namespaces/profile/collection - borrow explicit namespace filtering and structured memory grouping.

  **Acceptance Criteria**:
  - [ ] Ranking tests prove exact memory key and same namespace beat vague semantic matches.
  - [ ] Stale/invalidated/conflicting memories are excluded or demoted with trace reason.
  - [ ] Replay expected-memory hit rate ≥ 0.80 while false-positive injection rate ≤ 0.10.
  - [ ] Retrieval trace includes component scores and selected/rejected reason categories.

  **QA Scenarios**:
  ```
  Scenario: Same-namespace exact key outranks vague semantic hit
    Tool: Bash
    Steps: Run pytest/replay with two candidate memories: exact same-project key and high-similarity global vague hit.
    Expected: Same-project exact key is selected; global vague hit is rejected or ranked lower with trace reason.
    Evidence: .sisyphus/evidence/task-6-ranking-exact.json

  Scenario: Stale conflicting memory is not injected
    Tool: Bash
    Steps: Run replay with a current preference and an older superseded preference.
    Expected: Only current fact is injected; stale fact appears as rejected/conflict in trace if trace enabled.
    Evidence: .sisyphus/evidence/task-6-stale-conflict.json
  ```

  **Commit**: NO | Message: `fix(evomemory): calibrate hybrid retrieval ranking` | Files: [`mcp/evomemory/context/retrieval_service.py`, `mcp/evomemory/context/query_service.py`, `mcp/tests/test_evomemory_retrieval.py`, replay fixtures]

- [x] 7. Upgrade capture, extraction, and promotion from heuristic storage to fact-quality pipeline

  **What to do**: Improve `flush_session` capture so raw working-session storage remains lightweight, while long-term user/project memory promotion requires explicit signal, derived key/value, provenance, namespace, confidence, and conflict handling. Add deterministic extraction helpers for common preference/constraint/project-decision patterns before considering any LLM-based extraction. Ensure writes are async/bounded/idempotent and duplicate long-term memories reaffirm confidence instead of creating duplicates.
  **Must NOT do**: Do not store all assistant progress/status messages as long-term facts. Do not introduce an online LLM extraction dependency in the first pass. Do not allow the model to self-edit memory without controlled tool/policy checks.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: memory quality and promotion rules are core correctness behavior.
  - Skills: [`test-driven-development`, `systematic-debugging`] - capture rules must be pinned by fixtures and edge cases.
  - Omitted: [`contract-testing-builder`] - no external provider contract here.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8,10 | Blocked By: 1,2,3

  **References**:
  - Pattern: `mcp/evomemory/context/session_service.py:59` - current flush loop classifies messages, derives memory key/value, revises/promotes.
  - Pattern: `mcp/evomemory/domain/memory_policy.py:6` - current regex-based preference/project/constraint/test patterns.
  - Pattern: `mcp/evomemory/belief/promoter.py` - promotion logic to belief/governance/evaluation.
  - Pattern: `mcp/evomemory/belief/reviser.py` - revision/conflict invalidation path.
  - Test: `mcp/tests/test_evomemory_memory_policy.py` - classification and skip tests.
  - External: mem0 fact extraction - borrow structured fact extraction and filters, not generic transcript hoarding.
  - External: Letta core/recall/archival memory - borrow tier distinction, not uncontrolled self-editing.

  **Acceptance Criteria**:
  - [ ] New tests prove explicit user preferences and project constraints promote to long-term memory with key/value/provenance/confidence.
  - [ ] New tests prove assistant status updates and low-signal messages stay working-session or are skipped.
  - [ ] Duplicate long-term facts reaffirm/increase source_count instead of duplicating drawers.
  - [ ] Conflicting facts invalidate/supersede older entries and preserve audit trail.
  - [ ] Replay capture cases show improved promotion accuracy without increasing false positives.

  **QA Scenarios**:
  ```
  Scenario: Durable preference is extracted and promoted
    Tool: Bash
    Steps: Run pytest/replay with user saying "以后默认用中文简洁回复".
    Expected: Memory key/value generated, tier=user_preference, source_session/message recorded, confidence set, replay later recalls it.
    Evidence: .sisyphus/evidence/task-7-promote-preference.json

  Scenario: Assistant progress is not promoted
    Tool: Bash
    Steps: Run replay with assistant message "我现在开始检查文件".
    Expected: Message is skipped or stored only as working_session; no long-term belief/governance asset created.
    Evidence: .sisyphus/evidence/task-7-skip-progress.json
  ```

  **Commit**: NO | Message: `feat(evomemory): improve memory capture and promotion quality` | Files: [`mcp/evomemory/context/session_service.py`, `mcp/evomemory/domain/memory_policy.py`, `mcp/evomemory/belief/*`, tests]



- [x] 8. Make maintenance, revision, and retention dry-run-able, auditable, and reversible

  **What to do**: Strengthen maintenance so revision, governance reconciliation, stale marking, demotion, and retention produce audit records before destructive changes. Ensure retention defaults to dry-run/safe behavior in tests and exposes evidence for candidate_count, purgeable_count, retained_current_ids, retained_referenced_ids, deleted_count, and rollback/backup location where applicable. Maintenance should be runnable from MCP and plugin compact/idle paths without becoming correctness-critical for chat.
  **Must NOT do**: Do not delete live memory without dry-run evidence. Do not run maintenance automatically on every chat message. Do not make compact hook a required path for memory correctness.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: operational safety across maintenance/revision/retention code.
  - Skills: [`testing-regression`] - regression coverage is important after storage lifecycle changes.
  - Omitted: [`frontend-design`] - no UI.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 10 | Blocked By: 1,2,3,7

  **References**:
  - Pattern: `mcp/evomemory/context/retention_service.py:32` - `run_retention` already has dry_run/safe/window handling.
  - Pattern: `mcp/evomemory/context/bridge.py:1664` - BridgeCore delegates search/flush/compact and MCP operations.
  - Pattern: `mcp/evomemory/governance/service.py` - governance event, stale, score, demotion storage.
  - Pattern: `plugins/evomemory-opencode.js:372` - `runMaintenance` is optional and throttled.
  - Test: `mcp/tests/test_evomemory_maintenance_runner.py` - existing maintenance tests.

  **Acceptance Criteria**:
  - [ ] Maintenance dry-run tests show no destructive changes and full candidate/action report.
  - [ ] Destructive retention requires explicit non-dry-run and safe policy evidence.
  - [ ] Maintenance audit records include action, target_kind, target_id, rationale, source_record_id, and timestamp.
  - [ ] Plugin compact/idle maintenance path remains optional, throttled, and fail-open.

  **QA Scenarios**:
  ```
  Scenario: Retention dry-run protects current and referenced memory
    Tool: Bash
    Steps: Run pytest for retention with stale, current, and belief-referenced drawers.
    Expected: Dry-run reports purgeable and retained IDs; deleted_count=0.
    Evidence: .sisyphus/evidence/task-8-retention-dry-run.json

  Scenario: Maintenance failure does not block chat
    Tool: Bash
    Steps: Run plugin test with maintenance endpoint throwing timeout/error during compact or idle path.
    Expected: Plugin logs warning/fail-open trace and chat/message processing remains successful.
    Evidence: .sisyphus/evidence/task-8-maintenance-fail-open.json
  ```

  **Commit**: NO | Message: `fix(evomemory): audit maintenance and retention lifecycle` | Files: [`mcp/evomemory/context/retention_service.py`, `mcp/evomemory/context/bridge.py`, `mcp/evomemory/governance/*`, `plugins/evomemory-opencode.js`, tests]

- [x] 9. Harden bridge, MCP, and OpenCode config guardrails

  **What to do**: Add tests and code guardrails for bridge healthcheck caching, direct fallback launch, request timeout, MCP loopback restrictions, remote MCP visibility assumptions, and fail-open behavior. Document supported OpenCode hook/MCP usage without copying sensitive provider fields from `opencode.json`. Add config feature flags for new policies and clear rollback values.
  **Must NOT do**: Do not modify provider API keys or unrelated OpenCode model/provider config. Do not bind the bridge to non-loopback by default. Do not make MCP tools globally mandatory for every agent if permissions/tools can constrain them.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: operational hardening with config/documentation awareness.
  - Skills: [`agent-test-runner`] - verify JS and Python tests after bridge/MCP guardrail changes.
  - Omitted: [`mcp-builder`] - this is hardening an existing MCP, not building a new one.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 10 | Blocked By: 1,2

  **References**:
  - Pattern: `plugins/evomemory-bridge-manager.mjs` - bridge healthcheck/startup/fallback implementation.
  - Pattern: `plugins/tests/test_evomemory_bridge_manager.mjs` - tests for health cache and fallback direct launch.
  - Pattern: `mcp/evomemory/interfaces/mcp/server.py:19` - loopback host validation helper.
  - Pattern: `mcp/evomemory/interfaces/mcp/server.py:378` - `/health` and `/internal/*` route definitions.
  - Pattern: `opencode.json` - MCP/plugin/compaction config exists; provider/API fields are sensitive and out of scope.
  - External: OpenCode docs `https://opencode.ai/docs/plugins/` and MCP docs - supported hook/config boundaries.

  **Acceptance Criteria**:
  - [ ] JS bridge manager tests cover timeout, health cache, systemctl fallback, direct fallback, and no-block plugin init.
  - [ ] Python MCP server tests cover loopback internal route rejection and allowed local requests.
  - [ ] Config documentation lists feature flags and rollback defaults without copying secrets.
  - [ ] Replay bridge-down case records fail-open and no unhandled exception.

  **QA Scenarios**:
  ```
  Scenario: Bridge unavailable does not block plugin initialization
    Tool: Bash
    Steps: Run Node bridge/plugin tests with fetch never resolving or throwing.
    Expected: Plugin factory resolves quickly; warning trace recorded; no chat-blocking exception.
    Evidence: .sisyphus/evidence/task-9-bridge-unavailable.json

  Scenario: Internal MCP routes reject non-loopback clients
    Tool: Bash
    Steps: Run pytest MCP server test simulating non-loopback request to /internal/context/search.
    Expected: Response is 403 and no core search call is executed.
    Evidence: .sisyphus/evidence/task-9-loopback-guard.json
  ```

  **Commit**: NO | Message: `chore(evomemory): harden bridge and mcp guardrails` | Files: [`plugins/evomemory-bridge-manager.mjs`, `plugins/evomemory-opencode.config.json`, `mcp/evomemory/interfaces/mcp/server.py`, tests, docs/config notes]

- [x] 10. Add end-to-end replay gate, rollout notes, and maintainer documentation

  **What to do**: Finalize a maintainer-facing document or README section explaining the memory loop: capture, tiering, search trigger, ranking, injection, maintenance, replay metrics, feature flags, rollback, and known limitations. Add final replay gate thresholds that must pass in CI/local verification. Include before/after baseline comparison from Task 1 and final metrics after Tasks 2-9.
  **Must NOT do**: Do not claim “agent is smarter” without metrics. Do not document environment-specific secrets, absolute private service tokens, or private room/session IDs. Do not add a second plan.

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: documentation plus verification summary, informed by implementation evidence.
  - Skills: [`internal-comms`, `agent-test-runner`] - concise maintainer communication and final test execution.
  - Omitted: [`frontend-design`] - no UI.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: Final Verification | Blocked By: 1,2,3,4,5,6,7,8,9

  **References**:
  - Pattern: `mcp/evomemory/README.md` - existing MCP surface documentation.
  - Pattern: `plugins/evomemory-opencode.config.json` - plugin config knobs.
  - Pattern: `pyproject.toml:29` - pytest config.
  - Pattern: `./package.json:1` - repository-root Node package/module context for OpenCode plugin tests; do not use `mcp/grep_app_mcp/package.json`.
  - Evidence: `.sisyphus/evidence/evomemory-replay-summary.json` - final replay metrics.

  **Acceptance Criteria**:
  - [ ] Final replay gate exits 0 and writes before/after comparison evidence.
  - [ ] `node --test plugins/tests/*evomemory*.mjs` exits 0.
  - [ ] `pytest mcp/tests/test_evomemory*.py` exits 0.
  - [ ] Documentation explains hook usage, MCP assumptions, feature flags, rollback, and privacy/safety guardrails.
  - [ ] Documentation avoids secrets and environment-specific sensitive values.

  **QA Scenarios**:
  ```
  Scenario: Full replay gate proves improvement
    Tool: Bash
    Steps: Run `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/task-10-final-replay.json` after all tasks complete.
    Expected: hit_rate >= 0.80, false_positive_rate <= 0.10, unsafe_count=0, cross_namespace_leakage=0, p95 latency within configured threshold.
    Evidence: .sisyphus/evidence/task-10-final-replay.json

  Scenario: Maintainer docs contain rollback and no secrets
    Tool: Bash
    Steps: Run a text scan over changed docs/config notes for API-key-like patterns and required sections.
    Expected: Required sections present; no provider token/API key/private session ID copied.
    Evidence: .sisyphus/evidence/task-10-docs-safety.txt
  ```

  **Commit**: NO | Message: `docs(evomemory): document memory learning loop and replay gates` | Files: [`mcp/evomemory/README.md`, replay evidence, tests]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [x] F1. Plan Compliance Audit — oracle

  **What to do**: Verify every implemented change maps to Tasks 1-10, every acceptance criterion has evidence, all referenced files exist, and no work outside the plan was added. Check that final replay metrics meet the defined thresholds and that F1 evidence cites exact task evidence files.
  **Recommended Agent Profile**:
  - Category: `ultrabrain` - Reason: cross-checks the full implementation against the plan and evidence.
  - Skills: [] - no extra skill required beyond plan/evidence review.
  - Omitted: [`agent-test-runner`] - this audit cites test evidence; F2/F3 execute test/QA checks.

  **Parallelization**: Can Parallel: YES | Final Verification | Blocks: completion | Blocked By: 1,2,3,4,5,6,7,8,9,10

  **Acceptance Criteria**:
  - [ ] All Tasks 1-10 have evidence files.
  - [ ] No implementation outside EvoMemory plugin/MCP/tests/docs/evidence scope is included.
  - [ ] Final replay summary meets hit_rate, false_positive_rate, unsafe_count, cross_namespace_leakage, and latency thresholds.
  **QA Scenarios**:
  ```
  Scenario: Evidence completeness audit
    Tool: Bash
    Steps: List `.sisyphus/evidence/` and compare expected task-1 through task-10 evidence names against plan acceptance criteria.
    Expected: Every task has required evidence; missing or stale evidence is reported as rejection.
    Evidence: .sisyphus/evidence/f1-plan-compliance.md
  ```
  **Evidence**: `.sisyphus/evidence/f1-plan-compliance.md`

- [x] F2. Code Quality Review — unspecified-high

  **What to do**: Review changed JS/Python for maintainability, minimality, failure paths, secret handling, namespace correctness, migration safety, and test quality. Run or cite the final Node and pytest commands.
  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: hands-on code quality, tests, and failure-path review.
  - Skills: [`agent-test-runner`] - needed to run final Node and pytest suites.
  - Omitted: [`frontend-design`] - no UI work.

  **Parallelization**: Can Parallel: YES | Final Verification | Blocks: completion | Blocked By: 1,2,3,4,5,6,7,8,9,10

  **Acceptance Criteria**:
  - [ ] `node --test plugins/tests/*evomemory*.mjs` passes.
  - [ ] `pytest mcp/tests/test_evomemory*.py` passes.
  - [ ] No secret-bearing config values are copied into docs, fixtures, traces, or evidence.
  - [ ] Bridge/MCP failures fail open for chat path.
  **QA Scenarios**:
  ```
  Scenario: Final automated test pass
    Tool: Bash
    Steps: Run `node --test plugins/tests/*evomemory*.mjs` and `pytest mcp/tests/test_evomemory*.py`; inspect changed files for secret-bearing strings.
    Expected: Both commands exit 0; no provider token/API key/private session ID is present in changed docs, fixtures, traces, or evidence.
    Evidence: .sisyphus/evidence/f2-code-quality.md
  ```
  **Evidence**: `.sisyphus/evidence/f2-code-quality.md`

- [x] F3. Real Manual QA — unspecified-high

  **What to do**: Execute the replay scenarios as real agent-facing QA: positive recall, negative no-recall, malicious memory, bridge-down, duplicate/conflict, and cross-namespace cases. This is “manual” in the sense of scenario-driven QA, but still agent-executed with commands and evidence.
  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: scenario-driven QA across replay cases and evidence interpretation.
  - Skills: [`testing-regression`] - confirms regressions across realistic scenarios.
  - Omitted: [`webapp-testing`] - no browser-level UI.

  **Parallelization**: Can Parallel: YES | Final Verification | Blocks: completion | Blocked By: 1,2,3,4,5,6,7,8,9,10

  **Acceptance Criteria**:
  - [ ] Positive recall injects the expected sourced memory.
  - [ ] Negative/current-code case avoids irrelevant historical injection.
  - [ ] Malicious memory is redacted and cannot become instruction.
  - [ ] Bridge-down case does not block chat path.
  - [ ] Cross-namespace case has zero leakage.
  **QA Scenarios**:
  ```
  Scenario: End-to-end replay QA pack
    Tool: Bash
    Steps: Run `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/f3-real-qa.md` over positive recall, negative no-recall, malicious memory, bridge-down, duplicate/conflict, and cross-namespace fixtures.
    Expected: Replay summary reports expected positive hits, no false positive current-code injection, unsafe_count=0, bridge fail-open, duplicate/conflict handled, cross_namespace_leakage=0.
    Evidence: .sisyphus/evidence/f3-real-qa.md
  ```
  **Evidence**: `.sisyphus/evidence/f3-real-qa.md`

- [x] F4. Scope Fidelity Check — deep

  **What to do**: Check that the final result still targets “agent gets smarter over time” through measurable memory behavior, not unrelated refactors. Confirm OSS/OpenCode research was used only as design guidance and did not introduce unnecessary dependencies or unsupported OpenCode hook reliance.
  **Recommended Agent Profile**:
  - Category: `deep` - Reason: verifies architectural intent, supported OpenCode boundaries, and absence of scope creep.
  - Skills: [`bmad-review-adversarial-general`] - useful for skeptical review of hidden scope creep and weak assumptions.
  - Omitted: [`refactor`] - review only; no code restructuring.

  **Parallelization**: Can Parallel: YES | Final Verification | Blocks: completion | Blocked By: 1,2,3,4,5,6,7,8,9,10

  **Acceptance Criteria**:
  - [ ] No new heavy external service dependency was added.
  - [ ] `experimental.session.compacting` is not correctness-critical.
  - [ ] Memory remains optional historical context, not a higher-priority instruction channel.
  - [ ] Documentation states limitations and rollback knobs.
  **QA Scenarios**:
  ```
  Scenario: Scope and dependency fidelity review
    Tool: Bash
    Steps: Inspect changed dependency/config/docs files and final design docs for new external services, unsupported hook reliance, and memory-as-instruction language.
    Expected: No heavy external service dependency; compacting remains optional; docs preserve memory as optional historical context and include rollback knobs.
    Evidence: .sisyphus/evidence/f4-scope-fidelity.md
  ```
  **Evidence**: `.sisyphus/evidence/f4-scope-fidelity.md`

## Commit Strategy
- Do not commit automatically. Project/user memory says git commit behavior is disabled unless explicitly requested.
- If user later requests a commit, include only EvoMemory implementation, tests, docs, and evidence relevant to this plan; exclude unrelated config secrets and unrelated workspace changes.

## Success Criteria
- The final replay suite proves a measurable improvement against the baseline while keeping prompt injection unsafe output at zero.
- OpenCode chat remains usable when EvoMemory bridge/MCP is down or slow.
- Memory retrieval is explainable: every injected item has provenance, tier/scope, reason, and budget accounting.
- Long-term memory cannot silently cross project/user/session boundaries.
- Maintenance and retention can run in dry-run mode and produce audit evidence before destructive changes.
