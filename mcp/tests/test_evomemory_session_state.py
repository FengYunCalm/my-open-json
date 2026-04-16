from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evomemory.infrastructure.state.session_state import SessionStateStore


def test_session_state_store_persists_sessions_across_instances():
    temp_dir = Path(tempfile.mkdtemp(prefix="mempalace-session-state-"))
    state_path = temp_dir / "state.sqlite3"

    writer = SessionStateStore(state_path)
    writer.save(
        {
            "sessions": {
                "ses_demo": {
                    "directory": "/workspace/demo",
                    "wing": "demo",
                    "last_saved_message_id": "msg_001",
                    "last_saved_signature": "msg_001:msg_002",
                    "last_saved_order": 2,
                    "last_saved_at": "2026-04-15T00:00:00+00:00",
                }
            }
        }
    )

    reader = SessionStateStore(state_path)
    state = reader.load()

    assert state["sessions"]["ses_demo"]["wing"] == "demo"
    assert state["sessions"]["ses_demo"]["last_saved_order"] == 2
    assert state["sessions"]["ses_demo"]["last_saved_signature"] == "msg_001:msg_002"


def test_session_state_store_migrates_legacy_json_payload():
    temp_dir = Path(tempfile.mkdtemp(prefix="mempalace-session-state-legacy-"))
    state_path = temp_dir / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "sessions": {
                    "ses_legacy": {
                        "directory": "/workspace/legacy",
                        "wing": "legacy",
                        "last_saved_message_id": "msg_legacy",
                        "last_saved_order": 9,
                        "last_saved_at": "2026-04-14T23:59:59+00:00",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    store = SessionStateStore(state_path)
    state = store.load()

    assert state["sessions"]["ses_legacy"]["wing"] == "legacy"
    assert state["sessions"]["ses_legacy"]["last_saved_order"] == 9
    assert state_path.with_suffix(".json.bak").exists()
