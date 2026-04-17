from __future__ import annotations

import json
import sys
from pathlib import Path

from starlette.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evomemory.interfaces.mcp.server import create_app


class FakeCore:
    def __init__(self):
        self.calls = []

    def health(self):
        return {"ok": True, "total_drawers": 3}

    def debug_status(self):
        return {
            "service": "evomemory-bridge",
            "state_backend": "sqlite",
            "session_count": 2,
            "drawer_count": 12,
            "current_drawer_count": 9,
            "historical_drawer_count": 3,
            "memory_tier_counts": {
                "working_session": 7,
                "user_preference": 3,
                "project_memory": 2,
            },
            "current_memory_tier_counts": {
                "working_session": 5,
                "user_preference": 2,
                "project_memory": 2,
            },
            "historical_memory_tier_counts": {
                "working_session": 2,
                "user_preference": 1,
            },
            "working_summary_count": 2,
            "current_working_summary_count": 1,
            "historical_working_summary_count": 1,
            "active_memory_key_counts": {
                "response_language": 2,
                "response_detail": 1,
                "code_change_permission": 1,
            },
            "current_memory_key_counts": {
                "response_language": 2,
                "response_detail": 1,
                "code_change_permission": 1,
            },
            "historical_memory_key_counts": {
                "response_language": 1,
            },
            "recent_active_memory_keys": [
                {
                    "memory_key": "code_change_permission",
                    "memory_tier": "project_memory",
                    "memory_value": "confirm_first",
                    "message_id": "msg_rule_3",
                },
                {
                    "memory_key": "response_detail",
                    "memory_tier": "user_preference",
                    "memory_value": "brief",
                    "message_id": "msg_rule_2",
                },
            ],
            "last_search_at": "2026-04-15T01:00:00+00:00",
            "last_flush_at": "2026-04-15T01:01:00+00:00",
            "last_compaction_at": "2026-04-15T01:02:00+00:00",
            "last_compaction_session_id": "ses_demo",
            "last_compaction_compacted_count": 3,
            "last_compaction_summary_drawer_id": "drawer_summary_ses_demo_1_3",
        }

    def start_session(self, session_id: str, directory: str):
        return {"session_id": session_id, "directory": directory, "wing": "opencode"}

    def search_context(self, query: str, directory: str, session_id: str | None = None):
        self.calls.append(
            (
                "search_context",
                {
                    "query": query,
                    "directory": directory,
                    "session_id": session_id,
                },
            )
        )
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

    def mcp_search(
        self,
        *,
        query: str,
        limit: int = 5,
        wing: str | None = None,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        room: str | None = None,
    ):
        self.calls.append(
            (
                "mcp_search",
                {
                    "query": query,
                    "limit": limit,
                    "wing": wing,
                    "memory_tier": memory_tier,
                    "current_only": current_only,
                    "historical_only": historical_only,
                    "room": room,
                },
            )
        )
        return {"query": query, "memory_tier": memory_tier, "results": []}

    def mcp_list_drawers(
        self,
        *,
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
    ):
        self.calls.append(
            (
                "mcp_list_drawers",
                {
                    "wing": wing,
                    "room": room,
                    "session_id": session_id,
                    "memory_tier": memory_tier,
                    "current_only": current_only,
                    "historical_only": historical_only,
                    "role": role,
                    "source_file": source_file,
                    "limit": limit,
                    "offset": offset,
                },
            )
        )
        return {"memory_tier": memory_tier, "drawers": []}

    def mcp_get_session_messages(
        self,
        *,
        session_id: str,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        role: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        self.calls.append(
            (
                "mcp_get_session_messages",
                {
                    "session_id": session_id,
                    "memory_tier": memory_tier,
                    "current_only": current_only,
                    "historical_only": historical_only,
                    "role": role,
                    "limit": limit,
                    "offset": offset,
                },
            )
        )
        return {"memory_tier": memory_tier, "messages": []}

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

    def evomemory_status(self):
        self.calls.append(("evomemory_status", {}))
        return {
            "service": "evomemory",
            "context": {"service": "evomemory-bridge"},
            "belief": {"plane": "belief", "fact_count": 0},
            "governance": {
                "plane": "governance",
                "gene_count": 0,
                "capsule_count": 0,
                "event_count": 0,
            },
        }

    def evomemory_query_beliefs(
        self,
        scope=None,
        key=None,
        current_only=False,
        historical_only=False,
        min_confidence=None,
        limit=10,
    ):
        self.calls.append(
            (
                "evomemory_query_beliefs",
                {
                    "scope": scope,
                    "key": key,
                    "current_only": current_only,
                    "historical_only": historical_only,
                    "min_confidence": min_confidence,
                    "limit": limit,
                },
            )
        )
        return {
            "scope": scope,
            "key": key,
            "current_only": current_only,
            "historical_only": historical_only,
            "min_confidence": min_confidence,
            "count": 0,
            "facts": [],
        }

    def evomemory_query_genes(
        self,
        scope=None,
        key=None,
        current_only=False,
        stale_only=False,
        limit=10,
    ):
        self.calls.append(
            (
                "evomemory_query_genes",
                {
                    "scope": scope,
                    "key": key,
                    "current_only": current_only,
                    "stale_only": stale_only,
                    "limit": limit,
                },
            )
        )
        return {"count": 0, "genes": []}

    def evomemory_query_capsules(
        self,
        scope=None,
        current_only=False,
        stale_only=False,
        limit=10,
    ):
        self.calls.append(
            (
                "evomemory_query_capsules",
                {
                    "scope": scope,
                    "current_only": current_only,
                    "stale_only": stale_only,
                    "limit": limit,
                },
            )
        )
        return {"count": 0, "capsules": []}

    def evomemory_record_feedback(self, target_kind, target_id, signal, note=None):
        self.calls.append(
            (
                "evomemory_record_feedback",
                {
                    "target_kind": target_kind,
                    "target_id": target_id,
                    "signal": signal,
                    "note": note,
                },
            )
        )
        return {
            "target": {
                "id": target_id,
                "kind": target_kind,
                "score": 1 if signal in {"success", "confirm"} else -1,
            },
            "delta": 1 if signal in {"success", "confirm"} else -1,
            "signal": signal,
        }

    def evomemory_list_feedback(self, target_kind=None, target_id=None, limit=20):
        self.calls.append(
            (
                "evomemory_list_feedback",
                {
                    "target_kind": target_kind,
                    "target_id": target_id,
                    "limit": limit,
                },
            )
        )
        return {"count": 0, "records": []}

    def evomemory_run_revision(self, min_confidence=0.5):
        self.calls.append(
            ("evomemory_run_revision", {"min_confidence": min_confidence})
        )
        return {"revised_count": 0, "revised_beliefs": []}

    def evomemory_export_snapshot(self, limit=20):
        self.calls.append(("evomemory_export_snapshot", {"limit": limit}))
        return {
            "service": "evomemory",
            "context": {"service": "evomemory-bridge"},
            "belief": {"count": 0, "facts": []},
            "governance": {"gene_count": 0, "capsule_count": 0, "event_count": 0},
            "evaluation": {"metrics": {}},
            "feedback": {"count": 0, "records": []},
        }

    def evomemory_run_benchmark(self, limit=20):
        self.calls.append(("evomemory_run_benchmark", {"limit": limit}))
        return {
            "score": 4,
            "checks": {
                "belief_present": True,
                "governance_present": True,
                "feedback_present": True,
                "search_enrichment_present": True,
            },
        }

    def evomemory_list_evolution_events(self, limit=20):
        self.calls.append(("evomemory_list_evolution_events", {"limit": limit}))
        return {"count": 0, "events": []}


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


def test_internal_debug_status_route_returns_runtime_metadata():
    client = TestClient(create_app(FakeCore()))

    response = client.get("/internal/debug/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["state_backend"] == "sqlite"
    assert payload["session_count"] == 2
    assert payload["last_search_at"] == "2026-04-15T01:00:00+00:00"
    assert payload["drawer_count"] == 12
    assert payload["current_memory_tier_counts"]["user_preference"] == 2
    assert payload["last_compaction_session_id"] == "ses_demo"
    assert payload["working_summary_count"] == 2
    assert payload["last_compaction_compacted_count"] == 3
    assert payload["active_memory_key_counts"]["response_language"] == 2
    assert payload["current_memory_key_counts"]["response_language"] == 2
    assert payload["historical_memory_key_counts"]["response_language"] == 1
    assert (
        payload["recent_active_memory_keys"][0]["memory_key"]
        == "code_change_permission"
    )


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
        assert "evomemory_search_drawers" in response.text
        assert "evomemory_status" in response.text


def test_mcp_tool_calls_forward_memory_tier_filters():
    core = FakeCore()
    with TestClient(create_app(core), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "evomemory_search_drawers",
                    "arguments": {
                        "query": "navigation",
                        "memory_tier": "project_memory",
                        "current_only": True,
                        "historical_only": False,
                    },
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200
        assert core.calls[0][0] == "mcp_search"
        assert core.calls[0][1]["memory_tier"] == "project_memory"
        assert core.calls[0][1]["current_only"] is True
        assert core.calls[0][1]["historical_only"] is False


def test_mcp_exposes_unified_evomemory_tools():
    core = FakeCore()
    with TestClient(create_app(core), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "evomemory_query_beliefs",
                    "arguments": {
                        "scope": "project",
                        "key": "code_change_permission",
                        "limit": 5,
                    },
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200
        assert core.calls[0][0] == "evomemory_query_beliefs"
        assert core.calls[0][1]["scope"] == "project"
        assert core.calls[0][1]["key"] == "code_change_permission"
        assert core.calls[0][1]["current_only"] is False
        assert core.calls[0][1]["historical_only"] is False
        assert core.calls[0][1]["min_confidence"] is None
        assert core.calls[0][1]["limit"] == 5


def test_mcp_exposes_evomemory_search_context_tool():
    core = FakeCore()
    with TestClient(create_app(core), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {
                    "name": "evomemory_search_context",
                    "arguments": {
                        "query": "git commit",
                        "directory": "/home/mechrevo/.config/opencode",
                        "session_id": "ses_demo",
                    },
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200
        assert core.calls[0][0] == "search_context"
        assert core.calls[0][1]["query"] == "git commit"
        assert core.calls[0][1]["directory"] == "/home/mechrevo/.config/opencode"
        assert core.calls[0][1]["session_id"] == "ses_demo"


def test_mcp_forwards_governance_filters_for_unified_queries():
    core = FakeCore()
    with TestClient(create_app(core), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {
                    "name": "evomemory_query_genes",
                    "arguments": {
                        "scope": "user",
                        "stale_only": True,
                        "limit": 5,
                    },
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200
        assert core.calls[0][0] == "evomemory_query_genes"
        assert core.calls[0][1]["scope"] == "user"
        assert core.calls[0][1]["key"] is None
        assert core.calls[0][1]["current_only"] is False
        assert core.calls[0][1]["stale_only"] is True
        assert core.calls[0][1]["limit"] == 5


def test_mcp_forwards_feedback_records_for_unified_queries():
    core = FakeCore()
    with TestClient(create_app(core), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {
                    "name": "evomemory_record_feedback",
                    "arguments": {
                        "target_kind": "gene",
                        "target_id": "gene_123",
                        "signal": "success",
                        "note": "Worked well",
                    },
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200
        assert core.calls[0][0] == "evomemory_record_feedback"
        assert core.calls[0][1]["target_kind"] == "gene"
        assert core.calls[0][1]["target_id"] == "gene_123"
        assert core.calls[0][1]["signal"] == "success"
        assert core.calls[0][1]["note"] == "Worked well"


def test_mcp_forwards_feedback_log_queries_for_unified_queries():
    core = FakeCore()
    with TestClient(create_app(core), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 12,
                "method": "tools/call",
                "params": {
                    "name": "evomemory_list_feedback",
                    "arguments": {
                        "target_kind": "capsule",
                        "target_id": "capsule_project",
                        "limit": 5,
                    },
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200
        assert core.calls[0][0] == "evomemory_list_feedback"
        assert core.calls[0][1]["target_kind"] == "capsule"
        assert core.calls[0][1]["target_id"] == "capsule_project"
        assert core.calls[0][1]["limit"] == 5


def test_mcp_forwards_belief_feedback_records_for_unified_queries():
    core = FakeCore()
    with TestClient(create_app(core), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 13,
                "method": "tools/call",
                "params": {
                    "name": "evomemory_record_feedback",
                    "arguments": {
                        "target_kind": "belief",
                        "target_id": "belief_123",
                        "signal": "confirm",
                        "note": "Belief remains valid",
                    },
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200
        assert core.calls[0][0] == "evomemory_record_feedback"
        assert core.calls[0][1]["target_kind"] == "belief"
        assert core.calls[0][1]["target_id"] == "belief_123"
        assert core.calls[0][1]["signal"] == "confirm"
        assert core.calls[0][1]["note"] == "Belief remains valid"


def test_mcp_forwards_revision_runs_for_unified_queries():
    core = FakeCore()
    with TestClient(create_app(core), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 14,
                "method": "tools/call",
                "params": {
                    "name": "evomemory_run_revision",
                    "arguments": {
                        "min_confidence": 0.5,
                    },
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200
        assert core.calls[0][0] == "evomemory_run_revision"
        assert core.calls[0][1]["min_confidence"] == 0.5


def test_mcp_forwards_snapshot_exports_for_unified_queries():
    core = FakeCore()
    with TestClient(create_app(core), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 15,
                "method": "tools/call",
                "params": {
                    "name": "evomemory_export_snapshot",
                    "arguments": {
                        "limit": 5,
                    },
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200
        assert core.calls[0][0] == "evomemory_export_snapshot"
        assert core.calls[0][1]["limit"] == 5


def test_mcp_forwards_benchmark_runs_for_unified_queries():
    core = FakeCore()
    with TestClient(create_app(core), base_url="http://127.0.0.1:8765") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 16,
                "method": "tools/call",
                "params": {
                    "name": "evomemory_run_benchmark",
                    "arguments": {
                        "limit": 5,
                    },
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

        assert response.status_code == 200
        assert core.calls[0][0] == "evomemory_run_benchmark"
        assert core.calls[0][1]["limit"] == 5
