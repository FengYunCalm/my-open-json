from __future__ import annotations

import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mempalace_bridge_core import BridgeConfig, BridgeCore


class FakeBackend:
    def __init__(self):
        self.saved_entries = []
        self.drawer = {
            "drawer_id": "drawer_opencode_opencode-session_abc123",
            "content": "User:\nPlease add drawer navigation",
            "metadata": {
                "wing": "opencode",
                "room": "opencode-session",
                "source_file": "session:ses_demo",
                "session_id": "ses_demo",
                "message_id": "msg_001",
                "role": "user",
                "filed_at": "2026-04-13T10:00:00+00:00",
            },
        }

    def status(self):
        return {"total_drawers": 1, "palace_path": "/tmp/palace"}

    def list_wings(self):
        return {"opencode": 3}

    def list_rooms(self, wing: str | None = None):
        assert wing in (None, "opencode")
        return {"opencode-session": 3}

    def get_drawer(self, drawer_id: str):
        if drawer_id == self.drawer["drawer_id"]:
            return self.drawer
        return None

    def kg_query(self, entity: str, as_of: str | None = None, direction: str = "both"):
        return {
            "entity": entity,
            "facts": [],
            "count": 0,
            "as_of": as_of,
            "direction": direction,
        }

    def query_drawers(
        self,
        *,
        query: str | None = None,
        wing: str | None = None,
        room: str | None = None,
        session_id: str | None = None,
        role: str | None = None,
        source_file: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        assert limit >= 1
        assert offset >= 0
        rows = [
            {
                "drawer_id": "drawer_opencode_opencode-session_abc123",
                "text": "User:\nPlease add drawer navigation",
                "wing": "opencode",
                "room": "opencode-session",
                "source_file": "session:ses_demo",
                "session_id": "ses_demo",
                "message_id": "msg_001",
                "role": "user",
                "filed_at": "2026-04-13T10:00:00+00:00",
                "similarity": 0.91,
                "distance": 0.09,
            },
            {
                "drawer_id": "drawer_opencode_opencode-session_def456",
                "text": "Assistant:\nNavigation is missing because search returns no drawer_id",
                "wing": "opencode",
                "room": "opencode-session",
                "source_file": "session:ses_demo",
                "session_id": "ses_demo",
                "message_id": "msg_002",
                "role": "assistant",
                "filed_at": "2026-04-13T10:01:00+00:00",
                "similarity": 0.88,
                "distance": 0.12,
            },
            {
                "drawer_id": "drawer_opencode_opencode-session_ghi789",
                "text": "Assistant:\nAnother session result",
                "wing": "opencode",
                "room": "opencode-session",
                "source_file": "session:ses_other",
                "session_id": "ses_other",
                "message_id": "msg_003",
                "role": "assistant",
                "filed_at": "2026-04-13T10:02:00+00:00",
                "similarity": 0.75,
                "distance": 0.25,
            },
        ]

        if wing is not None:
            rows = [row for row in rows if row["wing"] == wing]
        if room is not None:
            rows = [row for row in rows if row["room"] == room]
        if session_id is not None:
            rows = [row for row in rows if row["session_id"] == session_id]
        if role is not None:
            rows = [row for row in rows if row["role"] == role]
        if source_file is not None:
            rows = [row for row in rows if row["source_file"] == source_file]
        if query is not None:
            rows = [
                row
                for row in rows
                if "drawer" in query or query.lower() in row["text"].lower()
            ]
        return rows[offset : offset + limit]

    def get_taxonomy(self):
        return {"opencode": {"opencode-session": 3}}

    def list_drawers(
        self,
        *,
        wing: str | None = None,
        room: str | None = None,
        session_id: str | None = None,
        role: str | None = None,
        source_file: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        return self.query_drawers(
            wing=wing,
            room=room,
            session_id=session_id,
            role=role,
            source_file=source_file,
            limit=limit,
            offset=offset,
        )

    def list_sessions(
        self,
        *,
        wing: str | None = None,
        room: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        rows = self.query_drawers(wing=wing, room=room, limit=50, offset=0)
        sessions = {}
        for row in rows:
            entry = sessions.setdefault(
                row["session_id"],
                {
                    "session_id": row["session_id"],
                    "wing": row["wing"],
                    "room": row["room"],
                    "message_count": 0,
                    "last_filed_at": row["filed_at"],
                },
            )
            entry["message_count"] += 1
            if row["filed_at"] > entry["last_filed_at"]:
                entry["last_filed_at"] = row["filed_at"]
        ordered = sorted(
            sessions.values(),
            key=lambda item: (item["last_filed_at"], item["session_id"]),
            reverse=True,
        )
        return ordered[offset : offset + limit]

    def get_session_messages(
        self,
        *,
        session_id: str,
        role: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        rows = self.query_drawers(session_id=session_id, role=role, limit=50, offset=0)
        rows.sort(key=lambda item: item["message_id"])
        return rows[offset : offset + limit]

    def save_entry(
        self, *, wing: str, room: str, content: str, source_file: str, metadata: dict
    ):
        payload = {
            "drawer_id": f"drawer_{metadata.get('message_id', 'missing')}",
            "wing": wing,
            "room": room,
            "source_file": source_file,
            "metadata": metadata,
            "content": content,
        }
        self.saved_entries.append(payload)
        return payload


def make_core() -> tuple[BridgeCore, FakeBackend]:
    backend = FakeBackend()
    temp_dir = Path(tempfile.mkdtemp(prefix="mempalace-bridge-test-"))
    core = BridgeCore(
        BridgeConfig(
            max_block_chars=220,
            state_path=temp_dir / "state.json",
            wing_config_path=temp_dir / "wing_config.json",
        ),
        backend=backend,
    )
    return core, backend


def test_mcp_search_returns_navigation_metadata_and_preview():
    core, _backend = make_core()

    result = core.mcp_search(
        query="drawer navigation", limit=2, wing="opencode", room="opencode-session"
    )

    assert result["results"]
    top = result["results"][0]
    assert top["drawer_id"] == "drawer_opencode_opencode-session_abc123"
    assert top["session_id"] == "ses_demo"
    assert top["message_id"] == "msg_001"
    assert top["role"] == "user"
    assert top["distance"] == 0.09
    assert top["preview"].startswith("User:")


def test_mcp_search_results_can_be_opened_with_get_drawer():
    core, _backend = make_core()

    search = core.mcp_search(
        query="drawer", limit=1, wing="opencode", room="opencode-session"
    )
    drawer = core.mcp_get_drawer(search["results"][0]["drawer_id"])

    assert drawer["metadata"]["session_id"] == "ses_demo"
    assert "drawer navigation" in drawer["content"]


def test_mcp_get_taxonomy_returns_nested_counts():
    core, _backend = make_core()

    result = core.mcp_get_taxonomy()

    assert result["taxonomy"]["opencode"]["opencode-session"] == 3


def test_mcp_list_drawers_supports_session_and_role_filters():
    core, _backend = make_core()

    result = core.mcp_list_drawers(
        wing="opencode",
        room="opencode-session",
        session_id="ses_demo",
        role="assistant",
        limit=10,
        offset=0,
    )

    assert result["count"] == 1
    assert (
        result["drawers"][0]["drawer_id"] == "drawer_opencode_opencode-session_def456"
    )
    assert result["drawers"][0]["session_id"] == "ses_demo"


def test_mcp_list_sessions_groups_messages_by_session_id():
    core, _backend = make_core()

    result = core.mcp_list_sessions(
        wing="opencode", room="opencode-session", limit=10, offset=0
    )

    assert result["count"] == 2
    assert result["sessions"][0]["session_id"] == "ses_other"
    assert result["sessions"][1]["session_id"] == "ses_demo"
    assert result["sessions"][1]["message_count"] == 2


def test_mcp_get_session_messages_returns_sorted_items():
    core, _backend = make_core()

    result = core.mcp_get_session_messages(session_id="ses_demo", limit=10, offset=0)

    assert [item["message_id"] for item in result["messages"]] == ["msg_001", "msg_002"]
    assert (
        result["messages"][0]["drawer_id"] == "drawer_opencode_opencode-session_abc123"
    )


def test_flush_session_persists_session_order_for_new_messages():
    core, backend = make_core()

    messages = [
        {
            "info": {"id": "msg_001", "role": "user"},
            "parts": [{"type": "text", "text": "Please add drawer navigation"}],
        },
        {
            "info": {"id": "msg_002", "role": "assistant"},
            "parts": [{"type": "text", "text": "I will add session browsing"}],
        },
    ]

    core.start_session("ses_demo", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_demo", "/home/mechrevo/.config/opencode", messages, reason="idle"
    )

    assert [entry["metadata"]["session_order"] for entry in backend.saved_entries] == [
        1,
        2,
    ]
