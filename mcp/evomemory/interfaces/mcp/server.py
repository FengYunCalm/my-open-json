from __future__ import annotations

import argparse
import ipaddress
import os
from functools import partial
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse

from evomemory.context.bridge import BridgeConfig, BridgeCore


def _is_loopback_host(host: str | None) -> bool:
    if host in {None, "localhost", "testclient"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _reject_non_local_request(request: Request) -> JSONResponse | None:
    client_host = request.client.host if request.client else None
    if _is_loopback_host(client_host):
        return None
    return JSONResponse(
        {"error": "internal routes require a loopback client"}, status_code=403
    )


def _validate_bind_host(host: str) -> None:
    if _is_loopback_host(host):
        return
    if os.getenv("EVOMEMORY_ALLOW_REMOTE") == "1":
        return
    raise SystemExit(
        "Refusing to bind evomemory bridge to a non-loopback host without EVOMEMORY_ALLOW_REMOTE=1"
    )


async def _run_core_call(func, *args, **kwargs):
    return await run_in_threadpool(partial(func, *args, **kwargs))


def create_mcp_server(core: BridgeCore | Any) -> FastMCP:
    server = FastMCP("evomemory", streamable_http_path="/mcp", stateless_http=True)

    @server.tool(name="evomemory_context_status")
    def evomemory_context_status() -> dict[str, Any]:
        return core.mcp_status()

    @server.tool(name="evomemory_list_wings")
    def evomemory_list_wings() -> dict[str, Any]:
        return core.mcp_list_wings()

    @server.tool(name="evomemory_list_rooms")
    def evomemory_list_rooms(wing: str | None = None) -> dict[str, Any]:
        return core.mcp_list_rooms(wing=wing)

    @server.tool(name="evomemory_get_taxonomy")
    def evomemory_get_taxonomy() -> dict[str, Any]:
        return core.mcp_get_taxonomy()

    @server.tool(name="evomemory_get_drawer")
    def evomemory_get_drawer(drawer_id: str) -> dict[str, Any]:
        return core.mcp_get_drawer(drawer_id)

    @server.tool(name="evomemory_search_drawers")
    def evomemory_search_drawers(
        query: str,
        limit: int = 5,
        wing: str | None = None,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        room: str | None = None,
        include_trace: bool = False,
    ) -> dict[str, Any]:
        return core.mcp_search(
            query=query,
            limit=limit,
            wing=wing,
            memory_tier=memory_tier,
            current_only=current_only,
            historical_only=historical_only,
            room=room,
            include_trace=include_trace,
        )

    @server.tool(name="evomemory_list_drawers")
    def evomemory_list_drawers(
        wing: str | None = None,
        room: str | None = None,
        session_id: str | None = None,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        role: str | None = None,
        source_file: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        return core.mcp_list_drawers(
            wing=wing,
            room=room,
            session_id=session_id,
            memory_tier=memory_tier,
            current_only=current_only,
            historical_only=historical_only,
            role=role,
            source_file=source_file,
            limit=limit,
            offset=offset,
        )

    @server.tool(name="evomemory_list_sessions")
    def evomemory_list_sessions(
        wing: str | None = None,
        room: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        return core.mcp_list_sessions(wing=wing, room=room, limit=limit, offset=offset)

    @server.tool(name="evomemory_get_session_messages")
    def evomemory_get_session_messages(
        session_id: str,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        role: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        return core.mcp_get_session_messages(
            session_id=session_id,
            memory_tier=memory_tier,
            current_only=current_only,
            historical_only=historical_only,
            role=role,
            limit=limit,
            offset=offset,
        )

    @server.tool(name="evomemory_query_graph")
    def evomemory_query_graph(
        entity: str, as_of: str | None = None, direction: str = "both"
    ) -> dict[str, Any]:
        return core.mcp_kg_query(entity=entity, as_of=as_of, direction=direction)

    @server.tool(name="evomemory_status")
    def evomemory_status() -> dict[str, Any]:
        return core.evomemory_status()

    @server.tool(name="evomemory_search_context")
    def evomemory_search_context(
        query: str,
        directory: str,
        session_id: str | None = None,
        include_trace: bool = False,
    ) -> dict[str, Any]:
        return core.search_context(
            query,
            directory,
            session_id=session_id,
            include_trace=include_trace,
        )

    @server.tool(name="evomemory_query_beliefs")
    def evomemory_query_beliefs(
        scope: str | None = None,
        key: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        as_of: str | None = None,
        min_confidence: float | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        return core.evomemory_query_beliefs(
            scope=scope,
            key=key,
            current_only=current_only,
            historical_only=historical_only,
            as_of=as_of,
            min_confidence=min_confidence,
            limit=limit,
        )

    @server.tool(name="evomemory_query_timeline")
    def evomemory_query_timeline(
        key: str,
        scope: str | None = None,
        as_of: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        return core.evomemory_query_timeline(
            scope=scope,
            key=key,
            as_of=as_of,
            limit=limit,
        )

    @server.tool(name="evomemory_query_genes")
    def evomemory_query_genes(
        scope: str | None = None,
        key: str | None = None,
        current_only: bool = False,
        stale_only: bool = False,
        limit: int = 10,
    ) -> dict[str, Any]:
        return core.evomemory_query_genes(
            scope=scope,
            key=key,
            current_only=current_only,
            stale_only=stale_only,
            limit=limit,
        )

    @server.tool(name="evomemory_query_capsules")
    def evomemory_query_capsules(
        scope: str | None = None,
        current_only: bool = False,
        stale_only: bool = False,
        limit: int = 10,
    ) -> dict[str, Any]:
        return core.evomemory_query_capsules(
            scope=scope,
            current_only=current_only,
            stale_only=stale_only,
            limit=limit,
        )

    @server.tool(name="evomemory_list_evolution_events")
    def evomemory_list_evolution_events(limit: int = 20) -> dict[str, Any]:
        return core.evomemory_list_evolution_events(limit=limit)

    @server.tool(name="evomemory_evaluation_summary")
    def evomemory_evaluation_summary() -> dict[str, Any]:
        return core.evomemory_evaluation_summary()

    @server.tool(name="evomemory_list_feedback")
    def evomemory_list_feedback(
        target_kind: str | None = None,
        target_id: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        return core.evomemory_list_feedback(
            target_kind=target_kind,
            target_id=target_id,
            limit=limit,
        )

    @server.tool(name="evomemory_record_feedback")
    def evomemory_record_feedback(
        target_kind: str,
        target_id: str,
        signal: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        return core.evomemory_record_feedback(
            target_kind=target_kind,
            target_id=target_id,
            signal=signal,
            note=note,
        )

    @server.tool(name="evomemory_run_revision")
    def evomemory_run_revision(min_confidence: float = 0.5) -> dict[str, Any]:
        return core.evomemory_run_revision(min_confidence=min_confidence)

    @server.tool(name="evomemory_run_maintenance")
    def evomemory_run_maintenance(
        profile: str = "light",
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> dict[str, Any]:
        return core.evomemory_run_maintenance(
            profile=profile,
            min_confidence=min_confidence,
            limit=limit,
        )

    @server.tool(name="evomemory_reconcile_governance")
    def evomemory_reconcile_governance() -> dict[str, Any]:
        return core.evomemory_reconcile_governance()

    @server.tool(name="evomemory_maintenance_summary")
    def evomemory_maintenance_summary() -> dict[str, Any]:
        return core.maintenance_summary()

    @server.tool(name="evomemory_export_snapshot")
    def evomemory_export_snapshot(limit: int = 20) -> dict[str, Any]:
        return core.evomemory_export_snapshot(limit=limit)

    @server.tool(name="evomemory_export_archive")
    def evomemory_export_archive(limit: int = 20) -> dict[str, Any]:
        return core.evomemory_export_archive(limit=limit)

    @server.tool(name="evomemory_import_archive")
    def evomemory_import_archive(
        archive: dict[str, Any],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        return core.evomemory_import_archive(archive=archive, dry_run=dry_run)

    @server.tool(name="evomemory_run_benchmark")
    def evomemory_run_benchmark(limit: int = 20) -> dict[str, Any]:
        return core.evomemory_run_benchmark(limit=limit)

    @server.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health_route(_request: Request):
        return JSONResponse(core.health())

    @server.custom_route(
        "/internal/debug/status", methods=["GET"], include_in_schema=False
    )
    async def debug_status_route(request: Request):
        rejection = _reject_non_local_request(request)
        if rejection is not None:
            return rejection
        return JSONResponse(core.debug_status())

    @server.custom_route(
        "/internal/debug/maintenance", methods=["GET"], include_in_schema=False
    )
    async def debug_maintenance_route(request: Request):
        rejection = _reject_non_local_request(request)
        if rejection is not None:
            return rejection
        return JSONResponse(core.maintenance_summary())

    @server.custom_route(
        "/internal/session/start", methods=["POST"], include_in_schema=False
    )
    async def session_start_route(request: Request):
        rejection = _reject_non_local_request(request)
        if rejection is not None:
            return rejection
        payload = await request.json()
        return JSONResponse(
            core.start_session(payload["session_id"], payload["directory"])
        )

    @server.custom_route(
        "/internal/context/search", methods=["POST"], include_in_schema=False
    )
    async def context_search_route(request: Request):
        rejection = _reject_non_local_request(request)
        if rejection is not None:
            return rejection
        payload = await request.json()
        return JSONResponse(
            await _run_core_call(
                core.search_context,
                payload["query"],
                payload["directory"],
                session_id=payload.get("session_id"),
                include_trace=bool(payload.get("include_trace", False)),
            )
        )

    @server.custom_route(
        "/internal/session/flush", methods=["POST"], include_in_schema=False
    )
    async def session_flush_route(request: Request):
        rejection = _reject_non_local_request(request)
        if rejection is not None:
            return rejection
        payload = await request.json()
        return JSONResponse(
            await _run_core_call(
                core.flush_session,
                payload["session_id"],
                payload["directory"],
                payload.get("messages", []),
                reason=payload.get("reason", "idle"),
            )
        )

    @server.custom_route(
        "/internal/session/compact", methods=["POST"], include_in_schema=False
    )
    async def session_compact_route(request: Request):
        rejection = _reject_non_local_request(request)
        if rejection is not None:
            return rejection
        payload = await request.json()
        return JSONResponse(
            core.compact_session(
                payload["session_id"], payload["directory"], payload.get("messages", [])
            )
        )

    @server.custom_route(
        "/internal/maintenance/run", methods=["POST"], include_in_schema=False
    )
    async def maintenance_run_route(request: Request):
        rejection = _reject_non_local_request(request)
        if rejection is not None:
            return rejection
        payload = await request.json()
        return JSONResponse(
            core.evomemory_run_maintenance(
                profile=payload.get("profile", "light"),
                min_confidence=float(payload.get("min_confidence", 0.5)),
                limit=int(payload.get("limit", 20)),
            )
        )

    return server


def create_app(core: BridgeCore | Any | None = None):
    bridge_core = core or BridgeCore(BridgeConfig())
    return create_mcp_server(bridge_core).streamable_http_app()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenCode bridge for EvoMemory")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="streamable-http",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--palace-path", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.transport == "streamable-http":
        _validate_bind_host(args.host)
    config = (
        BridgeConfig(palace_path=args.palace_path)
        if args.palace_path
        else BridgeConfig()
    )
    core = BridgeCore(config)
    if args.transport == "stdio":
        create_mcp_server(core).run("stdio")
        return
    uvicorn.run(create_app(core), host=args.host, port=args.port)


if __name__ == "__main__":
    main()


__all__ = [
    "create_app",
    "create_mcp_server",
    "main",
    "parse_args",
    "_is_loopback_host",
    "_validate_bind_host",
]
