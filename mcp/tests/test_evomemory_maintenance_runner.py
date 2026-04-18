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
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )

    result = core.evomemory_run_maintenance(profile="full", limit=10)
    summary = core.maintenance_summary()

    assert result["profile"] == "full"
    assert result["snapshot"]["service"] == "evomemory"
    assert result["benchmark"]["limit"] == 10
    assert summary["last_maintenance_at"] is not None
    assert summary["last_maintenance_profile"] == "full"
