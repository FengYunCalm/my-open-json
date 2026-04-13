from __future__ import annotations

import json
import sys
from pathlib import Path

from starlette.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mempalace_bridge_server import create_app


class FakeCore:
    def health(self):
        return {"ok": True, "total_drawers": 3}

    def start_session(self, session_id: str, directory: str):
        return {"session_id": session_id, "directory": directory, "wing": "opencode"}

    def search_context(self, query: str, directory: str, session_id: str | None = None):
        return {
            "query": query,
            "directory": directory,
            "session_id": session_id,
            "wing": "opencode",
            "results": [
                {
                    "text": "Assistant:\nStored context",
                    "room": "opencode-session",
                    "role": "assistant",
                    "source_file": "session:ses_demo",
                    "similarity": 0.8,
                }
            ],
        }

    def flush_session(
        self, session_id: str, directory: str, messages: list[dict], reason: str
    ):
        return {
            "session_id": session_id,
            "saved": len(messages),
            "directory": directory,
            "reason": reason,
        }

    def compact_session(self, session_id: str, directory: str, messages: list[dict]):
        return {
            "session_id": session_id,
            "saved": len(messages),
            "directory": directory,
            "reason": "compact",
        }


def test_health_route_returns_bridge_payload():
    client = TestClient(create_app(FakeCore()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_internal_context_search_route_returns_results():
    client = TestClient(create_app(FakeCore()))

    response = client.post(
        "/internal/context/search",
        json={
            "query": "drawer navigation",
            "directory": "/home/mechrevo/.config/opencode",
            "session_id": "ses_demo",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["source_file"] == "session:ses_demo"
    assert payload["results"][0]["room"] == "opencode-session"


def test_mcp_endpoint_accepts_stale_session_header_in_stateless_mode():
    with TestClient(create_app(FakeCore()), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": "stale-session-from-before-restart",
            },
        )

        assert response.status_code == 200
        assert "Session not found" not in response.text
        assert "mempalace_search" in response.text
