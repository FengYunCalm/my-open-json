# evomemory

Phase-one package layout for the unified memory/evolution stack.

Current status:

- `evomemory.context` is the canonical context-plane implementation.
- `evomemory.belief` now supports promotion, reaffirmation, confidence, and low-confidence revision.
- `evomemory.governance` now persists genes, capsules, events, score, stale state, and demotions.
- `evomemory.runtime` now enriches search results with belief and governance overlays.
- `evomemory.evaluation` now tracks metrics, feedback ledgers, and benchmark snapshots.
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
- `evomemory_query_genes`
- `evomemory_query_capsules`
- `evomemory_list_evolution_events`
- `evomemory_evaluation_summary`
- `evomemory_search_context`
- `evomemory_list_feedback`
- `evomemory_record_feedback`
- `evomemory_run_revision`
- `evomemory_export_snapshot`
- `evomemory_run_benchmark`
