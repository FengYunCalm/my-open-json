# evomemory

Phase-one package layout for the unified memory/evolution stack.

Current status:

- `evomemory.context` is the canonical context-plane implementation.
- `evomemory.belief` now supports promotion, reaffirmation, confidence, low-confidence revision, and `as_of` point-in-time lookup.
- `evomemory.governance` now persists genes, capsules, events, score, stale state, and demotions.
- `evomemory.runtime` now enriches search results with belief and governance overlays, plus optional retrieval trace output.
- `evomemory.evaluation` now tracks metrics, feedback ledgers, benchmark snapshots, and archive export readiness.
- `evomemory.interfaces.mcp.server` is now the canonical MCP server entrypoint.
- The MCP server exposes additive `evomemory_*` tools alongside the existing `mempalace_*` tools.

This phase establishes the package boundary and the canonical `evomemory_*` tool surface.

## Phase-one MCP surface

Unified evomemory tools:

- `evomemory_status`
- `evomemory_context_status`
- `evomemory_list_wings`
- `evomemory_list_rooms`
- `evomemory_get_taxonomy`
- `evomemory_get_drawer`
- `evomemory_search_drawers`
- `evomemory_list_drawers`
- `evomemory_list_sessions`
- `evomemory_get_session_messages`
- `evomemory_query_graph`
- `evomemory_query_beliefs`
- `evomemory_query_timeline`
- `evomemory_query_genes`
- `evomemory_query_capsules`
- `evomemory_list_evolution_events`
- `evomemory_evaluation_summary`
- `evomemory_search_context`
- `evomemory_list_feedback`
- `evomemory_record_feedback`
- `evomemory_run_revision`
- `evomemory_run_maintenance`
- `evomemory_export_snapshot`
- `evomemory_export_archive`
- `evomemory_import_archive`
- `evomemory_run_benchmark`

---

## Maintainer Documentation

This section is for maintainers of the EvoMemory stack. For usage, see the OpenCode integration README (`mcp/evomemory/adapters/opencode/README.md`).

### 1. Capture / flush triggers
- Messages are captured on `chat.message`; memory context is injected via `experimental.chat.system.transform`; `experimental.session.compacting` can flush recent context and optionally trigger maintenance, but it is not required for correctness.
- Automatic flush occurs on `chat.message` when `autoFlushOnMessage` is enabled, on idle timeout (`autoFlushOnIdle`), and on compaction (`autoFlushOnCompact`). `session.deleted` clears local plugin state but does not flush memory.
- Manual flush via `evomemory_run_revision` or `evomemory_export_snapshot` persists current context-plane state.

### 2. Tiering and promotion behavior
- Memory tiers: `ephemeral` (session-local), `short` (wing/room), `long` (cross-session). Default promotion from ephemeral to short based on reaffirmation frequency and confidence.
- Belief-plane promotion requires confidence >= `maintenanceMinConfidence` (default 0.5) and at least 2 reaffirmations within a rolling window.
- Governance-plane caps promotion at `maintenanceLimit` (default 20) per maintenance cycle.

### 3. Search trigger policy
- Search is triggered when `prompt_chars >= minSearchChars` (default 16) and the prompt is not flagged as a direct command or system instruction.
- Context search (`evomemory_search_context`) runs in the background with a timeout of `requestTimeoutMs` (default 5000ms). Fail-open: on timeout or bridge error, the plugin injects no memory and continues.

### 4. Ranking / rejection logic
- Retrieved drawers are ranked by: (score from `minRetrievalScore` default 0.24) * confidence (belief-plane) * recency.
- Top candidates are injected only if their rank-adjusted score exceeds the threshold.
- Rejection reasons logged when `searchIncludeTrace` or `logRetrievalTrace` is true.

### 5. Injection rules and fail‑open behavior
- Injection is limited to `maxInjectedChars` (default 1800) total, per-memory excerpt limited to `safeExcerptChars` (default 180).
- If the MCP bridge is unreachable or times out, the plugin proceeds with no memory injection (fail‑open).
- The `bridge-timeout-fail-open` replay case verifies this behavior.

### 6. Maintenance / retention / rollback posture
- Retention: `evomemory_run_retention` evaluates stale `context_drawer` retention candidates under safe/dry-run defaults, reports purgeable and retained IDs, and only performs destructive deletion on explicit non-dry-run execution.
- Rollback: EvoMemory state can be restored from JSON archives (`evomemory_export_archive` / `import_archive`). The plugin keeps no runtime rollback; use minimal config changes and test via replay.
- Regular maintenance: `autoRunMaintenanceOnCompact` can run `maintenanceProfile="light"` after compaction.

### 7. Replay metrics and required thresholds for local/CI gates
- The replay runner (`plugins/tests/evomemory_replay_runner.mjs`) enforces:
  - Hit rate >= 0.80 (recall of expected memories)
  - False‑positive injection rate <= 0.10
  - `unsafe_injection_count == 0` (no prompt‑injection leaks)
  - `cross_namespace_leakage_count == 0` (no memories cross projects)
  - Added latency per case <= `requestTimeoutMs` (default 5000ms)
- These thresholds are checked in CI via `node plugins/tests/evomemory_replay_runner.mjs && node --test`.

### 8. Feature flags and where to tune them
All plugin flags live in `plugins/evomemory-opencode.config.json`. Key flags:
- `searchMode`: `"targeted"` (default), `"core-only"`, `"aggressive-test"`, or `"off"`
- `minSearchChars`, `maxInjectedChars`, `minRetrievalScore`, `safeExcerptChars`
- `autoFlushOnMessage`, `autoFlushOnIdle`, `autoFlushOnCompact`
- `searchIncludeTrace`, `logRetrievalTrace` (debugging)
- `autoRunMaintenanceOnCompact`, `maintenanceProfile`, `maintenanceMinConfidence`, `maintenanceLimit`
- `requestTimeoutMs`, `ensureBridgeCommand`

### 9. Privacy / safety guardrails
- The runner scans injected text for `UNSAFE_PATTERNS` (API keys, bearer tokens, ignore‑instructions, etc.) and fails the case if found.
- Cross‑namespace leakage is enforced by the fixture design: each case has a distinct `session_id`, `directory`, and `wing`; the runner verifies that no memory from one case leaks into another.
- Secrets (API keys, private tokens) are **never** written to logs or evidence files. The runner fails on any occurrence.

### 10. Known limitations
- The replay runner works offline with synthetic fixtures; it does not test the real MCP bridge connectivity (the `bridge-timeout-fail-open` case simulates timeout).
- False‑positive rate above 0.10 is currently tolerated in baseline (0.3333 from Task 1); optimization targets bringing it to ≤0.10.
- Cross‑namespace leakage was 1 in baseline; must be 0 for final gates.
- Replay summaries now include Task 1 baseline comparison directly from the runner; unrecovered historical baseline fields remain intentionally omitted and documented via `comparison.baseline_source`.
- Python unit tests require `uv run pytest`; bare `pytest` is not guaranteed to work.
- `lsp_diagnostics` requires `typescript-language-server`; if missing, rely on `node --test` and build commands.
