# OpenCode Integration

`evomemory` integrates with OpenCode through two extension points:

1. **MCP server** for the memory/query surface
2. **Plugin hooks** for future session-lifecycle orchestration

Phase one ships the MCP adapter and config templates, plus the `plugins/evomemory-opencode.js` runtime bridge plugin.

## Local MCP example

Examples shipped with this package:

- `opencode.mcp.local.jsonc`: let OpenCode spawn the local `evomemory` MCP server directly
- `opencode.mcp.remote.jsonc`: connect to an already-running local or remote `evomemory` MCP server

## Exposed evomemory tools

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
- `evomemory_search_context`
- `evomemory_query_beliefs`
- `evomemory_query_timeline`
- `evomemory_query_genes`
- `evomemory_query_capsules`
- `evomemory_list_evolution_events`
- `evomemory_evaluation_summary`
- `evomemory_list_feedback`
- `evomemory_record_feedback`
- `evomemory_run_revision`
- `evomemory_run_maintenance`
- `evomemory_export_snapshot`
- `evomemory_export_archive`
- `evomemory_import_archive`
- `evomemory_run_benchmark`

## Current plane coverage

- **context-plane**: session flush, search, compaction, message replay, scoped retrieval, retrieval trace
- **belief-plane**: promotion, reaffirmation, confidence, low-confidence stale sweep, point-in-time lookup, timeline view
- **governance-plane**: gene/capsule creation, score, stale state, demotion, events
- **evaluation-plane**: counters, feedback ledger, snapshot export, archive export/import, benchmark runner, unified maintenance entry

## OpenCode plugin notes

- OpenCode loads local plugins from `~/.config/opencode/plugins/` automatically.
- MCP servers are configured through `~/.config/opencode/opencode.json` under `mcp`.
- `evomemory` keeps the core memory engine in MCP; the plugin layer should stay thin and focus on lifecycle hooks and prompt orchestration.
- Canonical plugin entry:
  - `plugins/evomemory-opencode.js`
- Plugin config toggles live in:
  - `plugins/evomemory-opencode.config.json`
- New optional plugin toggles:
  - `searchIncludeTrace` / `logRetrievalTrace`: ask the bridge for retrieval trace and emit debug logs for the top-ranked candidate
  - `autoRunMaintenanceOnCompact`: run `evomemory_run_maintenance` after compaction flush
  - `maintenanceProfile`, `maintenanceMinConfidence`, `maintenanceLimit`, `maintenanceThrottleMs`: tune compaction-triggered maintenance behavior

## Security and runtime guardrails

### Bridge network binding

The evomemory MCP server binds to loopback (127.0.0.1) by default. To bind to a non-loopback address (e.g., 0.0.0.0 for remote access), set the environment variable `EVOMEMORY_ALLOW_REMOTE=1` before starting the server. Without this override, binding to a non-loopback host exits with a validation error.

### Internal route protection

All `/internal/*` routes (such as `/internal/context/search` and `/internal/session/flush`) reject requests from non-loopback clients. The server returns HTTP 403 for any request where the client IP is not 127.0.0.1. Loopback clients (127.0.0.1) are allowed and the request is forwarded to the core memory engine.

### MCP tool visibility

The MCP server exposes all memory tools (evomemory_status, evomemory_search_context, etc.) unconditionally. However, OpenCode may enforce client-side tool policies or permissions. The tools are discoverable via the standard MCP `tools/list` endpoint. The server does not filter tools based on client identity.

### Plugin feature flags and rollback defaults

The OpenCode plugin (`plugins/evomemory-opencode.js`) reads configuration from `plugins/evomemory-opencode.config.json`. Below are the current flags and their default values that control runtime behavior. Changing any flag requires restarting OpenCode to reload the plugin.

| Flag | Default | Description |
|------|---------|-------------|
| `bridgeBaseUrl` | "http://127.0.0.1:8765" | Base URL for the bridge server |
| `searchMode` | "targeted" | One of "targeted", "core-only", "aggressive-test", "off" |
| `minSearchChars` | 16 | Minimum characters to trigger historical search |
| `minPersistChars` | 8 | Minimum characters to flush a message |
| `maxInjectedChars` | 1800 | Maximum characters injected into system block |
| `minRetrievalScore` | 0.24 | Minimum similarity score to include a result |
| `safeExcerptChars` | 180 | Safe excerpt length for redacted text |
| `preloadCoreMemory` | true | Preload core memory on session start |
| `autoFlushOnMessage` | true | Flush session after each user message |
| `searchIncludeTrace` | false | Request retrieval trace from bridge |
| `logRetrievalTrace` | false | Emit debug logs for retrieval trace |
| `autoFlushOnIdle` | true | Flush session when idle |
| `autoFlushOnCompact` | true | Flush session after compaction |
| `allowLifecycleHistoryFlush` | true | Flush lifecycle history messages |
| `maxLifecycleHistoryMessages` | 40 | Max history messages kept |
| `autoRunMaintenanceOnCompact` | false | Run maintenance after compaction flush |
| `maintenanceProfile` | "light" | Maintenance profile ("light", "full") |
| `maintenanceMinConfidence` | 0.5 | Minimum confidence for maintenance |
| `maintenanceLimit` | 20 | Max items per maintenance run |
| `maintenanceThrottleMs` | 300000 | Throttle between maintenance runs (ms) |
| `requestTimeoutMs` | 5000 | Timeout for bridge HTTP requests |
| `ensureBridgeCommand` | ["bash","-lc","systemctl --user start evomemory-bridge.service"] | Command to start the bridge if missing |

### Direct fallback behavior

If the bridge is unreachable or fails health checks, the plugin proceeds without historical context injection. The session continues with core memory only, and a fail-open trace is recorded. No unhandled exceptions are thrown. The `ensureBridgeCommand` is attempted on the first request to start a missing bridge.

## Why MCP first

- OpenCode automatically exposes MCP tools to the model.
- The MCP surface is stable across OpenCode, Claude Desktop, and other MCP clients.
- Plugin hooks should stay thin and focus on lifecycle orchestration rather than implementing the memory engine itself.
