from __future__ import annotations

import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evomemory.context.bridge import (
    EVOMEMORY_COLLECTION_NAME,
    EVOMEMORY_PALACE_ENV,
    BridgeConfig,
    BridgeCore,
    EvoMemoryBackend,
    _resolve_palace_path,
    _resolve_wing_config_path,
)


class FakeBackend:
    def __init__(self):
        self.saved_entries = []
        self.drawer = {
            "drawer_id": "drawer_opencode_opencode-session_abc123",
            "content": "User:\nPlease add drawer navigation",
            "metadata": {
                "wing": "opencode",
                "room": "opencode-session",
                "directory": "/home/mechrevo/.config/opencode",
                "source_file": "session:ses_demo",
                "session_id": "ses_demo",
                "message_id": "msg_001",
                "role": "user",
                "memory_tier": "working_session",
                "filed_at": "2026-04-13T10:00:00+00:00",
            },
        }

    def status(self):
        return {"total_drawers": 1, "palace_path": "/tmp/palace"}

    def memory_stats(self):
        rows = self.query_drawers(limit=1000, offset=0)
        payload = {
            "drawer_count": 0,
            "current_drawer_count": 0,
            "historical_drawer_count": 0,
            "memory_tier_counts": {},
            "current_memory_tier_counts": {},
            "historical_memory_tier_counts": {},
            "working_summary_count": 0,
            "current_working_summary_count": 0,
            "historical_working_summary_count": 0,
            "active_memory_key_counts": {},
            "current_memory_key_counts": {},
            "historical_memory_key_counts": {},
            "recent_active_memory_keys": [],
        }
        recent_candidates = []
        for item in rows:
            memory_tier = item.get("memory_tier") or "unknown"
            payload["drawer_count"] += 1
            payload["memory_tier_counts"][memory_tier] = (
                payload["memory_tier_counts"].get(memory_tier, 0) + 1
            )
            if item.get("valid_to"):
                payload["historical_drawer_count"] += 1
                payload["historical_memory_tier_counts"][memory_tier] = (
                    payload["historical_memory_tier_counts"].get(memory_tier, 0) + 1
                )
                if item.get("working_summary") is True:
                    payload["historical_working_summary_count"] += 1
                memory_key = item.get("memory_key")
                if memory_key and memory_key != "working_session_summary":
                    payload["historical_memory_key_counts"][memory_key] = (
                        payload["historical_memory_key_counts"].get(memory_key, 0) + 1
                    )
            else:
                payload["current_drawer_count"] += 1
                payload["current_memory_tier_counts"][memory_tier] = (
                    payload["current_memory_tier_counts"].get(memory_tier, 0) + 1
                )
                if item.get("working_summary") is True:
                    payload["current_working_summary_count"] += 1
                memory_key = item.get("memory_key")
                if memory_key and memory_key != "working_session_summary":
                    payload["active_memory_key_counts"][memory_key] = (
                        payload["active_memory_key_counts"].get(memory_key, 0) + 1
                    )
                    payload["current_memory_key_counts"][memory_key] = (
                        payload["current_memory_key_counts"].get(memory_key, 0) + 1
                    )
                    recent_candidates.append(
                        {
                            "memory_key": memory_key,
                            "memory_tier": memory_tier,
                            "memory_value": item.get("memory_value"),
                            "message_id": item.get("message_id"),
                            "session_id": item.get("session_id"),
                            "valid_from": item.get("valid_from"),
                            "filed_at": item.get("filed_at"),
                        }
                    )
            if item.get("working_summary") is True:
                payload["working_summary_count"] += 1
        seen_keys = set()
        for item in sorted(
            recent_candidates,
            key=lambda row: (
                row.get("valid_from") or row.get("filed_at") or "",
                row.get("message_id") or "",
            ),
            reverse=True,
        ):
            key = item.get("memory_key")
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            payload["recent_active_memory_keys"].append(item)
        return payload

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
        directory: str | None = None,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
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
                "directory": "/home/mechrevo/.config/opencode",
                "source_file": "session:ses_demo",
                "session_id": "ses_demo",
                "message_id": "msg_001",
                "role": "user",
                "memory_tier": "working_session",
                "memory_value": None,
                "filed_at": "2026-04-13T10:00:00+00:00",
                "similarity": 0.91,
                "distance": 0.09,
            },
            {
                "drawer_id": "drawer_opencode_opencode-session_def456",
                "text": "Assistant:\nNavigation is missing because search returns no drawer_id",
                "wing": "opencode",
                "room": "opencode-session",
                "directory": "/home/mechrevo/.config/opencode",
                "source_file": "session:ses_demo",
                "session_id": "ses_demo",
                "message_id": "msg_002",
                "role": "assistant",
                "memory_tier": "working_session",
                "memory_value": None,
                "filed_at": "2026-04-13T10:01:00+00:00",
                "similarity": 0.88,
                "distance": 0.12,
            },
            {
                "drawer_id": "drawer_opencode_opencode-session_ghi789",
                "text": "Assistant:\nSame wing navigation result from another directory",
                "wing": "opencode",
                "room": "opencode-session",
                "directory": "/home/mechrevo/projects/other",
                "source_file": "session:ses_other",
                "session_id": "ses_other",
                "message_id": "msg_003",
                "role": "assistant",
                "memory_tier": "working_session",
                "memory_value": None,
                "filed_at": "2026-04-13T10:02:00+00:00",
                "similarity": 0.75,
                "distance": 0.25,
            },
            {
                "drawer_id": "drawer_opencode_opencode-session_jkl111",
                "text": "Assistant:\nSame directory navigation result from another session",
                "wing": "opencode",
                "room": "opencode-session",
                "directory": "/home/mechrevo/.config/opencode",
                "source_file": "session:ses_peer",
                "session_id": "ses_peer",
                "message_id": "msg_004",
                "role": "assistant",
                "memory_tier": "working_session",
                "memory_value": None,
                "filed_at": "2026-04-13T10:03:00+00:00",
                "similarity": 0.86,
                "distance": 0.14,
            },
            {
                "drawer_id": "drawer_global_memory_mno222",
                "text": "Assistant:\nGlobal navigation result from another wing",
                "wing": "global-memory",
                "room": "cross-project",
                "directory": "/home/mechrevo/shared",
                "source_file": "session:ses_global",
                "session_id": "ses_global",
                "message_id": "msg_005",
                "role": "assistant",
                "memory_tier": "project_memory",
                "memory_key": "test_execution_behavior",
                "memory_value": "required",
                "valid_from": "2026-04-13T10:04:00+00:00",
                "filed_at": "2026-04-13T10:04:00+00:00",
                "similarity": 0.7,
                "distance": 0.3,
            },
            {
                "drawer_id": "drawer_preference_lang_xyz999",
                "text": "User:\n以后都用中文回复，默认简洁一点",
                "wing": "opencode",
                "room": "preferences",
                "directory": "/home/mechrevo/preferences-fixture",
                "source_file": "session:ses_pref_fixture",
                "session_id": "ses_pref_fixture",
                "message_id": "msg_006",
                "role": "user",
                "memory_tier": "user_preference",
                "memory_key": "response_language",
                "memory_value": "zh-cn",
                "valid_from": "2026-04-13T10:05:00+00:00",
                "filed_at": "2026-04-13T10:05:00+00:00",
                "similarity": 0.6,
                "distance": 0.4,
            },
        ]

        rows.extend(
            {
                "drawer_id": item["drawer_id"],
                "text": item["content"],
                "wing": item["wing"],
                "room": item["room"],
                "directory": item["metadata"].get("directory"),
                "source_file": item["source_file"],
                "session_id": item["metadata"].get("session_id"),
                "message_id": item["metadata"].get("message_id"),
                "role": item["metadata"].get("role"),
                "memory_tier": item["metadata"].get("memory_tier"),
                "memory_key": item["metadata"].get("memory_key"),
                "memory_value": item["metadata"].get("memory_value"),
                "dedupe_hash": item["metadata"].get("dedupe_hash"),
                "valid_from": item["metadata"].get("valid_from"),
                "valid_to": item["metadata"].get("valid_to"),
                "working_summary": item["metadata"].get("working_summary") is True,
                "filed_at": item["metadata"].get("filed_at"),
                "similarity": 0.95,
                "distance": 0.05,
            }
            for item in self.saved_entries
        )

        if wing is not None:
            rows = [row for row in rows if row["wing"] == wing]
        if directory is not None:
            rows = [row for row in rows if row["directory"] == directory]
        if memory_tier is not None:
            rows = [row for row in rows if row["memory_tier"] == memory_tier]
        if current_only:
            rows = [row for row in rows if not row.get("valid_to")]
        elif historical_only:
            rows = [row for row in rows if row.get("valid_to")]
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
        rows = self.query_drawers(limit=1000, offset=0)
        taxonomy = {}
        taxonomy_by_memory_tier = {}
        taxonomy_by_memory_key = {}
        for row in rows:
            wing = row.get("wing") or "unknown"
            room = row.get("room") or "unknown"
            memory_tier = row.get("memory_tier") or "unknown"
            taxonomy.setdefault(wing, {})
            taxonomy[wing][room] = taxonomy[wing].get(room, 0) + 1
            taxonomy_by_memory_tier.setdefault(memory_tier, {})
            taxonomy_by_memory_tier[memory_tier].setdefault(wing, {})
            taxonomy_by_memory_tier[memory_tier][wing][room] = (
                taxonomy_by_memory_tier[memory_tier][wing].get(room, 0) + 1
            )
            memory_key = row.get("memory_key")
            if memory_key:
                taxonomy_by_memory_key.setdefault(memory_key, {})
                taxonomy_by_memory_key[memory_key].setdefault(wing, {})
                taxonomy_by_memory_key[memory_key][wing][room] = (
                    taxonomy_by_memory_key[memory_key][wing].get(room, 0) + 1
                )
        return {
            "taxonomy": taxonomy,
            "taxonomy_by_memory_tier": taxonomy_by_memory_tier,
            "taxonomy_by_memory_key": taxonomy_by_memory_key,
        }

    def list_drawers(
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
        return self.query_drawers(
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
                    "current_message_count": 0,
                    "historical_message_count": 0,
                    "memory_tier_counts": {},
                    "current_memory_tier_counts": {},
                    "historical_memory_tier_counts": {},
                    "last_filed_at": row["filed_at"],
                },
            )
            entry["message_count"] += 1
            memory_tier = row.get("memory_tier") or "unknown"
            entry["memory_tier_counts"][memory_tier] = (
                entry["memory_tier_counts"].get(memory_tier, 0) + 1
            )
            if row.get("valid_to"):
                entry["historical_message_count"] += 1
                entry["historical_memory_tier_counts"][memory_tier] = (
                    entry["historical_memory_tier_counts"].get(memory_tier, 0) + 1
                )
            else:
                entry["current_message_count"] += 1
                entry["current_memory_tier_counts"][memory_tier] = (
                    entry["current_memory_tier_counts"].get(memory_tier, 0) + 1
                )
            if row["filed_at"] and (
                entry["last_filed_at"] is None
                or row["filed_at"] > entry["last_filed_at"]
            ):
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
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        role: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        rows = self.query_drawers(
            session_id=session_id,
            memory_tier=memory_tier,
            current_only=current_only,
            historical_only=historical_only,
            role=role,
            limit=50,
            offset=0,
        )
        rows.sort(key=lambda item: item["message_id"])
        return rows[offset : offset + limit]

    def save_entry(
        self, *, wing: str, room: str, content: str, source_file: str, metadata: dict
    ):
        metadata = {
            **metadata,
            "filed_at": metadata.get("filed_at") or "2026-04-15T00:00:00+00:00",
        }
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

    def invalidate_memory_conflicts(
        self,
        *,
        wing: str,
        directory: str,
        memory_tier: str,
        memory_key: str,
        valid_to: str,
    ) -> int:
        invalidated = 0
        for entry in self.saved_entries:
            metadata = entry["metadata"]
            if entry.get("wing") != wing:
                continue
            if metadata.get("directory") != directory:
                continue
            if metadata.get("memory_tier") != memory_tier:
                continue
            if metadata.get("memory_key") != memory_key:
                continue
            if metadata.get("valid_to"):
                continue
            metadata["valid_to"] = valid_to
            invalidated += 1
        return invalidated

    def invalidate_drawers(self, *, drawer_ids: list[str], valid_to: str) -> int:
        invalidated = 0
        drawer_id_set = set(drawer_ids)
        for entry in self.saved_entries:
            if entry["drawer_id"] not in drawer_id_set:
                continue
            metadata = entry["metadata"]
            if metadata.get("valid_to"):
                continue
            metadata["valid_to"] = valid_to
            invalidated += 1
        return invalidated


def make_core(**config_overrides) -> tuple[BridgeCore, FakeBackend]:
    backend = FakeBackend()
    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-bridge-test-"))
    core = BridgeCore(
        BridgeConfig(
            max_block_chars=700,
            state_path=temp_dir / "state.json",
            wing_config_path=temp_dir / "wing_config.json",
            **config_overrides,
        ),
        backend=backend,
    )
    return core, backend


def test_bridge_config_keeps_evomemory_state_path_without_legacy_migration():
    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-state-migrate-"))
    evomemory_state_path = temp_dir / "evomemory_bridge_state.sqlite3"

    config = BridgeConfig(state_path=evomemory_state_path)

    assert config.state_path == evomemory_state_path
    assert evomemory_state_path.exists() is False


def test_resolve_palace_path_prefers_evomemory_env():
    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-palace-env-"))
    env = {
        EVOMEMORY_PALACE_ENV: str(temp_dir / "custom" / "evomemory-palace"),
    }

    resolved = _resolve_palace_path(None, env=env, home=temp_dir)

    assert resolved == temp_dir / "custom" / "evomemory-palace"


def test_resolve_palace_path_defaults_to_evomemory_home():
    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-palace-migrate-"))

    resolved = _resolve_palace_path(None, env={}, home=temp_dir)

    assert resolved == temp_dir / ".evomemory" / "palace"
    assert resolved.exists() is False


def test_resolve_wing_config_path_defaults_to_evomemory_home():
    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-wing-config-"))

    resolved = _resolve_wing_config_path(
        temp_dir / ".evomemory" / "wing_config.json",
        home=temp_dir,
    )

    assert resolved == temp_dir / ".evomemory" / "wing_config.json"
    assert resolved.exists() is False


def test_backend_uses_evomemory_collection_name_without_legacy_migration():
    class FakeCollection:
        def __init__(self, name, rows=None):
            self.name = name
            self.rows = list(rows or [])

        def count(self):
            return len(self.rows)

        def get(self, *, include, limit=None, offset=0, ids=None, where=None):
            if ids is not None:
                selected = [row for row in self.rows if row["id"] in ids]
            else:
                end = None if limit is None else offset + limit
                selected = self.rows[offset:end]
            return {
                "ids": [row["id"] for row in selected],
                "documents": [row["document"] for row in selected],
                "metadatas": [row["metadata"] for row in selected],
            }

        def upsert(self, *, ids, documents, metadatas):
            existing = {row["id"]: row for row in self.rows}
            for drawer_id, document, metadata in zip(ids, documents, metadatas):
                existing[drawer_id] = {
                    "id": drawer_id,
                    "document": document,
                    "metadata": metadata,
                }
            self.rows = list(existing.values())

    class FakeClient:
        def __init__(self):
            self.collections = {}

        def get_collection(self, name):
            if name not in self.collections:
                raise ValueError(name)
            return self.collections[name]

        def get_or_create_collection(self, name):
            if name not in self.collections:
                self.collections[name] = FakeCollection(name)
            return self.collections[name]

    backend = object.__new__(EvoMemoryBackend)
    backend._client = FakeClient()
    backend._collection = None
    backend.collection_name = EVOMEMORY_COLLECTION_NAME

    collection = EvoMemoryBackend._collection_for(backend, create=True)

    assert collection.name == EVOMEMORY_COLLECTION_NAME
    assert collection.count() == 0


def test_flush_session_skips_low_signal_control_messages():
    core, backend = make_core()

    core.start_session("ses_skip", "/home/mechrevo/.config/opencode")
    result = core.flush_session(
        "ses_skip",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_skip_1", "role": "user"},
                "parts": [{"type": "text", "text": "继续"}],
            },
            {
                "info": {"id": "msg_skip_2", "role": "assistant"},
                "parts": [{"type": "text", "text": "我先看一下"}],
            },
        ],
        reason="idle",
    )

    assert result["saved"] == 0
    assert backend.saved_entries == []


def test_flush_session_skips_long_assistant_progress_updates():
    core, backend = make_core()

    core.start_session("ses_skip_long_progress", "/home/mechrevo/.config/opencode")
    result = core.flush_session(
        "ses_skip_long_progress",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_skip_long_progress", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "我会先检查 bridge 和 state store 的差异，再对一下当前会话的连接链路。",
                    }
                ],
            }
        ],
        reason="idle",
    )

    assert result["saved"] == 0
    assert backend.saved_entries == []


def test_flush_session_keeps_substantive_assistant_analysis_as_working_session():
    core, backend = make_core()

    core.start_session("ses_assistant_analysis", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_assistant_analysis",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_assistant_analysis", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "我检查了 bridge 和 state store，根因是 stdio 与 HTTP 双链路同时写同一套状态文件，导致当前会话和后台 bridge 的视图不一致。",
                    }
                ],
            }
        ],
        reason="idle",
    )

    assert backend.saved_entries[0]["metadata"]["memory_tier"] == "working_session"


def test_build_working_session_summary_content_flattens_previous_summaries():
    core, _backend = make_core()

    content = core._build_working_session_summary_content(
        [
            {
                "message_id": "summary_old",
                "text": "Working session summary:\n- bridge 健康检查返回 200\n- state store 快照不一致",
                "working_summary": True,
                "metadata": {"session_order": 1},
            },
            {
                "message_id": "msg_analysis",
                "text": "Assistant:\n最终结论是当前会话还连着旧 stdio MCP，所以需要统一到 HTTP bridge。",
                "working_summary": False,
                "metadata": {"session_order": 2},
            },
        ]
    )

    assert content.count("Working session summary:") == 1
    assert "- Working session summary:" not in content
    assert "- bridge 健康检查返回 200" in content
    assert "- state store 快照不一致" in content
    assert (
        "- Assistant: 最终结论是当前会话还连着旧 stdio MCP，所以需要统一到 HTTP bridge。"
        in content
    )


def test_backend_format_row_surfaces_memory_metadata():
    backend = EvoMemoryBackend.__new__(EvoMemoryBackend)

    row = EvoMemoryBackend._format_row(
        backend,
        drawer_id="drawer_test",
        text="Assistant:\nsummary",
        metadata={
            "wing": "opencode",
            "room": "opencode-session",
            "source_file": "session:ses_demo",
            "session_id": "ses_demo",
            "message_id": "msg_demo",
            "role": "assistant",
            "memory_tier": "working_session",
            "memory_key": "working_session_summary",
            "memory_value": "ses_demo",
            "valid_from": "2026-04-17T00:00:00+00:00",
            "valid_to": "2026-04-17T01:00:00+00:00",
            "working_summary": True,
            "filed_at": "2026-04-17T00:00:00+00:00",
        },
    )

    assert row["memory_key"] == "working_session_summary"
    assert row["memory_value"] == "ses_demo"
    assert row["valid_from"] == "2026-04-17T00:00:00+00:00"
    assert row["valid_to"] == "2026-04-17T01:00:00+00:00"
    assert row["working_summary"] is True


def test_flush_session_does_not_promote_assistant_constraint_summary_to_project_memory():
    core, backend = make_core()

    core.start_session("ses_assistant_summary", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_assistant_summary",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_assistant_summary", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "这个项目里不要自动提交 git commit，未经确认不要修改代码，修改后都要跑测试。",
                    }
                ],
            }
        ],
        reason="idle",
    )

    assert backend.saved_entries[0]["metadata"]["memory_tier"] == "working_session"
    assert backend.saved_entries[0]["metadata"].get("memory_key") is None


def test_backend_save_entry_omits_none_metadata_values():
    class CaptureCollection:
        def __init__(self):
            self.metadatas = []

        def upsert(self, *, ids, documents, metadatas):
            self.metadatas = metadatas

    collection = CaptureCollection()
    backend = object.__new__(EvoMemoryBackend)
    backend._collection = collection

    result = EvoMemoryBackend.save_entry(
        backend,
        wing="opencode",
        room="opencode-session",
        content="User:\nPlease remember this",
        source_file="session:ses_demo",
        metadata={
            "session_id": "ses_demo",
            "message_id": "msg_none",
            "memory_key": None,
            "memory_value": None,
            "dedupe_hash": None,
            "valid_to": None,
        },
    )

    saved = collection.metadatas[0]
    assert result["metadata"] == saved
    assert saved["session_id"] == "ses_demo"
    assert saved["message_id"] == "msg_none"
    assert "memory_key" not in saved
    assert "memory_value" not in saved
    assert "dedupe_hash" not in saved
    assert "valid_to" not in saved


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
    assert top["memory_tier"] == "working_session"
    assert top["distance"] == 0.09
    assert top["preview"].startswith("User:")


def test_mcp_search_supports_memory_tier_filter():
    core, _backend = make_core()

    result = core.mcp_search(query="navigation", limit=10, memory_tier="project_memory")

    assert [item["drawer_id"] for item in result["results"]] == [
        "drawer_global_memory_mno222"
    ]
    assert result["results"][0]["memory_tier"] == "project_memory"


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

    assert result["taxonomy"]["opencode"]["opencode-session"] == 4
    assert (
        result["taxonomy_by_memory_tier"]["working_session"]["opencode"][
            "opencode-session"
        ]
        == 4
    )
    assert (
        result["taxonomy_by_memory_tier"]["user_preference"]["opencode"]["preferences"]
        == 1
    )
    assert (
        result["taxonomy_by_memory_tier"]["project_memory"]["global-memory"][
            "cross-project"
        ]
        == 1
    )
    assert (
        result["taxonomy_by_memory_key"]["response_language"]["opencode"]["preferences"]
        == 1
    )
    assert (
        result["taxonomy_by_memory_key"]["test_execution_behavior"]["global-memory"][
            "cross-project"
        ]
        == 1
    )


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


def test_mcp_list_drawers_supports_memory_tier_filter():
    core, _backend = make_core()

    result = core.mcp_list_drawers(memory_tier="user_preference", limit=10, offset=0)

    assert result["count"] == 1
    assert result["drawers"][0]["drawer_id"] == "drawer_preference_lang_xyz999"
    assert result["drawers"][0]["memory_tier"] == "user_preference"


def test_mcp_list_sessions_groups_messages_by_session_id():
    core, _backend = make_core()

    result = core.mcp_list_sessions(
        wing="opencode", room="opencode-session", limit=10, offset=0
    )

    assert result["count"] == 3
    assert result["sessions"][0]["session_id"] == "ses_peer"
    assert result["sessions"][1]["session_id"] == "ses_other"
    assert result["sessions"][2]["session_id"] == "ses_demo"
    assert result["sessions"][2]["message_count"] == 2
    assert result["sessions"][2]["current_message_count"] == 2
    assert result["sessions"][2]["historical_message_count"] == 0
    assert result["sessions"][2]["memory_tier_counts"] == {"working_session": 2}
    assert result["sessions"][2]["current_memory_tier_counts"] == {"working_session": 2}
    assert result["sessions"][2]["historical_memory_tier_counts"] == {}


def test_mcp_list_sessions_includes_current_and_historical_counts():
    core, _backend = make_core()

    core.start_session("ses_pref_stats", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_pref_stats",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_stats_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_pref_stats",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_stats_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_pref_stats_2", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用英文回复"}],
            },
        ],
        reason="idle",
    )

    result = core.mcp_list_sessions(limit=20, offset=0)
    target = next(
        item for item in result["sessions"] if item["session_id"] == "ses_pref_stats"
    )

    assert target["message_count"] == 2
    assert target["current_message_count"] == 1
    assert target["historical_message_count"] == 1
    assert target["memory_tier_counts"] == {"user_preference": 2}
    assert target["current_memory_tier_counts"] == {"user_preference": 1}
    assert target["historical_memory_tier_counts"] == {"user_preference": 1}


def test_mcp_get_session_messages_returns_sorted_items():
    core, _backend = make_core()

    result = core.mcp_get_session_messages(session_id="ses_demo", limit=10, offset=0)

    assert [item["message_id"] for item in result["messages"]] == ["msg_001", "msg_002"]
    assert (
        result["messages"][0]["drawer_id"] == "drawer_opencode_opencode-session_abc123"
    )
    assert result["messages"][0]["memory_tier"] == "working_session"


def test_mcp_get_session_messages_supports_memory_tier_filter():
    core, _backend = make_core()

    result = core.mcp_get_session_messages(
        session_id="ses_pref_fixture", memory_tier="user_preference", limit=10, offset=0
    )

    assert result["count"] == 1
    assert result["messages"][0]["drawer_id"] == "drawer_preference_lang_xyz999"
    assert result["messages"][0]["memory_tier"] == "user_preference"


def test_flush_session_persists_session_order_for_new_messages():
    core, backend = make_core()

    messages = [
        {
            "info": {"id": "msg_001", "role": "user"},
            "parts": [{"type": "text", "text": "Please add drawer navigation"}],
        },
        {
            "info": {"id": "msg_002", "role": "assistant"},
            "parts": [
                {
                    "type": "text",
                    "text": "The missing drawer navigation comes from search results that do not carry drawer_id metadata.",
                }
            ],
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
    assert [entry["metadata"]["memory_tier"] for entry in backend.saved_entries] == [
        "working_session",
        "working_session",
    ]


def test_flush_session_marks_user_preferences_as_user_preference_tier():
    core, backend = make_core()

    messages = [
        {
            "info": {"id": "msg_pref", "role": "user"},
            "parts": [{"type": "text", "text": "以后都用中文回复，默认简洁一点"}],
        },
    ]

    core.start_session("ses_pref", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_pref", "/home/mechrevo/.config/opencode", messages, reason="idle"
    )

    assert backend.saved_entries[0]["metadata"]["memory_tier"] == "user_preference"


def test_flush_session_marks_response_detail_preference_with_structured_key():
    core, backend = make_core()

    messages = [
        {
            "info": {"id": "msg_detail", "role": "user"},
            "parts": [{"type": "text", "text": "默认详细一点"}],
        },
    ]

    core.start_session("ses_detail", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_detail", "/home/mechrevo/.config/opencode", messages, reason="idle"
    )

    assert backend.saved_entries[0]["metadata"]["memory_key"] == "response_detail"
    assert backend.saved_entries[0]["metadata"]["memory_value"] == "detailed"


def test_flush_session_marks_test_execution_behavior_with_structured_key():
    core, backend = make_core()

    messages = [
        {
            "info": {"id": "msg_test_rule", "role": "user"},
            "parts": [{"type": "text", "text": "这个项目里每次修改后都要跑测试"}],
        },
    ]

    core.start_session("ses_test_rule", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_test_rule", "/home/mechrevo/.config/opencode", messages, reason="idle"
    )

    assert backend.saved_entries[0]["metadata"]["memory_tier"] == "project_memory"
    assert (
        backend.saved_entries[0]["metadata"]["memory_key"] == "test_execution_behavior"
    )
    assert backend.saved_entries[0]["metadata"]["memory_value"] == "required"


def test_flush_session_marks_code_change_permission_with_structured_key():
    core, backend = make_core()

    messages = [
        {
            "info": {"id": "msg_code_permission", "role": "user"},
            "parts": [{"type": "text", "text": "未经确认，不要修改代码"}],
        },
    ]

    core.start_session("ses_code_permission", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_code_permission",
        "/home/mechrevo/.config/opencode",
        messages,
        reason="idle",
    )

    assert backend.saved_entries[0]["metadata"]["memory_tier"] == "project_memory"
    assert (
        backend.saved_entries[0]["metadata"]["memory_key"] == "code_change_permission"
    )
    assert backend.saved_entries[0]["metadata"]["memory_value"] == "confirm_first"


def test_flush_session_marks_implementation_mode_preference_with_structured_key():
    core, backend = make_core()

    messages = [
        {
            "info": {"id": "msg_impl_mode", "role": "user"},
            "parts": [{"type": "text", "text": "如果只是分析问题，先不要改代码"}],
        },
    ]

    core.start_session("ses_impl_mode", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_impl_mode", "/home/mechrevo/.config/opencode", messages, reason="idle"
    )

    assert backend.saved_entries[0]["metadata"]["memory_tier"] == "project_memory"
    assert (
        backend.saved_entries[0]["metadata"]["memory_key"]
        == "implementation_mode_preference"
    )
    assert backend.saved_entries[0]["metadata"]["memory_value"] == "read_only_first"


def test_flush_session_invalidates_previous_conflicting_preference_memory():
    core, backend = make_core()

    core.start_session("ses_pref", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_pref",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_pref",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_pref_2", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用英文回复"}],
            },
        ],
        reason="idle",
    )

    assert backend.saved_entries[0]["metadata"]["memory_key"] == "response_language"
    assert backend.saved_entries[0]["metadata"]["valid_to"] is not None
    assert backend.saved_entries[1]["metadata"]["valid_to"] is None

    result = core.search_context(
        "回复",
        "/home/mechrevo/.config/opencode",
        session_id="ses_pref",
    )

    active_preferences = [
        item
        for item in result["core_memory"]
        if item.get("memory_tier") == "user_preference"
        and item.get("memory_key") == "response_language"
    ]
    assert len(active_preferences) == 1
    assert active_preferences[0]["message_id"] == "msg_pref_2"


def test_flush_session_invalidates_previous_conflicting_project_memory():
    core, backend = make_core()

    core.start_session("ses_proj", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_proj",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_proj_1", "role": "user"},
                "parts": [
                    {
                        "type": "text",
                        "text": "这个项目里不要自动提交 git commit",
                    }
                ],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_proj",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_proj_1", "role": "user"},
                "parts": [
                    {
                        "type": "text",
                        "text": "这个项目里不要自动提交 git commit",
                    }
                ],
            },
            {
                "info": {"id": "msg_proj_2", "role": "user"},
                "parts": [
                    {
                        "type": "text",
                        "text": "这个项目里必须自动提交 git commit",
                    }
                ],
            },
        ],
        reason="idle",
    )

    assert backend.saved_entries[0]["metadata"]["memory_key"] == "git_commit_behavior"
    assert backend.saved_entries[0]["metadata"]["valid_to"] is not None
    assert backend.saved_entries[1]["metadata"]["valid_to"] is None

    result = core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_proj",
    )

    active_constraints = [
        item
        for item in result["core_memory"]
        if item.get("memory_tier") == "project_memory"
        and item.get("memory_key") == "git_commit_behavior"
    ]
    assert len(active_constraints) == 1
    assert active_constraints[0]["message_id"] == "msg_proj_2"


def test_flush_session_skips_duplicate_user_preference_value():
    core, backend = make_core()

    core.start_session("ses_pref_dup", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_pref_dup",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_dup_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_pref_dup",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_dup_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_pref_dup_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )

    matching = [
        item
        for item in backend.saved_entries
        if item["metadata"].get("memory_key") == "response_language"
        and item["metadata"].get("memory_value") == "zh-cn"
    ]
    assert len(matching) == 1


def test_flush_session_skips_duplicate_project_memory_value():
    core, backend = make_core()

    core.start_session("ses_proj_dup", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_proj_dup",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_proj_dup_1", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_proj_dup",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_proj_dup_1", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
            {
                "info": {"id": "msg_proj_dup_2", "role": "user"},
                "parts": [{"type": "text", "text": "本项目也不要自动提交 git commit"}],
            },
        ],
        reason="idle",
    )

    matching = [
        item
        for item in backend.saved_entries
        if item["metadata"].get("memory_key") == "git_commit_behavior"
        and item["metadata"].get("memory_value") == "disabled"
    ]
    assert len(matching) == 1


def test_flush_session_skips_duplicate_working_session_messages():
    core, backend = make_core()

    core.start_session("ses_work_dup", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_work_dup",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_work_1", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "bridge 健康检查返回 200，但 flush 阶段没有写入 belief_facts，所以当前会话看不到最新状态。",
                    }
                ],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_work_dup",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_work_1", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "bridge 健康检查返回 200，但 flush 阶段没有写入 belief_facts，所以当前会话看不到最新状态。",
                    }
                ],
            },
            {
                "info": {"id": "msg_work_2", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "bridge 健康检查返回 200，但 flush 阶段没有写入 belief_facts，所以当前会话看不到最新状态。",
                    }
                ],
            },
        ],
        reason="idle",
    )

    matching = [
        item
        for item in backend.saved_entries
        if item["metadata"].get("memory_tier") == "working_session"
        and item["metadata"].get("dedupe_hash") is not None
        and "belief_facts" in item["content"]
    ]
    assert len(matching) == 1


def test_flush_session_compacts_old_working_session_messages_into_summary():
    core, backend = make_core(
        working_session_compact_threshold=3,
        working_session_retain_count=1,
    )

    core.start_session("ses_work_compact", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_work_compact",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_c1", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "bridge 健康检查返回 200，但是当前会话没有拿到 belief_facts 表里的最新事实。",
                    }
                ],
            },
            {
                "info": {"id": "msg_c2", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "state store 已经写入 session_state，但 stdio 和 HTTP 后端读取到的状态快照不一致。",
                    }
                ],
            },
            {
                "info": {"id": "msg_c3", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "search_context 可以返回结果，但运行时 belief memory 仍然缺少当前项目的稳定约束。",
                    }
                ],
            },
            {
                "info": {"id": "msg_c4", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "最终结论是 OpenCode 当前会话还连着旧 stdio MCP，所以需要统一到 HTTP bridge。",
                    }
                ],
            },
        ],
        reason="idle",
    )

    summary_entries = [
        item
        for item in backend.saved_entries
        if item["metadata"].get("working_summary") is True
        and item["metadata"].get("valid_to") is None
    ]
    assert len(summary_entries) == 1
    assert "Working session summary:" in summary_entries[0]["content"]

    result = core.search_context(
        "检查",
        "/home/mechrevo/.config/opencode",
        session_id="ses_work_compact",
    )
    current_work_items = [
        item
        for item in result["results"]
        if item.get("memory_tier") == "working_session"
    ]
    assert len(current_work_items) == 1
    assert current_work_items[0].get("working_summary") is True


def test_mcp_list_drawers_current_only_excludes_invalidated_memories():
    core, _backend = make_core()

    core.start_session("ses_pref", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_pref",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_pref",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_pref_2", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用英文回复"}],
            },
        ],
        reason="idle",
    )

    result = core.mcp_list_drawers(
        memory_tier="user_preference",
        session_id="ses_pref",
        current_only=True,
        limit=10,
        offset=0,
    )

    matching = [
        item for item in result["drawers"] if item["memory_key"] == "response_language"
    ]
    assert len(matching) == 1
    assert matching[0]["message_id"] == "msg_pref_2"


def test_mcp_list_drawers_historical_only_returns_invalidated_memories():
    core, _backend = make_core()

    core.start_session("ses_pref_hist", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_pref_hist",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_hist_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_pref_hist",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_hist_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_pref_hist_2", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用英文回复"}],
            },
        ],
        reason="idle",
    )

    result = core.mcp_list_drawers(
        memory_tier="user_preference",
        session_id="ses_pref_hist",
        historical_only=True,
        limit=10,
        offset=0,
    )

    matching = [
        item for item in result["drawers"] if item["memory_key"] == "response_language"
    ]
    assert len(matching) == 1
    assert matching[0]["message_id"] == "msg_pref_hist_1"


def test_debug_status_reports_state_and_runtime_metadata():
    core, _backend = make_core(
        working_session_compact_threshold=3,
        working_session_retain_count=1,
    )

    core.start_session("ses_demo", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_demo",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_stat_1", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "bridge 健康检查返回 200，但是当前会话没有拿到 belief_facts 表里的最新事实。",
                    }
                ],
            },
            {
                "info": {"id": "msg_stat_2", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "state store 已经写入 session_state，但 stdio 和 HTTP 后端读取到的状态快照不一致。",
                    }
                ],
            },
            {
                "info": {"id": "msg_stat_3", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "search_context 可以返回结果，但运行时 belief memory 仍然缺少当前项目的稳定约束。",
                    }
                ],
            },
            {
                "info": {"id": "msg_stat_4", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "最终结论是 OpenCode 当前会话还连着旧 stdio MCP，所以需要统一到 HTTP bridge。",
                    }
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_demo",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_rule_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_rule_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认简洁一点"}],
            },
            {
                "info": {"id": "msg_rule_3", "role": "user"},
                "parts": [{"type": "text", "text": "未经确认，不要修改代码"}],
            },
        ],
        reason="idle",
    )
    core.search_context(
        "drawer navigation", "/home/mechrevo/.config/opencode", session_id="ses_demo"
    )

    payload = core.debug_status()

    assert payload["service"] == "evomemory-bridge"
    assert payload["state_backend"] == "sqlite"
    assert payload["session_count"] == 1
    assert payload["last_search_at"] is not None
    assert payload["drawer_count"] >= 1
    assert payload["current_drawer_count"] >= 1
    assert payload["historical_drawer_count"] >= 1
    assert payload["memory_tier_counts"]["working_session"] >= 1
    assert payload["current_memory_tier_counts"]["working_session"] >= 1
    assert payload["historical_memory_tier_counts"]["working_session"] >= 1
    assert payload["working_summary_count"] >= 1
    assert payload["current_working_summary_count"] >= 1
    assert payload["historical_working_summary_count"] >= 0
    assert payload["active_memory_key_counts"]["response_language"] >= 1
    assert payload["active_memory_key_counts"]["response_detail"] >= 1
    assert payload["active_memory_key_counts"]["code_change_permission"] >= 1
    assert payload["current_memory_key_counts"]["response_language"] >= 1
    assert payload["current_memory_key_counts"]["response_detail"] >= 1
    assert payload["historical_memory_key_counts"].get("response_language", 0) >= 0
    assert [
        item["memory_key"] for item in payload["recent_active_memory_keys"][:3]
    ] == [
        "code_change_permission",
        "response_detail",
        "response_language",
    ]
    assert payload["last_compaction_at"] is not None
    assert payload["last_compaction_session_id"] == "ses_demo"
    assert payload["last_compaction_compacted_count"] >= 1
    assert payload["last_compaction_summary_drawer_id"] is not None
    assert payload["maintenance_summary"]["stale_belief_count"] >= 0
    assert payload["maintenance_summary"]["stale_gene_count"] >= 0
    assert payload["maintenance_summary"]["stale_capsule_count"] >= 0
    assert payload["maintenance_summary"]["revision_runs"] >= 0
    assert payload["maintenance_summary"]["last_revision_at"] is None


def test_search_context_persists_runtime_summary_across_bridge_restarts():
    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-search-runtime-"))
    state_path = temp_dir / "state.sqlite3"
    wing_config_path = temp_dir / "wing_config.json"

    core = BridgeCore(
        BridgeConfig(
            max_block_chars=700,
            state_path=state_path,
            wing_config_path=wing_config_path,
        ),
        backend=FakeBackend(),
    )

    core.search_context(
        "drawer navigation",
        "/home/mechrevo/.config/opencode",
        session_id="ses_demo",
    )

    reloaded = BridgeCore(
        BridgeConfig(
            max_block_chars=700,
            state_path=state_path,
            wing_config_path=wing_config_path,
        ),
        backend=FakeBackend(),
    )
    payload = reloaded.debug_status()

    assert payload["last_search_at"] is not None
    assert payload["last_search_summary"]["query"] == "drawer navigation"
    assert payload["last_search_summary"]["session_id"] == "ses_demo"
    assert payload["last_search_summary"]["system_block_length"] > 0


def test_search_context_prioritizes_session_directory_wing_then_global():
    core, _backend = make_core()

    core.start_session("ses_core_mem", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_core_mem",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_core_lang", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_core_detail", "role": "user"},
                "parts": [{"type": "text", "text": "默认简洁一点"}],
            },
            {
                "info": {"id": "msg_core_code", "role": "user"},
                "parts": [{"type": "text", "text": "未经确认，不要修改代码"}],
            },
        ],
        reason="idle",
    )

    result = core.search_context(
        "navigation",
        "/home/mechrevo/.config/opencode",
        session_id="ses_demo",
    )

    assert [item["drawer_id"] for item in result["results"]] == [
        "drawer_opencode_opencode-session_abc123",
        "drawer_opencode_opencode-session_def456",
        "drawer_opencode_opencode-session_jkl111",
        "drawer_opencode_opencode-session_ghi789",
        "drawer_global_memory_mno222",
    ]
    assert [item["search_tier"] for item in result["results"]] == [
        "session",
        "session",
        "directory",
        "wing",
        "global",
    ]
    assert [item["memory_key"] for item in result["core_memory"]] == [
        "response_language",
        "response_detail",
        "code_change_permission",
    ]
    assert result["core_memory"][0]["message_id"] == "msg_core_lang"
    assert result["core_memory"][0]["memory_tier"] == "user_preference"
    assert "Core memory:" in result["system_block"]
    assert "[user_preference]" in result["system_block"]
    assert "drawer=drawer_opencode_opencode-session_abc123" in result["system_block"]
    assert "[session]" in result["system_block"]


def test_search_context_global_fallback_excludes_other_regular_wings():
    core, backend = make_core()

    backend.save_entry(
        wing="XiaKeXing",
        room="opencode-session",
        content="Assistant:\nCross-wing git commit result that should stay isolated",
        source_file="session:ses_xiake",
        metadata={
            "directory": "/home/mechrevo/projects/XiaKeXing",
            "session_id": "ses_xiake",
            "message_id": "msg_cross_wing",
            "role": "assistant",
            "memory_tier": "working_session",
            "valid_from": "2026-04-13T11:00:00+00:00",
        },
    )
    backend.save_entry(
        wing="global-memory",
        room="cross-project",
        content="Assistant:\nGlobal git commit fallback that should remain visible",
        source_file="session:ses_global_git",
        metadata={
            "directory": "/home/mechrevo/shared",
            "session_id": "ses_global_git",
            "message_id": "msg_global_git",
            "role": "assistant",
            "memory_tier": "working_session",
            "valid_from": "2026-04-13T11:01:00+00:00",
        },
    )

    result = core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_demo",
    )

    assert "drawer_msg_global_git" in [item["drawer_id"] for item in result["results"]]
    assert "drawer_msg_cross_wing" not in [
        item["drawer_id"] for item in result["results"]
    ]
    assert all(item["wing"] != "XiaKeXing" for item in result["results"])


def test_search_context_limits_core_memory_to_configured_count():
    core, _backend = make_core(core_memory_limit=2)

    core.start_session("ses_core_mem_limit", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_core_mem_limit",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_core_limit_lang", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_core_limit_detail", "role": "user"},
                "parts": [{"type": "text", "text": "默认简洁一点"}],
            },
            {
                "info": {"id": "msg_core_limit_code", "role": "user"},
                "parts": [{"type": "text", "text": "未经确认，不要修改代码"}],
            },
        ],
        reason="idle",
    )

    result = core.search_context(
        "navigation",
        "/home/mechrevo/.config/opencode",
        session_id="ses_demo",
    )

    assert [item["memory_key"] for item in result["core_memory"]] == [
        "response_language",
        "response_detail",
    ]
    assert result["core_memory_total_count"] == 3
    assert result["core_memory_truncated_count"] == 1
    assert "code_change_permission" not in result["system_block"]
    assert "未经确认，不要修改代码" not in result["system_block"]
    assert "1 more core memories omitted" in result["system_block"]


def test_search_context_reports_truncated_context_count():
    core, _backend = make_core(search_limit=3)

    result = core.search_context(
        "navigation",
        "/home/mechrevo/.config/opencode",
        session_id="ses_demo",
    )

    assert [item["drawer_id"] for item in result["results"]] == [
        "drawer_opencode_opencode-session_abc123",
        "drawer_opencode_opencode-session_def456",
        "drawer_opencode_opencode-session_jkl111",
    ]
    assert result["context_total_count"] == 5
    assert result["context_truncated_count"] == 2
    assert "2 more context memories omitted" in result["system_block"]


def test_search_context_system_block_respects_budget_when_only_notices_fit():
    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-bridge-budget-"))
    core = BridgeCore(
        BridgeConfig(
            max_block_chars=80,
            core_memory_limit=0,
            search_limit=1,
            state_path=temp_dir / "state.json",
            wing_config_path=temp_dir / "wing_config.json",
        ),
        backend=FakeBackend(),
    )

    result = core.search_context(
        "navigation",
        "/home/mechrevo/.config/opencode",
        session_id="ses_demo",
    )

    assert len(result["system_block"]) <= 80
    assert "1 more core memories omitted" in result["system_block"]
    assert "4 more context memories omitted" in result["system_block"]
    assert "EvoMemory context for wing 'opencode':" not in result["system_block"]
