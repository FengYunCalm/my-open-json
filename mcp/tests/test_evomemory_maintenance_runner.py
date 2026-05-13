from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_evomemory_package import PromotionBackend


def test_run_maintenance_light_wraps_revision_and_persists_runtime_summary():
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-maintenance-light-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_maintenance_light", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_maintenance_light",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_maintenance_light_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_maintenance_light_2", "role": "user"},
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
        note="Force maintenance revision.",
    )

    result = core.evomemory_run_maintenance(profile="light", min_confidence=0.7)
    summary = core.maintenance_summary()

    assert result["profile"] == "light"
    assert result["revision"]["revised_count"] == 1
    assert result["snapshot"] is None
    assert result["benchmark"] is None
    assert summary["last_maintenance_at"] is not None
    assert summary["last_maintenance_profile"] == "light"


def test_run_maintenance_full_includes_snapshot_and_benchmark():
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-maintenance-full-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_maintenance_full", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_maintenance_full",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_maintenance_full_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_maintenance_full_2", "role": "user"},
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
        note="Force maintenance revision.",
    )

    result = core.evomemory_run_maintenance(profile="full", min_confidence=0.7)
    summary = core.maintenance_summary()

    assert result["profile"] == "full"
    assert result["revision"]["revised_count"] == 1
    assert result["snapshot"] is not None
    assert result["benchmark"] is not None
    assert summary["last_maintenance_at"] is not None
    assert summary["last_maintenance_profile"] == "full"


TEST_DIRECTORY = "/home/mechrevo/.config/opencode"
RETENTION_STALE_FROM = "2020-01-01T00:00:00+00:00"
RETENTION_STALE_TO = "2020-01-02T00:00:00+00:00"
RETENTION_BELIEF_FROM = "2024-01-01T00:00:00+00:00"



def _make_retention_core(prefix: str):
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    temp_dir = Path(tempfile.mkdtemp(prefix=f"evomemory-{prefix}-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    session_id = f"ses_{prefix}"
    core.start_session(session_id, TEST_DIRECTORY)
    return core, session_id



def _save_retention_drawer(
    core,
    *,
    session_id: str,
    message_id: str,
    text: str,
    valid_to: str | None,
):
    return core.repository.save_entry(
        wing="opencode",
        room="opencode-session",
        content=f"User:\n{text}",
        source_file=f"session:{session_id}",
        metadata={
            "type": "opencode_message",
            "session_id": session_id,
            "message_id": message_id,
            "role": "user",
            "reason": "idle",
            "directory": TEST_DIRECTORY,
            "memory_tier": "project_memory",
            "memory_key": f"task8_{message_id}",
            "memory_value": text,
            "dedupe_hash": None,
            "valid_from": RETENTION_STALE_FROM,
            "valid_to": valid_to,
            "session_order": 1,
        },
    )



def _build_retention_fixture(prefix: str) -> dict[str, object]:
    core, session_id = _make_retention_core(prefix)
    purgeable = _save_retention_drawer(
        core,
        session_id=session_id,
        message_id="task8_purgeable",
        text="Purge this stale historical drawer",
        valid_to=RETENTION_STALE_TO,
    )
    current = _save_retention_drawer(
        core,
        session_id=session_id,
        message_id="task8_current_protected",
        text="Keep this stale current drawer",
        valid_to=None,
    )
    referenced = _save_retention_drawer(
        core,
        session_id=session_id,
        message_id="task8_referenced_protected",
        text="Keep this stale referenced drawer",
        valid_to=RETENTION_STALE_TO,
    )
    belief = core.promoter.promote_saved_memory(
        scope="project",
        memory_tier="project_memory",
        memory_key="task8_reference_guard",
        memory_value="protect referenced drawer",
        source_session=session_id,
        source_message_id="task8_referenced_protected",
        source_record_id=referenced["drawer_id"],
        valid_from=RETENTION_BELIEF_FROM,
    )["belief"]
    return {
        "core": core,
        "belief": belief,
        "purgeable_drawer_id": purgeable["drawer_id"],
        "current_drawer_id": current["drawer_id"],
        "referenced_drawer_id": referenced["drawer_id"],
        "candidate_drawer_ids": {
            purgeable["drawer_id"],
            current["drawer_id"],
            referenced["drawer_id"],
        },
    }



def test_retention_dry_run_audits_protected_and_purgeable_candidates():
    fixture = _build_retention_fixture("retention-dry-run")
    core = fixture["core"]
    current_drawer_id = fixture["current_drawer_id"]
    referenced_drawer_id = fixture["referenced_drawer_id"]
    purgeable_drawer_id = fixture["purgeable_drawer_id"]

    assert core.repository.get_drawer(current_drawer_id) is not None
    assert core.repository.get_drawer(referenced_drawer_id) is not None
    assert fixture["belief"]["source_record_id"] == referenced_drawer_id

    result_dry = core.evomemory_run_retention(dry_run=True, safe=True, window_days=0)

    assert result_dry["dry_run"] is True
    assert result_dry["safe"] is True
    assert result_dry["window_days"] == 0
    assert result_dry["candidate_count"] == 3
    assert set(result_dry["candidate_drawer_ids"]) == fixture["candidate_drawer_ids"]
    assert result_dry["purgeable_count"] == 1
    assert result_dry["purgeable_drawer_ids"] == [purgeable_drawer_id]
    assert result_dry["protected_current_drawer_ids"] == [current_drawer_id]
    assert result_dry["protected_referenced_drawer_ids"] == [referenced_drawer_id]
    assert result_dry["deleted_count"] == 0
    assert result_dry["deleted_drawer_ids"] == []
    assert result_dry["audit_events"]
    assert len(result_dry["audit_events"]) == 3
    assert result_dry["rollback_available"] is False
    assert result_dry["rollback_location"] is None

    audit_events_by_target = {
        event["target_id"]: event for event in result_dry["audit_events"]
    }
    assert audit_events_by_target[purgeable_drawer_id]["action"] == "retention_dry_run"
    assert audit_events_by_target[current_drawer_id]["action"] == "retention_protect"
    assert audit_events_by_target[referenced_drawer_id]["action"] == "retention_protect"
    for event in result_dry["audit_events"]:
        assert event["target_kind"] == "context_drawer"
        assert event["target_id"]
        assert event["rationale"]
        assert event["source_record_id"]
        assert event["created_at"]



def test_retention_safe_delete_removes_only_purgeable_drawers():
    fixture = _build_retention_fixture("retention-delete")
    core = fixture["core"]
    current_drawer_id = fixture["current_drawer_id"]
    referenced_drawer_id = fixture["referenced_drawer_id"]
    purgeable_drawer_id = fixture["purgeable_drawer_id"]

    assert core.repository.get_drawer(purgeable_drawer_id) is not None
    assert core.repository.get_drawer(current_drawer_id) is not None
    assert core.repository.get_drawer(referenced_drawer_id) is not None
    assert fixture["belief"]["source_record_id"] == referenced_drawer_id

    result_delete = core.evomemory_run_retention(dry_run=False, safe=True, window_days=0)

    assert result_delete["dry_run"] is False
    assert result_delete["safe"] is True
    assert result_delete["candidate_count"] == 3
    assert result_delete["purgeable_count"] == 1
    assert result_delete["purgeable_drawer_ids"] == [purgeable_drawer_id]
    assert result_delete["protected_current_drawer_ids"] == [current_drawer_id]
    assert result_delete["protected_referenced_drawer_ids"] == [referenced_drawer_id]
    assert result_delete["deleted_count"] == 1
    assert result_delete["deleted_drawer_ids"] == [purgeable_drawer_id]
    assert result_delete["rollback_available"] is False
    assert result_delete["rollback_location"] is None
    assert core.repository.get_drawer(purgeable_drawer_id) is None
    assert core.repository.get_drawer(current_drawer_id) is not None
    assert core.repository.get_drawer(referenced_drawer_id) is not None
