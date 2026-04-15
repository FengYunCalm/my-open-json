from __future__ import annotations

import argparse
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from mempalace_bridge_core import BridgeConfig, BridgeCore


def create_mcp_server(core: BridgeCore | Any) -> FastMCP:
    server = FastMCP("mempalace", streamable_http_path="/mcp", stateless_http=True)

    @server.tool(name="mempalace_status")
    def mempalace_status() -> dict[str, Any]:
        return core.mcp_status()

    @server.tool(name="mempalace_list_wings")
    def mempalace_list_wings() -> dict[str, Any]:
        return core.mcp_list_wings()

    @server.tool(name="mempalace_list_rooms")
    def mempalace_list_rooms(wing: str | None = None) -> dict[str, Any]:
        return core.mcp_list_rooms(wing=wing)

    @server.tool(name="mempalace_get_taxonomy")
    def mempalace_get_taxonomy() -> dict[str, Any]:
        return core.mcp_get_taxonomy()

    @server.tool(name="mempalace_get_drawer")
    def mempalace_get_drawer(drawer_id: str) -> dict[str, Any]:
        return core.mcp_get_drawer(drawer_id)

    @server.tool(name="mempalace_search")
    def mempalace_search(
        query: str,
        limit: int = 5,
        wing: str | None = None,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        room: str | None = None,
    ) -> dict[str, Any]:
        return core.mcp_search(
            query=query,
            limit=limit,
            wing=wing,
            memory_tier=memory_tier,
            current_only=current_only,
            historical_only=historical_only,
            room=room,
        )

    @server.tool(name="mempalace_list_drawers")
    def mempalace_list_drawers(
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

    @server.tool(name="mempalace_list_sessions")
    def mempalace_list_sessions(
        wing: str | None = None,
        room: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        return core.mcp_list_sessions(wing=wing, room=room, limit=limit, offset=offset)

    @server.tool(name="mempalace_get_session_messages")
    def mempalace_get_session_messages(
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

    @server.tool(name="mempalace_kg_query")
    def mempalace_kg_query(
        entity: str, as_of: str | None = None, direction: str = "both"
    ) -> dict[str, Any]:
        return core.mcp_kg_query(entity=entity, as_of=as_of, direction=direction)

    @server.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health_route(_request: Request):
        return JSONResponse(core.health())

    @server.custom_route(
        "/internal/debug/status", methods=["GET"], include_in_schema=False
    )
    async def debug_status_route(_request: Request):
        return JSONResponse(core.debug_status())

    @server.custom_route(
        "/internal/session/start", methods=["POST"], include_in_schema=False
    )
    async def session_start_route(request: Request):
        payload = await request.json()
        return JSONResponse(
            core.start_session(payload["session_id"], payload["directory"])
        )

    @server.custom_route(
        "/internal/context/search", methods=["POST"], include_in_schema=False
    )
    async def context_search_route(request: Request):
        payload = await request.json()
        return JSONResponse(
            core.search_context(
                payload["query"],
                payload["directory"],
                session_id=payload.get("session_id"),
            )
        )

    @server.custom_route(
        "/internal/session/flush", methods=["POST"], include_in_schema=False
    )
    async def session_flush_route(request: Request):
        payload = await request.json()
        return JSONResponse(
            core.flush_session(
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
        payload = await request.json()
        return JSONResponse(
            core.compact_session(
                payload["session_id"], payload["directory"], payload.get("messages", [])
            )
        )

    return server


def create_app(core: BridgeCore | Any | None = None):
    bridge_core = core or BridgeCore(BridgeConfig())
    return create_mcp_server(bridge_core).streamable_http_app()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenCode bridge for MemPalace")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--palace-path", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = (
        BridgeConfig(palace_path=args.palace_path)
        if args.palace_path
        else BridgeConfig()
    )
    uvicorn.run(create_app(BridgeCore(config)), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
