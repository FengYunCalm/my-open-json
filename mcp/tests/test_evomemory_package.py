from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class PromotionBackend:
    def __init__(self):
        self.saved_entries = []

    def query_drawers(
        self,
        *,
        query=None,
        wing=None,
        directory=None,
        memory_tier=None,
        current_only=False,
        historical_only=False,
        room=None,
        session_id=None,
        role=None,
        source_file=None,
        limit=20,
        offset=0,
    ):
        rows = []
        for entry in self.saved_entries:
            metadata = entry["metadata"]
            row = {
                "drawer_id": entry["drawer_id"],
                "text": entry["content"],
                "wing": entry["wing"],
                "room": entry["room"],
                "directory": metadata.get("directory"),
                "source_file": entry["source_file"],
                "session_id": metadata.get("session_id"),
                "message_id": metadata.get("message_id"),
                "role": metadata.get("role"),
                "memory_tier": metadata.get("memory_tier"),
                "memory_key": metadata.get("memory_key"),
                "memory_value": metadata.get("memory_value"),
                "dedupe_hash": metadata.get("dedupe_hash"),
                "valid_from": metadata.get("valid_from"),
                "valid_to": metadata.get("valid_to"),
                "filed_at": metadata.get("filed_at"),
                "working_summary": metadata.get("working_summary") is True,
                "metadata": metadata,
                "similarity": 1.0,
            }
            rows.append(row)
        if wing is not None:
            rows = [row for row in rows if row["wing"] == wing]
        if directory is not None:
            rows = [row for row in rows if row.get("directory") == directory]
        if memory_tier is not None:
            rows = [row for row in rows if row.get("memory_tier") == memory_tier]
        if room is not None:
            rows = [row for row in rows if row["room"] == room]
        if session_id is not None:
            rows = [row for row in rows if row.get("session_id") == session_id]
        if role is not None:
            rows = [row for row in rows if row.get("role") == role]
        if source_file is not None:
            rows = [row for row in rows if row.get("source_file") == source_file]
        if current_only:
            rows = [row for row in rows if not row.get("valid_to")]
        elif historical_only:
            rows = [row for row in rows if row.get("valid_to")]
        rows.sort(
            key=lambda row: (row.get("valid_from") or "", row.get("message_id") or "")
        )
        return rows[offset : offset + limit]

    def get_session_messages(self, **kwargs):
        return self.query_drawers(**kwargs)

    def save_entry(self, *, wing, room, content, source_file, metadata):
        payload = {
            "drawer_id": f"drawer_{metadata.get('message_id', len(self.saved_entries) + 1)}",
            "wing": wing,
            "room": room,
            "source_file": source_file,
            "metadata": metadata,
            "content": content,
        }
        self.saved_entries.append(payload)
        return payload

    def invalidate_memory_conflicts(
        self, *, wing, directory, memory_tier, memory_key, valid_to
    ):
        invalidated = 0
        for entry in self.saved_entries:
            metadata = entry["metadata"]
            if entry["wing"] != wing:
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

    def invalidate_drawers(self, *, drawer_ids, valid_to):
        invalidated = 0
        ids = set(drawer_ids)
        for entry in self.saved_entries:
            if entry["drawer_id"] not in ids:
                continue
            if entry["metadata"].get("valid_to"):
                continue
            entry["metadata"]["valid_to"] = valid_to
            invalidated += 1
        return invalidated

    def delete_drawers(self, *, drawer_ids):
        ids = list(dict.fromkeys(drawer_ids))
        id_set = set(ids)
        before = len(self.saved_entries)
        self.saved_entries = [
            entry for entry in self.saved_entries if entry["drawer_id"] not in id_set
        ]
        return before - len(self.saved_entries)

    def list_stale_drawer_ids(self, *, before):
        result = []
        for entry in self.saved_entries:
            metadata = entry["metadata"]
            valid_to = metadata.get("valid_to") or ""
            reference_at = metadata.get("valid_from") or metadata.get("filed_at") or ""
            if valid_to and valid_to <= before:
                result.append(entry["drawer_id"])
                continue
            if reference_at and reference_at <= before and not valid_to:
                result.append(entry["drawer_id"])
        return result

    def status(self):
        return {"total_drawers": len(self.saved_entries), "palace_path": "/tmp/palace"}

    def memory_stats(self):
        return {}

    def list_wings(self):
        return {}

    def list_rooms(self, wing=None):
        return {}

    def get_taxonomy(self):
        return {}

    def list_drawers(self, **kwargs):
        return self.query_drawers(**kwargs)

    def get_drawer(self, drawer_id):
        return next(
            (entry for entry in self.saved_entries if entry["drawer_id"] == drawer_id),
            None,
        )

    def list_sessions(self, **kwargs):
        return []

    def kg_query(self, entity, as_of=None, direction="both"):
        return {
            "entity": entity,
            "facts": [],
            "count": 0,
            "as_of": as_of,
            "direction": direction,
        }


def test_evomemory_exposes_phase_one_contracts_and_modules():
    from evomemory import BeliefPlaneService, GovernancePlaneService
    from evomemory.contracts import Capsule, EvolutionEvent, Gene, MemoryRecord
    from evomemory.context.bridge import BridgeConfig, BridgeCore, EvoMemoryBackend
    from evomemory.context.query_service import ContextQueryService
    from evomemory.context.repository import ContextRepository
    from evomemory.context.session_service import SessionLifecycleService
    from evomemory.domain.memory_policy import classify_memory_tier
    from evomemory.infrastructure.state.session_state import SessionStateStore
    from evomemory.interfaces.mcp.server import create_app

    record = MemoryRecord(
        scope="session",
        plane="context",
        kind="event",
        key="message",
        value="hello",
    )
    gene = Gene(id="gene_skill_reuse", summary="avoid duplicate skill reloads")
    capsule = Capsule(id="capsule_debugging", summary="debugging workflow")
    event = EvolutionEvent(
        id="event_001",
        action="promote",
        target_kind="gene",
        target_id="gene_skill_reuse",
    )

    assert record.scope == "session"
    assert gene.id == "gene_skill_reuse"
    assert capsule.id == "capsule_debugging"
    assert event.target_kind == "gene"
    assert BridgeConfig is not None
    assert BridgeCore is not None
    assert BeliefPlaneService is not None
    assert ContextRepository is not None
    assert SessionLifecycleService is not None
    assert ContextQueryService is not None
    assert GovernancePlaneService is not None
    assert EvoMemoryBackend is not None
    assert classify_memory_tier("user", "以后都用中文") == "user_preference"
    assert SessionStateStore is not None
    assert create_app is not None


def test_evomemory_ships_opencode_mcp_template():
    template = (
        Path(__file__).resolve().parents[1]
        / "evomemory"
        / "adapters"
        / "opencode"
        / "opencode.mcp.remote.jsonc"
    )

    assert template.exists()
    assert '"evomemory"' in template.read_text(encoding="utf-8")


def test_bridge_core_exposes_evomemory_unified_query_surface():
    import importlib.util

    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-belief-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.json"), backend=PromotionBackend()
    )

    status = core.evomemory_status()
    assert status["service"] == "evomemory"
    assert status["context"]["service"] == "evomemory-bridge"
    assert status["context"]["budget_policy"] == {
        "max_block_chars": 2000,
        "runtime_overlay_reserved_chars": 96,
        "runtime_base_min_chars": 80,
    }
    assert status["context"]["budget_policy_diff"] == {}
    assert status["belief"]["plane"] == "belief"
    assert status["governance"]["plane"] == "governance"
    assert status["maintenance_summary"]["plane"] == "maintenance"
    assert status["maintenance_summary"]["service"] == "evomemory"
    assert core.evomemory_query_beliefs()["facts"] == []
    assert core.evomemory_query_genes()["genes"] == []
    assert core.evomemory_query_capsules()["capsules"] == []
    assert core.evomemory_list_evolution_events()["events"] == []


def test_memory_reviser_skips_duplicate_current_value_and_invalidates_conflicts():
    from evomemory.belief.reviser import MemoryReviser
    from evomemory.context.repository import ContextRepository

    backend = PromotionBackend()
    repository = ContextRepository(backend)
    reviser = MemoryReviser(repository)

    backend.save_entry(
        wing="opencode",
        room="opencode-session",
        content="User:\n以后都用中文回复",
        source_file="session:ses_rev",
        metadata={
            "session_id": "ses_rev",
            "message_id": "msg_rev_1",
            "directory": "/home/mechrevo/.config/opencode",
            "memory_tier": "user_preference",
            "memory_key": "response_language",
            "memory_value": "zh-cn",
            "valid_from": "2026-04-16T00:00:00+00:00",
            "valid_to": None,
        },
    )

    duplicate = reviser.revise_memory(
        wing="opencode",
        directory="/home/mechrevo/.config/opencode",
        memory_tier="user_preference",
        memory_key="response_language",
        memory_value="zh-cn",
        valid_to="2026-04-16T00:01:00+00:00",
    )
    changed = reviser.revise_memory(
        wing="opencode",
        directory="/home/mechrevo/.config/opencode",
        memory_tier="user_preference",
        memory_key="response_language",
        memory_value="en",
        valid_to="2026-04-16T00:02:00+00:00",
    )

    assert duplicate["skip_save"] is True
    assert changed["skip_save"] is False
    assert changed["invalidated_count"] == 1
    assert (
        backend.saved_entries[0]["metadata"]["valid_to"] == "2026-04-16T00:02:00+00:00"
    )


def test_memory_promoter_promotes_beliefs_and_governance_assets():
    from evomemory.belief.promoter import MemoryPromoter
    from evomemory.belief.service import BeliefPlaneService
    from evomemory.governance.service import GovernancePlaneService

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-promoter-"))
    belief = BeliefPlaneService(temp_dir / "state.sqlite3")
    governance = GovernancePlaneService(temp_dir / "state.sqlite3")
    promoter = MemoryPromoter(belief, governance)

    result = promoter.promote_saved_memory(
        scope="project",
        memory_tier="project_memory",
        memory_key="git_commit_behavior",
        memory_value="disabled",
        source_session="ses_promote",
        source_message_id="msg_promote_1",
        source_record_id="drawer_msg_promote_1",
        valid_from="2026-04-16T00:00:00+00:00",
    )

    assert result["belief"]["key"] == "git_commit_behavior"
    assert result["gene"]["key"] == "git_commit_behavior"
    assert result["capsule"]["scope"] == "project"
    assert {item["action"] for item in result["events"]} >= {"promote"}


def test_flush_session_requires_reaffirmation_before_promoting_memories_into_belief_plane():
    import importlib.util

    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-belief-conflict-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.json"), backend=PromotionBackend()
    )
    core.start_session("ses_belief", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_belief",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_proj", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    first_pass_beliefs = core.evomemory_query_beliefs(current_only=True, limit=10)
    assert first_pass_beliefs["count"] == 0

    core.flush_session(
        "ses_belief",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_proj", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
            {
                "info": {"id": "msg_pref_reaffirm", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_proj_reaffirm", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )

    user_beliefs = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True
    )
    project_beliefs = core.evomemory_query_beliefs(
        scope="project", key="git_commit_behavior", current_only=True
    )
    genes = core.evomemory_query_genes(limit=10)
    capsules = core.evomemory_query_capsules(limit=10)
    status = core.evomemory_status()

    assert user_beliefs["count"] == 1
    assert user_beliefs["facts"][0]["value"] == "zh-cn"
    assert user_beliefs["facts"][0]["memory_tier"] == "user_preference"
    assert project_beliefs["count"] == 1
    assert project_beliefs["facts"][0]["value"] == "disabled"
    assert project_beliefs["facts"][0]["memory_tier"] == "project_memory"
    assert genes["count"] == 2
    assert {item["key"] for item in genes["genes"]} >= {
        "response_language",
        "git_commit_behavior",
    }
    assert capsules["count"] == 2
    assert {item["scope"] for item in capsules["capsules"]} >= {"user", "project"}
    assert status["belief"]["fact_count"] == 2
    assert status["context"]["budget_policy"] == {
        "max_block_chars": 2000,
        "runtime_overlay_reserved_chars": 96,
        "runtime_base_min_chars": 80,
    }
    assert status["context"]["budget_policy_diff"] == {}


def test_reaffirming_current_belief_updates_metadata_without_creating_new_fact():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-belief-metadata-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.sqlite3"), backend=PromotionBackend()
    )
    core.start_session("ses_belief_meta", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_belief_meta",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_meta_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    assert (
        core.evomemory_query_beliefs(scope="user", key="response_language")["count"]
        == 0
    )
    core.flush_session(
        "ses_belief_meta",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_meta_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_meta_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )

    beliefs = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True
    )

    assert beliefs["count"] == 1
    assert beliefs["facts"][0]["value"] == "zh-cn"
    assert beliefs["facts"][0]["source_count"] == 2
    assert beliefs["facts"][0]["last_confirmed_at"] is not None
    assert beliefs["facts"][0]["confidence"] > 0.6


def test_unstructured_user_preference_candidates_fall_back_to_working_session():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-unstructured-preference-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.sqlite3"), backend=PromotionBackend()
    )
    core.start_session("ses_unstructured_preference", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_unstructured_preference",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_unstructured_preference", "role": "user"},
                "parts": [
                    {
                        "type": "text",
                        "text": "就用你默认的稳方案，现在开始plan最终可执行方案",
                    }
                ],
            }
        ],
        reason="idle",
    )

    user_preferences = core.mcp_list_drawers(
        memory_tier="user_preference",
        current_only=True,
        session_id="ses_unstructured_preference",
        role="user",
        limit=10,
    )
    session_messages = core.mcp_get_session_messages(
        "ses_unstructured_preference",
        current_only=True,
        role="user",
        limit=10,
    )

    assert user_preferences["count"] == 0
    assert session_messages["count"] == 1
    assert session_messages["messages"][0]["memory_tier"] == "working_session"
    assert session_messages["messages"][0]["memory_key"] is None


def test_belief_query_supports_min_confidence_filter():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-belief-filter-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.sqlite3"), backend=PromotionBackend()
    )
    core.start_session("ses_belief_filter", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_belief_filter",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_filter_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_filter_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
            {
                "info": {"id": "msg_filter_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_belief_filter",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_filter_4", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_belief_filter",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_filter_5", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
            {
                "info": {"id": "msg_filter_6", "role": "user"},
                "parts": [{"type": "text", "text": "请继续用中文回复"}],
            },
        ],
        reason="idle",
    )

    all_beliefs = core.evomemory_query_beliefs(current_only=True, limit=10)
    strong_beliefs = core.evomemory_query_beliefs(
        current_only=True,
        min_confidence=0.9,
        limit=10,
    )

    assert all_beliefs["count"] >= 2
    assert strong_beliefs["count"] == 1
    assert strong_beliefs["facts"][0]["key"] == "response_language"


def test_conflicting_beliefs_supersede_previous_fact_and_record_events():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-belief-conflict-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.json"), backend=PromotionBackend()
    )
    core.start_session("ses_conflict", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_conflict",
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
        "ses_conflict",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_conflict",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_3", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用英文回复"}],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_conflict",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_4", "role": "user"},
                "parts": [{"type": "text", "text": "默认以后都用英文回复"}],
            },
        ],
        reason="idle",
    )

    current_beliefs = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True
    )
    historical_beliefs = core.evomemory_query_beliefs(
        scope="user", key="response_language", historical_only=True
    )
    events = core.evomemory_list_evolution_events(limit=10)

    assert current_beliefs["count"] == 1
    assert current_beliefs["facts"][0]["value"] == "en"
    assert historical_beliefs["count"] == 1
    assert historical_beliefs["facts"][0]["value"] == "zh-cn"
    assert (
        historical_beliefs["facts"][0]["superseded_by"]
        == current_beliefs["facts"][0]["id"]
    )
    assert events["count"] >= 2
    assert {item["action"] for item in events["events"]} >= {"promote", "supersede"}


def test_beliefs_and_events_persist_across_bridge_instances():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-persist-"))
    state_path = temp_dir / "state.sqlite3"

    core_a = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core_a.start_session("ses_persist", "/home/mechrevo/.config/opencode")
    core_a.flush_session(
        "ses_persist",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
        ],
        reason="idle",
    )
    core_a.flush_session(
        "ses_persist",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )
    core_a.flush_session(
        "ses_persist",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_3", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用英文回复"}],
            }
        ],
        reason="idle",
    )
    core_a.flush_session(
        "ses_persist",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_4", "role": "user"},
                "parts": [{"type": "text", "text": "默认以后都用英文回复"}],
            }
        ],
        reason="idle",
    )

    core_b = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    current_beliefs = core_b.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True
    )
    historical_beliefs = core_b.evomemory_query_beliefs(
        scope="user", key="response_language", historical_only=True
    )
    genes = core_b.evomemory_query_genes(limit=10)
    capsules = core_b.evomemory_query_capsules(limit=10)
    events = core_b.evomemory_list_evolution_events(limit=10)

    assert current_beliefs["count"] == 1
    assert current_beliefs["facts"][0]["value"] == "en"
    assert historical_beliefs["count"] == 1
    assert historical_beliefs["facts"][0]["value"] == "zh-cn"
    assert genes["count"] >= 2
    assert capsules["count"] >= 1
    assert events["count"] >= 2


def test_search_context_includes_beliefs_and_governance_assets():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-runtime-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.sqlite3"), backend=PromotionBackend()
    )
    core.start_session("ses_runtime", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_runtime",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_proj", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_runtime",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_pref_again", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_proj_again", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )

    result = core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_runtime",
    )

    assert result["belief_memory_count"] == 2
    assert {item["key"] for item in result["belief_memory"]} >= {
        "response_language",
        "git_commit_behavior",
    }
    assert result["governance_assets"]["gene_count"] >= 2
    assert result["governance_assets"]["capsule_count"] >= 1
    assert "Belief memory:" in result["system_block"]
    assert "Governance assets:" in result["system_block"]


def test_search_context_prioritizes_higher_confidence_beliefs_in_runtime_overlay():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-runtime-confidence-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.sqlite3"), backend=PromotionBackend()
    )
    core.start_session("ses_runtime_confidence", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_runtime_confidence",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_runtime_lang_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_runtime_code_1", "role": "user"},
                "parts": [{"type": "text", "text": "未经确认，不要修改代码"}],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_runtime_confidence",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_runtime_lang_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_runtime_code_2", "role": "user"},
                "parts": [{"type": "text", "text": "未经确认，还是不要修改代码"}],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_runtime_confidence",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_runtime_code_3", "role": "user"},
                "parts": [{"type": "text", "text": "未经确认，继续不要修改代码"}],
            }
        ],
        reason="idle",
    )

    result = core.search_context(
        "修改代码",
        "/home/mechrevo/.config/opencode",
        session_id="ses_runtime_confidence",
    )

    assert [item["key"] for item in result["belief_memory"][:2]] == [
        "code_change_permission",
        "response_language",
    ]
    assert (
        result["belief_memory"][0]["confidence"]
        > result["belief_memory"][1]["confidence"]
    )
    assert "1. [project] code_change_permission=confirm_first" in result["system_block"]


def test_search_context_prioritizes_higher_score_governance_assets_in_runtime_overlay():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-runtime-governance-rank-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.sqlite3"), backend=PromotionBackend()
    )
    core.start_session("ses_runtime_governance", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_runtime_governance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_runtime_gene_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_runtime_gene_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_runtime_governance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_runtime_gene_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_runtime_gene_4", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )

    language_gene = next(
        item
        for item in core.evomemory_query_genes(current_only=True, limit=10)["genes"]
        if item["key"] == "response_language"
    )
    core.evomemory_record_feedback(
        target_kind="gene",
        target_id=language_gene["id"],
        signal="success",
        note="Language policy is the most reliable governance signal.",
    )

    result = core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_runtime_governance",
    )

    assert [item["key"] for item in result["governance_assets"]["genes"][:2]] == [
        "response_language",
        "git_commit_behavior",
    ]
    assert (
        result["governance_assets"]["genes"][0]["score"]
        > result["governance_assets"]["genes"][1]["score"]
    )
    assert "gene[user] response_language=zh-cn" in result["system_block"]


def test_runtime_overlay_system_block_respects_budget_for_belief_memory():
    from evomemory.runtime.orchestrator import RuntimeOrchestrator

    orchestrator = RuntimeOrchestrator(
        SimpleNamespace(config=SimpleNamespace(max_block_chars=90))
    )

    result = orchestrator._augment_system_block(
        "Base system block",
        [
            {
                "scope": "project",
                "key": "code_change_permission",
                "value": "confirm_first",
            },
            {"scope": "user", "key": "response_language", "value": "zh-cn"},
        ],
        {"genes": [], "capsules": []},
    )

    assert len(result) <= 90
    assert "Belief memory:" in result
    assert "1. [project] code_change_permission=confirm_first" in result
    assert "2. [user] response_language=zh-cn" not in result


def test_runtime_overlay_system_block_respects_budget_for_governance_assets():
    from evomemory.runtime.orchestrator import RuntimeOrchestrator

    orchestrator = RuntimeOrchestrator(
        SimpleNamespace(config=SimpleNamespace(max_block_chars=80))
    )

    result = orchestrator._augment_system_block(
        "Base system block",
        [],
        {
            "genes": [
                {"scope": "user", "key": "response_language", "value": "zh-cn"},
                {
                    "scope": "project",
                    "key": "git_commit_behavior",
                    "value": "disabled",
                },
            ],
            "capsules": [{"scope": "project", "gene_ids": ["gene_a", "gene_b"]}],
        },
    )

    assert len(result) <= 80
    assert "Governance assets:" in result
    assert "- gene[user] response_language=zh-cn" in result
    assert "- gene[project] git_commit_behavior=disabled" not in result
    assert "- capsule[project] genes=gene_a,gene_b" not in result


def test_runtime_overlay_can_trim_base_block_to_keep_top_belief():
    from evomemory.runtime.orchestrator import RuntimeOrchestrator

    orchestrator = RuntimeOrchestrator(
        SimpleNamespace(config=SimpleNamespace(max_block_chars=220))
    )

    result = orchestrator._augment_system_block(
        "   ... 2 more core memories omitted\n\n"
        "   ... 1 more context memories omitted\n\n"
        "Optional historical context from EvoMemory for wing 'opencode'. Use only if it directly helps the current request:\n"
        "1. [1.00][session] drawer=drawer_m1 room=opencode-session role=user src=session:ses\n"
        "   User: 以后都用中文回复",
        [
            {
                "scope": "project",
                "key": "git_commit_behavior",
                "value": "disabled",
            },
            {"scope": "user", "key": "response_language", "value": "zh-cn"},
        ],
        {
            "genes": [
                {
                    "scope": "project",
                    "key": "git_commit_behavior",
                    "value": "disabled",
                }
            ],
            "capsules": [],
        },
    )

    assert len(result) <= 220
    assert "Belief memory:" in result
    assert "1. [project] git_commit_behavior=disabled" in result
    assert "- gene[project] git_commit_behavior=disabled" not in result
    assert "User: 以后都用中文回复" not in result


def test_search_context_reserves_budget_for_top_belief_overlay_when_base_block_is_near_limit():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-runtime-budget-balance-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(
        BridgeConfig(
            state_path=state_path,
            max_block_chars=220,
            core_memory_limit=0,
            search_limit=1,
        ),
        backend=PromotionBackend(),
    )
    core.start_session("ses_runtime_budget_balance", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_runtime_budget_balance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_budget_balance_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_budget_balance_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_runtime_budget_balance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_budget_balance_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_budget_balance_4", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )

    result = core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_runtime_budget_balance",
    )
    snapshot = core.evomemory_export_snapshot(limit=10)

    assert len(result["system_block"]) <= 220
    assert "Belief memory:" in result["system_block"]
    assert "1. [project] git_commit_behavior=disabled" in result["system_block"]
    assert snapshot["runtime_context"]["displayed_belief_keys"]
    assert snapshot["runtime_context"]["displayed_belief_keys"][0] == (
        "git_commit_behavior"
    )
    assert snapshot["runtime_context"]["displayed_governance_gene_keys"] == []


def test_search_context_overlay_reserve_zero_keeps_minimal_budget_behavior():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-runtime-budget-zero-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(
        BridgeConfig(
            state_path=state_path,
            max_block_chars=220,
            core_memory_limit=0,
            search_limit=1,
            runtime_overlay_reserved_chars=0,
            runtime_base_min_chars=80,
        ),
        backend=PromotionBackend(),
    )
    core.start_session("ses_runtime_budget_zero", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_runtime_budget_zero",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_budget_zero_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_budget_zero_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_runtime_budget_zero",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_budget_zero_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_budget_zero_4", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )

    core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_runtime_budget_zero",
    )
    snapshot = core.evomemory_export_snapshot(limit=10)

    assert snapshot["runtime_context"]["displayed_belief_keys"][:1] == [
        "git_commit_behavior"
    ]
    assert snapshot["runtime_context"]["displayed_governance_gene_keys"] == []


def test_search_context_overlay_reserve_can_keep_top_governance_visible():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-runtime-budget-governance-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(
        BridgeConfig(
            state_path=state_path,
            max_block_chars=220,
            core_memory_limit=0,
            search_limit=1,
            runtime_overlay_reserved_chars=160,
            runtime_base_min_chars=0,
        ),
        backend=PromotionBackend(),
    )
    core.start_session(
        "ses_runtime_budget_governance", "/home/mechrevo/.config/opencode"
    )
    core.flush_session(
        "ses_runtime_budget_governance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_budget_governance_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_budget_governance_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_runtime_budget_governance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_budget_governance_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_budget_governance_4", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )

    result = core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_runtime_budget_governance",
    )
    snapshot = core.evomemory_export_snapshot(limit=10)

    assert len(result["system_block"]) <= 220
    assert snapshot["runtime_context"]["displayed_belief_keys"][:1] == [
        "git_commit_behavior"
    ]
    assert snapshot["runtime_context"]["displayed_governance_gene_keys"] == [
        "git_commit_behavior"
    ]


def test_evaluation_summary_tracks_promotions_supersedes_and_enriched_searches():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-eval-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_eval", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_eval",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_eval_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_eval_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_eval",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_eval_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_eval_4", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_eval",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_eval_5", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用英文回复"}],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_eval",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_eval_6", "role": "user"},
                "parts": [{"type": "text", "text": "默认以后都用英文回复"}],
            }
        ],
        reason="idle",
    )
    core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_eval",
    )

    summary = core.evomemory_evaluation_summary()

    assert summary["metrics"]["belief_promotions"] >= 3
    assert summary["metrics"]["belief_supersedes"] >= 1
    assert summary["metrics"]["gene_promotions"] >= 2
    assert summary["metrics"]["capsule_promotions"] >= 2
    assert summary["metrics"]["search_context_calls"] >= 1
    assert summary["metrics"]["enriched_searches"] >= 1


def test_feedback_updates_governance_scores_and_evaluation_metrics():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-feedback-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_feedback", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_feedback",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_feedback_1", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_feedback",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_feedback_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            }
        ],
        reason="idle",
    )

    gene_id = core.evomemory_query_genes(scope="project", current_only=True, limit=10)[
        "genes"
    ][0]["id"]
    capsule_id = core.evomemory_query_capsules(
        scope="project", current_only=True, limit=10
    )["capsules"][0]["id"]

    gene_feedback = core.evomemory_record_feedback(
        target_kind="gene",
        target_id=gene_id,
        signal="success",
        note="This gene helped complete the task.",
    )
    capsule_feedback = core.evomemory_record_feedback(
        target_kind="capsule",
        target_id=capsule_id,
        signal="reject",
        note="This capsule overfit the current task.",
    )

    genes = core.evomemory_query_genes(scope="project", limit=10)
    capsules = core.evomemory_query_capsules(scope="project", limit=10)
    summary = core.evomemory_evaluation_summary()
    events = core.evomemory_list_evolution_events(limit=20)

    assert gene_feedback["target"]["id"] == gene_id
    assert gene_feedback["target"]["score"] >= 1
    assert capsule_feedback["target"]["id"] == capsule_id
    assert capsule_feedback["target"]["score"] <= 0
    assert any(item["id"] == gene_id and item["score"] >= 1 for item in genes["genes"])
    assert any(
        item["id"] == capsule_id and item["score"] <= 0 for item in capsules["capsules"]
    )
    assert summary["metrics"]["feedback_records"] >= 2
    assert summary["metrics"]["positive_feedback"] >= 1
    assert summary["metrics"]["negative_feedback"] >= 1
    assert any(item["action"] == "feedback" for item in events["events"])


def test_feedback_policy_is_signal_specific_and_feedback_log_is_queryable():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-feedback-policy-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_feedback_policy", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_feedback_policy",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_feedback_policy_1", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_feedback_policy",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_feedback_policy_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            }
        ],
        reason="idle",
    )

    gene_id = core.evomemory_query_genes(scope="project", current_only=True, limit=10)[
        "genes"
    ][0]["id"]
    capsule_id = core.evomemory_query_capsules(
        scope="project", current_only=True, limit=10
    )["capsules"][0]["id"]

    confirm_feedback = core.evomemory_record_feedback(
        target_kind="gene",
        target_id=gene_id,
        signal="confirm",
        note="Still valid for this repository.",
    )
    correct_feedback = core.evomemory_record_feedback(
        target_kind="capsule",
        target_id=capsule_id,
        signal="correct",
        note="This capsule should be narrowed down.",
    )

    project_feedback = core.evomemory_list_feedback(
        target_kind="capsule", target_id=capsule_id, limit=10
    )
    all_feedback = core.evomemory_list_feedback(limit=10)
    summary = core.evomemory_evaluation_summary()

    assert confirm_feedback["target"]["score"] >= 1
    assert confirm_feedback["delta"] == 1
    assert correct_feedback["target"]["score"] <= -1
    assert correct_feedback["delta"] == -2
    assert correct_feedback["target"]["is_stale"] is True
    assert project_feedback["count"] == 1
    assert project_feedback["records"][0]["signal"] == "correct"
    assert all_feedback["count"] >= 2
    assert summary["metrics"]["feedback_confirm"] >= 1
    assert summary["metrics"]["feedback_correct"] >= 1


def test_export_snapshot_returns_all_planes():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-snapshot-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_snapshot", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_snapshot",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_snapshot_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_snapshot_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_snapshot",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_snapshot_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_snapshot_4", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    result = core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_snapshot",
    )

    snapshot = core.evomemory_export_snapshot(limit=10)

    assert snapshot["service"] == "evomemory"
    assert snapshot["context"]["service"] == "evomemory-bridge"
    assert snapshot["belief"]["count"] >= 2
    assert snapshot["governance"]["gene_count"] >= 2
    assert snapshot["governance"]["capsule_count"] >= 1
    assert snapshot["evaluation"]["metrics"]["search_context_calls"] >= 1
    assert snapshot["maintenance_summary"]["plane"] == "maintenance"
    assert snapshot["maintenance_summary"]["service"] == "evomemory"
    assert snapshot["feedback"]["count"] == 0
    assert snapshot["runtime_context"]["system_block_length"] == len(
        result["system_block"]
    )
    assert snapshot["runtime_context"]["system_block_char_limit"] == 2000
    assert snapshot["runtime_context"]["belief_memory_keys"] == [
        "git_commit_behavior",
        "response_language",
    ]
    assert snapshot["runtime_context"]["governance_gene_keys"] == [
        "git_commit_behavior",
        "response_language",
    ]
    assert snapshot["context"]["budget_policy"] == {
        "max_block_chars": 2000,
        "runtime_overlay_reserved_chars": 96,
        "runtime_base_min_chars": 80,
    }
    assert snapshot["context"]["budget_policy_diff"] == {}


def test_benchmark_runner_scores_snapshot_health():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-benchmark-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_benchmark", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_benchmark",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_benchmark_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_benchmark_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_benchmark",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_benchmark_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_benchmark_4", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_benchmark",
    )
    gene_id = core.evomemory_query_genes(scope="project", current_only=True, limit=10)[
        "genes"
    ][0]["id"]
    core.evomemory_record_feedback(
        target_kind="gene",
        target_id=gene_id,
        signal="success",
        note="Benchmark setup success.",
    )

    benchmark = core.evomemory_run_benchmark(limit=10)

    assert benchmark["score"] >= 3
    assert benchmark["checks"]["belief_present"] is True
    assert benchmark["checks"]["governance_present"] is True
    assert benchmark["checks"]["feedback_present"] is True
    assert benchmark["checks"]["search_enrichment_present"] is True
    assert benchmark["scenario_checks"]["response_language_captured"] is True
    assert benchmark["scenario_checks"]["git_commit_gene_present"] is True
    assert benchmark["scenario_checks"]["project_capsule_present"] is True
    assert benchmark["scenario_checks"]["search_enrichment_active"] is True
    assert benchmark["scenario_checks"]["runtime_block_within_budget"] is True
    assert benchmark["scenario_checks"]["runtime_top_belief_retained"] is True
    assert benchmark["scenario_checks"]["runtime_top_gene_retained"] is True
    assert benchmark["scenario_checks"]["archive_export_ready"] is True
    assert benchmark["scenario_summary"]["captured_belief_keys"] == [
        "git_commit_behavior",
        "response_language",
    ]
    assert benchmark["scenario_summary"]["gene_keys"] == [
        "git_commit_behavior",
        "response_language",
    ]
    assert benchmark["scenario_summary"]["capsule_scopes"] == ["project", "user"]
    assert benchmark["scenario_summary"]["runtime_block_length"] > 0
    assert benchmark["scenario_summary"]["runtime_block_char_limit"] == 2000
    assert benchmark["scenario_summary"]["runtime_belief_keys"] == [
        "git_commit_behavior",
        "response_language",
    ]
    assert benchmark["scenario_summary"]["runtime_gene_keys"] == [
        "git_commit_behavior",
        "response_language",
    ]
    assert (
        benchmark["scenario_summary"]["top_runtime_belief_key"] == "git_commit_behavior"
    )
    assert (
        benchmark["scenario_summary"]["top_runtime_gene_key"] == "git_commit_behavior"
    )
    assert benchmark["scenario_summary"]["budget_policy"] == {
        "max_block_chars": 2000,
        "runtime_overlay_reserved_chars": 96,
        "runtime_base_min_chars": 80,
    }
    assert benchmark["scenario_summary"]["budget_policy_diff"] == {}
    assert benchmark["scenario_summary"]["archive_format"] == "evomemory-archive-v1"
    assert benchmark["scenario_summary"]["archive_belief_count"] >= 2


def test_benchmark_runner_detects_runtime_items_dropped_by_small_budget():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    class QueryFilteringBackend(PromotionBackend):
        def query_drawers(self, **kwargs):
            rows = super().query_drawers(**kwargs)
            query = kwargs.get("query")
            if query is None:
                return rows
            return [row for row in rows if query in row.get("text", "")]

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-benchmark-small-budget-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(
        BridgeConfig(
            state_path=state_path,
            max_block_chars=90,
            core_memory_limit=0,
            search_limit=1,
        ),
        backend=QueryFilteringBackend(),
    )
    core.start_session("ses_benchmark_small_budget", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_benchmark_small_budget",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_benchmark_small_budget_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_benchmark_small_budget_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_benchmark_small_budget",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_benchmark_small_budget_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_benchmark_small_budget_4", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )

    result = core.search_context(
        "zzz-no-match",
        "/home/mechrevo/.config/opencode",
        session_id="ses_benchmark_small_budget",
    )
    snapshot = core.evomemory_export_snapshot(limit=10)
    benchmark = core.evomemory_run_benchmark(limit=10)

    assert len(result["system_block"]) <= 90
    assert snapshot["runtime_context"]["belief_memory_keys"] == [
        "git_commit_behavior",
        "response_language",
    ]
    assert snapshot["runtime_context"]["displayed_belief_keys"] == [
        "git_commit_behavior",
        "response_language",
    ]
    assert snapshot["runtime_context"]["displayed_governance_gene_keys"] == []
    assert benchmark["scenario_checks"]["runtime_block_within_budget"] is True
    assert benchmark["scenario_checks"]["runtime_top_belief_retained"] is True
    assert benchmark["scenario_checks"]["runtime_top_gene_retained"] is False
    assert benchmark["scenario_summary"]["runtime_gene_keys"] == []
    assert benchmark["scenario_summary"]["budget_policy_diff"] == {
        "max_block_chars": {"default": 2000, "current": 90, "delta": -1910}
    }
    assert (
        benchmark["scenario_summary"]["top_runtime_gene_key"] == "git_commit_behavior"
    )


def test_belief_feedback_updates_confidence_and_audit_log():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-belief-feedback-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_belief_feedback", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_belief_feedback",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_belief_feedback_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_belief_feedback",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_belief_feedback_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            }
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]

    confirm_feedback = core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="confirm",
        note="Still true for the current user.",
    )
    correct_feedback = core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="This belief should be reconsidered.",
    )

    updated_belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    feedback_log = core.evomemory_list_feedback(
        target_kind="belief", target_id=belief["id"], limit=10
    )
    summary = core.evomemory_evaluation_summary()

    assert confirm_feedback["target"]["id"] == belief["id"]
    assert confirm_feedback["delta"] == 1
    assert correct_feedback["delta"] == -2
    assert updated_belief["confidence"] < 1.0
    assert updated_belief["last_confirmed_at"] is not None
    assert feedback_log["count"] == 2
    assert {item["signal"] for item in feedback_log["records"]} == {
        "confirm",
        "correct",
    }
    assert summary["metrics"]["feedback_confirm"] >= 1
    assert summary["metrics"]["feedback_correct"] >= 1


def test_revision_marks_low_confidence_beliefs_stale_and_demotes_assets():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-revision-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_revision", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_revision",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_revision_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_revision",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_revision_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            }
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    gene = core.evomemory_query_genes(scope="user", current_only=True, limit=10)[
        "genes"
    ][0]
    capsule = core.evomemory_query_capsules(scope="user", current_only=True, limit=10)[
        "capsules"
    ][0]

    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="This belief is weak and should be revised.",
    )
    revision = core.evomemory_run_revision(min_confidence=0.7)

    current_beliefs = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )
    historical_beliefs = core.evomemory_query_beliefs(
        scope="user", key="response_language", historical_only=True, limit=10
    )
    stale_genes = core.evomemory_query_genes(scope="user", stale_only=True, limit=10)
    stale_capsules = core.evomemory_query_capsules(
        scope="user", stale_only=True, limit=10
    )
    summary = core.evomemory_evaluation_summary()

    assert revision["revised_count"] == 1
    assert revision["revised_beliefs"][0]["id"] == belief["id"]
    assert current_beliefs["count"] == 0
    assert historical_beliefs["count"] == 1
    assert historical_beliefs["facts"][0]["is_stale"] is True
    assert any(
        item["id"] == gene["id"] and item["is_stale"] is True
        for item in stale_genes["genes"]
    )
    assert any(
        item["id"] == capsule["id"] and item["is_stale"] is True
        for item in stale_capsules["capsules"]
    )
    assert summary["metrics"]["revision_runs"] >= 1
    assert summary["metrics"]["revised_beliefs"] >= 1


def test_revision_removes_stale_belief_from_core_memory():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-revision-core-memory-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_revision_core", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_revision_core",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_revision_core_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_revision_core",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_revision_core_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_revision_core_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="This belief is weak and should be revised.",
    )
    revision = core.evomemory_run_revision(min_confidence=0.7)

    result = core.search_context(
        "回复",
        "/home/mechrevo/.config/opencode",
        session_id="ses_revision_core",
    )

    assert revision["invalidated_context_count"] == 1
    assert result["belief_memory_count"] == 0
    assert all(
        item.get("memory_key") != "response_language" for item in result["core_memory"]
    )


def test_revision_recovers_from_stale_context_records():
    from evomemory.context.bridge import BridgeCore, BridgeConfig
    import sqlite3

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-revision-recover-"))
    state_path = temp_dir / "state.sqlite3"
    backend = PromotionBackend()
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=backend)
    core.start_session("ses_revision_recover", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_revision_recover",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_recover_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_recover_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    with sqlite3.connect(state_path) as connection:
        connection.execute(
            "UPDATE belief_facts SET source_record_id = NULL WHERE id = ?",
            (belief["id"],),
        )
    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="This belief is weak and should be revised.",
    )
    revision = core.evomemory_run_revision(min_confidence=0.7)

    result = core.search_context(
        "回复",
        "/home/mechrevo/.config/opencode",
        session_id="ses_revision_recover",
    )

    assert revision["invalidated_context_count"] == 1
    assert revision["revised_count"] == 1
    assert result["belief_memory_count"] == 0
    assert all(
        item.get("memory_key") != "response_language" for item in result["core_memory"]
    )


def test_governance_reconcile_sweeps_stale_assets_back_to_consistent_state():
    from evomemory.context.bridge import BridgeCore, BridgeConfig
    import sqlite3

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-governance-reconcile-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_gov_reconcile", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_gov_reconcile",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_gov_reconcile_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_gov_reconcile",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_gov_reconcile_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            }
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="This belief is weak and should be revised.",
    )
    core.evomemory_run_revision(min_confidence=0.7)

    gene_id = core.evomemory_query_genes(scope="user", stale_only=True, limit=10)[
        "genes"
    ][0]["id"]
    capsule_id = core.evomemory_query_capsules(scope="user", stale_only=True, limit=10)[
        "capsules"
    ][0]["id"]

    with sqlite3.connect(state_path) as connection:
        connection.execute(
            "UPDATE genes SET is_stale = 0, demoted_at = NULL WHERE id = ?",
            (gene_id,),
        )
        connection.execute(
            "UPDATE capsules SET is_stale = 0, demoted_at = NULL WHERE id = ?",
            (capsule_id,),
        )

    assert any(
        item["id"] == gene_id
        for item in core.evomemory_query_genes(
            scope="user", current_only=True, limit=10
        )["genes"]
    )
    assert any(
        item["id"] == capsule_id
        for item in core.evomemory_query_capsules(
            scope="user", current_only=True, limit=10
        )["capsules"]
    )

    reconcile = core.evomemory_reconcile_governance()
    stale_genes = core.evomemory_query_genes(scope="user", stale_only=True, limit=10)
    stale_capsules = core.evomemory_query_capsules(
        scope="user", stale_only=True, limit=10
    )
    summary = core.evomemory_evaluation_summary()

    assert reconcile["reconciled_gene_count"] == 1
    assert reconcile["reconciled_capsule_count"] == 1
    assert any(item["id"] == gene_id for item in stale_genes["genes"])
    assert any(item["id"] == capsule_id for item in stale_capsules["capsules"])
    assert summary["metrics"]["reconciled_stale_genes"] >= 1
    assert summary["metrics"]["reconciled_stale_capsules"] >= 1


def test_revision_reconciles_historical_stale_governance_assets():
    from evomemory.context.bridge import BridgeCore, BridgeConfig
    import sqlite3

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-revision-gov-reconcile-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_revision_gov_reconcile", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_revision_gov_reconcile",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_revision_gov_reconcile_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_revision_gov_reconcile",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_revision_gov_reconcile_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            }
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="This belief is weak and should be revised.",
    )
    first_revision = core.evomemory_run_revision(min_confidence=0.7)

    gene_id = first_revision["demoted_genes"][0]["id"]
    capsule_id = first_revision["demoted_capsules"][0]["id"]
    with sqlite3.connect(state_path) as connection:
        connection.execute(
            "UPDATE genes SET is_stale = 0, demoted_at = NULL WHERE id = ?",
            (gene_id,),
        )
        connection.execute(
            "UPDATE capsules SET is_stale = 0, demoted_at = NULL WHERE id = ?",
            (capsule_id,),
        )

    revision = core.evomemory_run_revision(min_confidence=0.7)
    stale_genes = core.evomemory_query_genes(scope="user", stale_only=True, limit=10)
    stale_capsules = core.evomemory_query_capsules(
        scope="user", stale_only=True, limit=10
    )

    assert revision["revised_count"] == 0
    assert revision["reconciled_gene_count"] == 1
    assert revision["reconciled_capsule_count"] == 1
    assert any(item["id"] == gene_id for item in stale_genes["genes"])
    assert any(item["id"] == capsule_id for item in stale_capsules["capsules"])


def test_repromoting_same_value_reactivates_stale_gene_and_capsule():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-reactivate-governance-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_reactivate_governance", "/home/mechrevo/.config/opencode")

    core.flush_session(
        "ses_reactivate_governance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_reactivate_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_reactivate_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="Force this belief below revision threshold.",
    )
    core.evomemory_run_revision(min_confidence=0.7)

    assert (
        core.evomemory_query_genes(scope="user", current_only=True, limit=10)["count"]
        == 0
    )
    assert (
        core.evomemory_query_capsules(scope="user", current_only=True, limit=10)[
            "count"
        ]
        == 0
    )

    core.flush_session(
        "ses_reactivate_governance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_reactivate_3", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_reactivate_4", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )

    current_belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    current_gene = core.evomemory_query_genes(
        scope="user", current_only=True, limit=10
    )["genes"][0]
    current_capsule = core.evomemory_query_capsules(
        scope="user", current_only=True, limit=10
    )["capsules"][0]

    assert current_gene["source_fact_id"] == current_belief["id"]
    assert current_gene["is_stale"] is False
    assert current_gene["demoted_at"] is None
    assert current_capsule["is_stale"] is False
    assert current_capsule["demoted_at"] is None
    assert current_capsule["gene_ids"] == [current_gene["id"]]


def test_current_capsule_hides_stale_gene_ids_after_superseded_belief():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-capsule-current-gene-ids-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session(
        "ses_capsule_current_gene_ids", "/home/mechrevo/.config/opencode"
    )

    core.flush_session(
        "ses_capsule_current_gene_ids",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_capsule_gene_ids_1", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
            {
                "info": {"id": "msg_capsule_gene_ids_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
            {
                "info": {"id": "msg_capsule_gene_ids_3", "role": "user"},
                "parts": [{"type": "text", "text": "这个项目里每次都要跑测试"}],
            },
            {
                "info": {"id": "msg_capsule_gene_ids_4", "role": "user"},
                "parts": [{"type": "text", "text": "这个项目里记得跑测试"}],
            },
            {
                "info": {"id": "msg_capsule_gene_ids_5", "role": "user"},
                "parts": [{"type": "text", "text": "这个项目里必须 git commit"}],
            },
            {
                "info": {"id": "msg_capsule_gene_ids_6", "role": "user"},
                "parts": [{"type": "text", "text": "这个项目里必须要 git commit"}],
            },
        ],
        reason="idle",
    )

    current_genes = core.evomemory_query_genes(
        scope="project", current_only=True, limit=10
    )
    stale_genes = core.evomemory_query_genes(scope="project", stale_only=True, limit=10)
    current_capsule = core.evomemory_query_capsules(
        scope="project", current_only=True, limit=10
    )["capsules"][0]

    stale_git_commit_gene = next(
        item
        for item in stale_genes["genes"]
        if item["key"] == "git_commit_behavior" and item["value"] == "disabled"
    )

    assert current_capsule["is_stale"] is False
    assert set(current_capsule["gene_ids"]) == {
        item["id"] for item in current_genes["genes"]
    }
    assert stale_git_commit_gene["id"] not in current_capsule["gene_ids"]


def test_revision_self_heals_missing_current_governance_assets_for_current_beliefs():
    from evomemory.context.bridge import BridgeCore, BridgeConfig
    import sqlite3

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-governance-self-heal-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_governance_self_heal", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_governance_self_heal",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_self_heal_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_self_heal_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_governance_self_heal",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_self_heal_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_self_heal_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
            {
                "info": {"id": "msg_self_heal_3", "role": "user"},
                "parts": [
                    {
                        "type": "text",
                        "text": "这个项目里还是不要自动提交 git commit",
                    }
                ],
            },
        ],
        reason="idle",
    )

    with sqlite3.connect(state_path) as connection:
        connection.execute(
            "UPDATE genes SET is_stale = 1, demoted_at = CURRENT_TIMESTAMP WHERE scope = ? AND key = ?",
            ("project", "git_commit_behavior"),
        )
        connection.execute(
            "UPDATE capsules SET is_stale = 1, demoted_at = CURRENT_TIMESTAMP WHERE scope = ?",
            ("project",),
        )

    before_genes = core.evomemory_query_genes(
        scope="project", key="git_commit_behavior", current_only=True, limit=10
    )
    before_capsules = core.evomemory_query_capsules(
        scope="project", current_only=True, limit=10
    )
    assert before_genes["count"] == 0
    assert before_capsules["count"] == 0

    core.evomemory_run_revision(min_confidence=0.7)

    after_genes = core.evomemory_query_genes(
        scope="project", key="git_commit_behavior", current_only=True, limit=10
    )
    after_capsules = core.evomemory_query_capsules(
        scope="project", current_only=True, limit=10
    )

    assert after_genes["count"] == 1
    assert after_genes["genes"][0]["is_stale"] is False
    assert after_genes["genes"][0]["demoted_at"] is None
    assert after_capsules["count"] == 1
    assert after_capsules["capsules"][0]["is_stale"] is False
    assert after_capsules["capsules"][0]["demoted_at"] is None


def test_compact_flush_self_heals_missing_current_governance_assets():
    from evomemory.context.bridge import BridgeCore, BridgeConfig
    import sqlite3

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-compact-self-heal-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_compact_self_heal", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_compact_self_heal",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_compact_self_heal_1", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
            {
                "info": {"id": "msg_compact_self_heal_2", "role": "user"},
                "parts": [
                    {
                        "type": "text",
                        "text": "这个项目里还是不要自动提交 git commit",
                    }
                ],
            },
        ],
        reason="idle",
    )

    with sqlite3.connect(state_path) as connection:
        connection.execute(
            "UPDATE genes SET is_stale = 1, demoted_at = CURRENT_TIMESTAMP WHERE scope = ? AND key = ?",
            ("project", "git_commit_behavior"),
        )
        connection.execute(
            "UPDATE capsules SET is_stale = 1, demoted_at = CURRENT_TIMESTAMP WHERE scope = ?",
            ("project",),
        )

    core.flush_session(
        "ses_compact_self_heal",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_compact_self_heal_3", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "我已经确认这轮 compact 需要顺手校正治理资产。",
                    }
                ],
            }
        ],
        reason="compact",
    )

    after_genes = core.evomemory_query_genes(
        scope="project", key="git_commit_behavior", current_only=True, limit=10
    )
    after_capsules = core.evomemory_query_capsules(
        scope="project", current_only=True, limit=10
    )

    assert after_genes["count"] == 1
    assert after_genes["genes"][0]["demoted_at"] is None
    assert after_capsules["count"] == 1
    assert after_capsules["capsules"][0]["demoted_at"] is None


def test_compact_flush_triggers_revision_maintenance_for_low_confidence_beliefs():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-auto-maintenance-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_auto_maintenance", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_auto_maintenance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_auto_maintenance_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_auto_maintenance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_auto_maintenance_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            }
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="This belief should be revised.",
    )
    before_revision_runs = core.evomemory_evaluation_summary()["metrics"].get(
        "revision_runs", 0
    )

    result = core.flush_session(
        "ses_auto_maintenance",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_auto_maintenance_3", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "我已经确认当前会话需要在空闲后自动维护。",
                    }
                ],
            }
        ],
        reason="compact",
    )

    current_beliefs = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )
    historical_beliefs = core.evomemory_query_beliefs(
        scope="user", key="response_language", historical_only=True, limit=10
    )
    summary = core.evomemory_evaluation_summary()

    assert result["saved"] == 1
    assert summary["metrics"]["revision_runs"] == before_revision_runs + 1
    assert current_beliefs["count"] == 0
    assert historical_beliefs["count"] == 1
    assert summary["maintenance_summary"]["last_revision_at"] is not None
    assert summary["maintenance_summary"]["last_revision_revised_count"] == 1


def test_compact_flush_reconciles_stale_governance_assets():
    from evomemory.context.bridge import BridgeCore, BridgeConfig
    import sqlite3

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-auto-reconcile-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_auto_reconcile", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_auto_reconcile",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_auto_reconcile_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_auto_reconcile",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_auto_reconcile_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            }
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="This belief should be revised.",
    )
    revision = core.evomemory_run_revision(min_confidence=0.7)
    gene_id = revision["demoted_genes"][0]["id"]
    capsule_id = revision["demoted_capsules"][0]["id"]
    with sqlite3.connect(state_path) as connection:
        connection.execute(
            "UPDATE genes SET is_stale = 0, demoted_at = NULL WHERE id = ?",
            (gene_id,),
        )
        connection.execute(
            "UPDATE capsules SET is_stale = 0, demoted_at = NULL WHERE id = ?",
            (capsule_id,),
        )
    before_reconcile_runs = core.evomemory_evaluation_summary()["metrics"].get(
        "reconcile_runs", 0
    )

    result = core.flush_session(
        "ses_auto_reconcile",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_auto_reconcile_3", "role": "assistant"},
                "parts": [
                    {
                        "type": "text",
                        "text": "我已经确认治理资产需要在 compact 时自动校正。",
                    }
                ],
            }
        ],
        reason="compact",
    )

    stale_genes = core.evomemory_query_genes(scope="user", stale_only=True, limit=10)
    stale_capsules = core.evomemory_query_capsules(
        scope="user", stale_only=True, limit=10
    )
    summary = core.evomemory_evaluation_summary()

    assert result["saved"] == 1
    assert summary["metrics"].get("reconcile_runs", 0) == before_reconcile_runs + 1
    assert any(item["id"] == gene_id for item in stale_genes["genes"])
    assert any(item["id"] == capsule_id for item in stale_capsules["capsules"])
    assert summary["maintenance_summary"]["last_reconcile_at"] is not None
    assert summary["maintenance_summary"]["last_reconcile_gene_count"] == 1
    assert summary["maintenance_summary"]["last_reconcile_capsule_count"] == 1


def test_evaluation_summary_includes_maintenance_snapshot():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-maintenance-summary-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_maintenance_summary", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_maintenance_summary",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_maintenance_summary_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_maintenance_summary",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_maintenance_summary_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            }
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="This belief is weak and should be revised.",
    )
    revision = core.evomemory_run_revision(min_confidence=0.7)
    summary = core.evomemory_evaluation_summary()

    assert summary["maintenance_summary"]["plane"] == "maintenance"
    assert summary["maintenance_summary"]["service"] == "evomemory"
    assert summary["maintenance_summary"]["updated_at"] is not None
    assert summary["maintenance_summary"]["revision_runs"] >= 1
    assert summary["maintenance_summary"]["revised_beliefs"] >= 1
    assert summary["maintenance_summary"]["revised_context_memories"] >= 1
    assert summary["maintenance_summary"]["stale_belief_count"] >= 1
    assert summary["maintenance_summary"]["stale_gene_count"] >= 1
    assert summary["maintenance_summary"]["stale_capsule_count"] >= 1
    assert summary["maintenance_summary"]["last_revision_at"] is not None
    assert (
        summary["maintenance_summary"]["last_revision_revised_count"]
        == revision["revised_count"]
    )


def test_maintenance_summary_exposes_status_and_runtime_fields():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-maintenance-status-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())

    summary = core.maintenance_summary()

    assert summary["plane"] == "maintenance"
    assert summary["service"] == "evomemory"
    assert summary["revision_runs"] == 0
    assert summary["reconcile_runs"] == 0
    assert summary["stale_belief_count"] == 0
    assert summary["stale_gene_count"] == 0
    assert summary["stale_capsule_count"] == 0
    assert summary["updated_at"] is None
    assert summary["last_revision_at"] is None
    assert summary["last_reconcile_at"] is None


def test_maintenance_summary_persists_revision_runtime_across_restart():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-maintenance-restart-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session(
        "ses_maintenance_restart_revision", "/home/mechrevo/.config/opencode"
    )
    core.flush_session(
        "ses_maintenance_restart_revision",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_maintenance_restart_revision_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_maintenance_restart_revision_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="Force revision before restart.",
    )
    core.evomemory_run_revision(min_confidence=0.7)
    before = core.maintenance_summary()

    restarted = BridgeCore(
        BridgeConfig(state_path=state_path), backend=PromotionBackend()
    )
    after = restarted.maintenance_summary()

    assert before["last_revision_at"] is not None
    assert after["last_revision_at"] == before["last_revision_at"]
    assert after["last_revision_revised_count"] == before["last_revision_revised_count"]
    assert after["updated_at"] == before["updated_at"]


def test_maintenance_summary_persists_reconcile_runtime_across_restart():
    from evomemory.context.bridge import BridgeCore, BridgeConfig
    import sqlite3

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-maintenance-reconcile-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session(
        "ses_maintenance_restart_reconcile", "/home/mechrevo/.config/opencode"
    )
    core.flush_session(
        "ses_maintenance_restart_reconcile",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_maintenance_restart_reconcile_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_maintenance_restart_reconcile_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
        ],
        reason="idle",
    )

    belief = core.evomemory_query_beliefs(
        scope="user", key="response_language", current_only=True, limit=10
    )["facts"][0]
    core.evomemory_record_feedback(
        target_kind="belief",
        target_id=belief["id"],
        signal="correct",
        note="Force reconcile before restart.",
    )
    revision = core.evomemory_run_revision(min_confidence=0.7)
    gene_id = revision["demoted_genes"][0]["id"]
    capsule_id = revision["demoted_capsules"][0]["id"]
    with sqlite3.connect(state_path) as connection:
        connection.execute(
            "UPDATE genes SET is_stale = 0, demoted_at = NULL WHERE id = ?",
            (gene_id,),
        )
        connection.execute(
            "UPDATE capsules SET is_stale = 0, demoted_at = NULL WHERE id = ?",
            (capsule_id,),
        )

    core.flush_session(
        "ses_maintenance_restart_reconcile",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {
                    "id": "msg_maintenance_restart_reconcile_3",
                    "role": "assistant",
                },
                "parts": [
                    {
                        "type": "text",
                        "text": "我已经确认治理资产需要在 compact 时自动校正。",
                    }
                ],
            }
        ],
        reason="compact",
    )
    before = core.maintenance_summary()

    restarted = BridgeCore(
        BridgeConfig(state_path=state_path), backend=PromotionBackend()
    )
    after = restarted.maintenance_summary()

    assert before["last_reconcile_at"] is not None
    assert after["last_reconcile_at"] == before["last_reconcile_at"]
    assert after["last_reconcile_gene_count"] == before["last_reconcile_gene_count"]
    assert (
        after["last_reconcile_capsule_count"] == before["last_reconcile_capsule_count"]
    )
    assert after["updated_at"] == before["updated_at"]


def test_governance_scores_and_stale_detection_are_tracked():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-score-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_score", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_score",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_score_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_score",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_score_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_score",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_score_3", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用英文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_score",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_score_4", "role": "user"},
                "parts": [{"type": "text", "text": "默认以后都用英文回复"}],
            }
        ],
        reason="idle",
    )
    core.search_context(
        "回复",
        "/home/mechrevo/.config/opencode",
        session_id="ses_score",
    )

    genes = core.evomemory_query_genes(limit=10)
    capsules = core.evomemory_query_capsules(limit=10)
    historical_beliefs = core.evomemory_query_beliefs(
        scope="user", key="response_language", historical_only=True
    )
    summary = core.evomemory_evaluation_summary()

    assert any(item.get("score", 0) > 0 for item in genes["genes"])
    assert any(item.get("score", 0) > 0 for item in capsules["capsules"])
    assert historical_beliefs["facts"][0].get("is_stale") is True
    stale_genes = [item for item in genes["genes"] if item.get("is_stale") is True]
    assert stale_genes
    assert summary["metrics"]["stale_beliefs"] >= 1
    assert summary["metrics"]["gene_score_updates"] >= 1
    assert summary["metrics"]["capsule_score_updates"] >= 1
    assert summary["metrics"]["gene_demotions"] >= 1


def test_governance_queries_support_scope_and_stale_filters():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-governance-filter-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_gov_filter", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_gov_filter",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_user_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_proj_1", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_gov_filter",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_user_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_proj_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_gov_filter",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_user_3", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用英文回复"}],
            }
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_gov_filter",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_user_4", "role": "user"},
                "parts": [{"type": "text", "text": "默认以后都用英文回复"}],
            },
        ],
        reason="idle",
    )

    stale_user_genes = core.evomemory_query_genes(
        scope="user", stale_only=True, limit=10
    )
    current_user_genes = core.evomemory_query_genes(
        scope="user", current_only=True, limit=10
    )
    project_capsules = core.evomemory_query_capsules(
        scope="project", current_only=True, limit=10
    )

    assert stale_user_genes["count"] >= 1
    assert all(
        item["scope"] == "user" and item["is_stale"] is True
        for item in stale_user_genes["genes"]
    )
    assert current_user_genes["count"] >= 1
    assert all(
        item["scope"] == "user" and item["is_stale"] is False
        for item in current_user_genes["genes"]
    )
    assert project_capsules["count"] == 1
    assert project_capsules["capsules"][0]["scope"] == "project"
    assert project_capsules["capsules"][0]["is_stale"] is False


def test_retention_dry_run_reports_candidates_without_deleting_current_or_referenced_drawers():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-retention-dry-run-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())

    backend = core.repository.backend
    backend.save_entry(
        wing="opencode",
        room="opencode-session",
        content="User:\n以后都用中文回复",
        source_file="session:ses_retention",
        metadata={
            "session_id": "ses_retention",
            "message_id": "msg_retention_hist",
            "role": "user",
            "memory_tier": "user_preference",
            "memory_key": "response_language",
            "memory_value": "zh-cn",
            "valid_from": "2026-01-01T00:00:00+00:00",
            "valid_to": "2026-01-02T00:00:00+00:00",
            "filed_at": "2026-01-01T00:00:00+00:00",
        },
    )
    referenced = backend.save_entry(
        wing="opencode",
        room="opencode-session",
        content="User:\n这个项目里不要自动提交 git commit",
        source_file="session:ses_retention",
        metadata={
            "session_id": "ses_retention",
            "message_id": "msg_retention_ref",
            "role": "user",
            "memory_tier": "project_memory",
            "memory_key": "git_commit_behavior",
            "memory_value": "disabled",
            "valid_from": "2026-01-03T00:00:00+00:00",
            "filed_at": "2026-01-03T00:00:00+00:00",
        },
    )
    core.promoter.promote_saved_memory(
        scope="project",
        memory_tier="project_memory",
        memory_key="git_commit_behavior",
        memory_value="disabled",
        source_session="ses_retention",
        source_message_id="msg_retention_ref",
        source_record_id=referenced["drawer_id"],
        valid_from="2026-01-03T00:00:00+00:00",
        initial_source_count=2,
    )
    backend.save_entry(
        wing="opencode",
        room="opencode-session",
        content="Assistant:\nWorking note kept current.",
        source_file="session:ses_retention",
        metadata={
            "session_id": "ses_retention",
            "message_id": "msg_retention_current",
            "role": "assistant",
            "memory_tier": "working_session",
            "valid_from": "2026-01-04T00:00:00+00:00",
            "filed_at": "2026-01-04T00:00:00+00:00",
        },
    )

    result = core.evomemory_run_retention(
        dry_run=True,
        safe=True,
        window_days=30,
    )

    assert result["dry_run"] is True
    assert result["safe"] is True
    assert result["candidate_count"] == 3
    assert result["protected_current_count"] == 2
    assert result["protected_referenced_count"] == 1
    assert result["purgeable_count"] == 1
    assert result["deleted_count"] == 0
    assert len(backend.saved_entries) == 3


def test_retention_safe_purge_deletes_only_unreferenced_historical_drawers():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-retention-safe-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())

    backend = core.repository.backend
    historical = backend.save_entry(
        wing="opencode",
        room="opencode-session",
        content="User:\n以后都用中文回复",
        source_file="session:ses_retention_safe",
        metadata={
            "session_id": "ses_retention_safe",
            "message_id": "msg_retention_safe_hist",
            "role": "user",
            "memory_tier": "user_preference",
            "memory_key": "response_language",
            "memory_value": "zh-cn",
            "valid_from": "2026-01-01T00:00:00+00:00",
            "valid_to": "2026-01-02T00:00:00+00:00",
            "filed_at": "2026-01-01T00:00:00+00:00",
        },
    )
    referenced = backend.save_entry(
        wing="opencode",
        room="opencode-session",
        content="User:\n这个项目里不要自动提交 git commit",
        source_file="session:ses_retention_safe",
        metadata={
            "session_id": "ses_retention_safe",
            "message_id": "msg_retention_safe_ref",
            "role": "user",
            "memory_tier": "project_memory",
            "memory_key": "git_commit_behavior",
            "memory_value": "disabled",
            "valid_from": "2026-01-03T00:00:00+00:00",
            "valid_to": "2026-01-04T00:00:00+00:00",
            "filed_at": "2026-01-03T00:00:00+00:00",
        },
    )
    core.promoter.promote_saved_memory(
        scope="project",
        memory_tier="project_memory",
        memory_key="git_commit_behavior",
        memory_value="disabled",
        source_session="ses_retention_safe",
        source_message_id="msg_retention_safe_ref",
        source_record_id=referenced["drawer_id"],
        valid_from="2026-01-05T00:00:00+00:00",
        initial_source_count=2,
    )

    result = core.evomemory_run_retention(dry_run=False, safe=True, window_days=30)
    remaining_ids = {entry["drawer_id"] for entry in backend.saved_entries}

    assert result["deleted_count"] == 1
    assert result["deleted_drawer_ids"] == [historical["drawer_id"]]
    assert historical["drawer_id"] not in remaining_ids
    assert referenced["drawer_id"] in remaining_ids


def test_retention_can_purge_old_current_drawers_when_safe_mode_is_disabled():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-retention-unsafe-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())

    backend = core.repository.backend
    current = backend.save_entry(
        wing="opencode",
        room="opencode-session",
        content="Assistant:\nOld working session note.",
        source_file="session:ses_retention_unsafe",
        metadata={
            "session_id": "ses_retention_unsafe",
            "message_id": "msg_retention_unsafe_current",
            "role": "assistant",
            "memory_tier": "working_session",
            "valid_from": "2026-01-01T00:00:00+00:00",
            "filed_at": "2026-01-01T00:00:00+00:00",
        },
    )

    result = core.evomemory_run_retention(dry_run=False, safe=False, window_days=30)

    assert result["safe"] is False
    assert result["deleted_drawer_ids"] == [current["drawer_id"]]
    assert core.repository.get_drawer(current["drawer_id"]) is None


def test_retention_safe_mode_does_not_preserve_drawers_only_referenced_by_historical_events():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-retention-event-history-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())

    backend = core.repository.backend
    historical = backend.save_entry(
        wing="opencode",
        room="opencode-session",
        content="User:\n这个项目里不要自动提交 git commit",
        source_file="session:ses_retention_event_history",
        metadata={
            "session_id": "ses_retention_event_history",
            "message_id": "msg_retention_event_history_1",
            "role": "user",
            "memory_tier": "project_memory",
            "memory_key": "git_commit_behavior",
            "memory_value": "disabled",
            "valid_from": "2026-01-01T00:00:00+00:00",
            "valid_to": "2026-01-02T00:00:00+00:00",
            "filed_at": "2026-01-01T00:00:00+00:00",
        },
    )
    core.promoter.promote_saved_memory(
        scope="project",
        memory_tier="project_memory",
        memory_key="git_commit_behavior",
        memory_value="disabled",
        source_session="ses_retention_event_history",
        source_message_id="msg_retention_event_history_1",
        source_record_id=historical["drawer_id"],
        valid_from="2026-01-01T00:00:00+00:00",
    )
    core.promoter.promote_saved_memory(
        scope="project",
        memory_tier="project_memory",
        memory_key="git_commit_behavior",
        memory_value="confirm_first",
        source_session="ses_retention_event_history",
        source_message_id="msg_retention_event_history_2",
        source_record_id=None,
        valid_from="2026-01-03T00:00:00+00:00",
    )

    result = core.evomemory_run_retention(dry_run=False, safe=True, window_days=30)
    events = core.evomemory_list_evolution_events(limit=20)
    timeline = core.evomemory_query_timeline(
        scope="project",
        key="git_commit_behavior",
        limit=20,
    )

    assert result["deleted_drawer_ids"] == [historical["drawer_id"]]
    assert core.repository.get_drawer(historical["drawer_id"]) is None
    assert any(
        item.get("source_record_id") == historical["drawer_id"]
        for item in events["events"]
    )
    assert {item["action"] for item in timeline["events"]} >= {"promote", "supersede"}


def test_maintenance_summary_exposes_retention_runtime_fields():
    from evomemory.context.bridge import BridgeCore, BridgeConfig

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-retention-summary-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())

    backend = core.repository.backend
    backend.save_entry(
        wing="opencode",
        room="opencode-session",
        content="Assistant:\nHistorical summary.",
        source_file="session:ses_retention_summary",
        metadata={
            "session_id": "ses_retention_summary",
            "message_id": "msg_retention_summary",
            "role": "assistant",
            "memory_tier": "working_session",
            "valid_from": "2026-01-01T00:00:00+00:00",
            "valid_to": "2026-01-02T00:00:00+00:00",
            "filed_at": "2026-01-01T00:00:00+00:00",
        },
    )

    before = core.evomemory_run_retention(dry_run=True, safe=True, window_days=30)
    after = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    summary = after.maintenance_summary()

    assert before["maintenance_summary"]["last_retention_at"] is not None
    assert (
        summary["last_retention_at"]
        == before["maintenance_summary"]["last_retention_at"]
    )
    assert summary["last_retention_window_days"] == 30
    assert summary["last_retention_candidate_count"] == 1
    assert summary["last_retention_purgeable_count"] == 1
    assert summary["last_retention_deleted_count"] == 0
    assert summary["last_retention_safe"] is True
    assert summary["last_retention_dry_run"] is True
    assert summary["updated_at"] == summary["last_retention_at"]


def test_canonical_modules_live_under_evomemory_namespace():
    from evomemory.context.bridge import BridgeConfig, BridgeCore, EvoMemoryBackend
    from evomemory.domain.memory_policy import classify_memory_tier
    from evomemory.infrastructure.state.session_state import SessionStateStore
    from evomemory.interfaces.mcp.server import create_app

    assert BridgeConfig.__module__ == "evomemory.context.bridge"
    assert BridgeCore.__module__ == "evomemory.context.bridge"
    assert EvoMemoryBackend.__module__ == "evomemory.context.bridge"
    assert classify_memory_tier.__module__ == "evomemory.domain.memory_policy"
    assert (
        SessionStateStore.__module__ == "evomemory.infrastructure.state.session_state"
    )
    assert create_app.__module__ == "evomemory.interfaces.mcp.server"


def test_server_parse_args_supports_stdio_transport():
    import sys

    from evomemory.interfaces.mcp.server import parse_args

    original = list(sys.argv)
    try:
        sys.argv = ["server.py", "--transport", "stdio"]
        args = parse_args()
    finally:
        sys.argv = original

    assert args.transport == "stdio"
