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

## Why MCP first

- OpenCode automatically exposes MCP tools to the model.
- The MCP surface is stable across OpenCode, Claude Desktop, and other MCP clients.
- Plugin hooks should stay thin and focus on lifecycle orchestration rather than implementing the memory engine itself.
