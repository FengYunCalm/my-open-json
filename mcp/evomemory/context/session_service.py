from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class SessionLifecycleService:
    def __init__(self, core: Any):
        self.core = core

    def start_session(self, session_id: str, directory: str) -> dict[str, Any]:
        state = self.core._load_state()
        sessions = state.setdefault("sessions", {})
        entry = sessions.setdefault(session_id, {})
        entry["directory"] = self.core._normalize_directory(directory)
        entry["wing"] = self.core.resolve_wing(directory)
        entry.setdefault("last_saved_message_id", None)
        entry.setdefault("last_saved_order", 0)
        self.core._save_state(state)
        return {
            "session_id": session_id,
            "wing": entry["wing"],
            "directory": entry["directory"],
        }

    def flush_session(
        self,
        session_id: str,
        directory: str,
        messages: list[dict[str, Any]],
        reason: str,
    ) -> dict[str, Any]:
        state = self.core._load_state()
        sessions = state.setdefault("sessions", {})
        session = sessions.setdefault(session_id, {})
        session.setdefault("directory", self.core._normalize_directory(directory))
        session.setdefault("wing", self.core.resolve_wing(directory))
        session.setdefault("last_saved_order", 0)
        new_messages = self.core._new_messages(
            messages, session.get("last_saved_message_id")
        )
        saved = []
        next_order = int(session.get("last_saved_order") or 0)
        existing_working_hashes = {
            item.get("dedupe_hash")
            for item in self.core.repository.get_session_messages(
                session_id=session_id,
                memory_tier="working_session",
                current_only=True,
                limit=1000,
                offset=0,
            )
            if item.get("dedupe_hash")
        }

        for message in new_messages:
            info = message.get("info", {})
            role = info.get("role")
            if role not in self.core.valid_roles:
                continue
            text = self.core._collect_text(message.get("parts", []))
            if not self.core._is_meaningful_text(text):
                continue
            next_order += 1
            content = f"{role.title()}:\n{text}"
            memory_tier = self.core.classify_memory_tier(role, text)
            memory_key = self.core.derive_memory_key(memory_tier, text)
            memory_value = self.core.derive_memory_value(memory_key, text)
            dedupe_hash = None
            filed_at = datetime.now(timezone.utc).isoformat()
            if memory_key and memory_tier in {"user_preference", "project_memory"}:
                revision = self.core.reviser.revise_memory(
                    wing=session["wing"],
                    directory=session["directory"],
                    memory_tier=memory_tier,
                    memory_key=memory_key,
                    memory_value=memory_value,
                    valid_to=filed_at,
                )
                if revision["skip_save"]:
                    scope = "user" if memory_tier == "user_preference" else "project"
                    self.core.promoter.promote_saved_memory(
                        scope=scope,
                        memory_tier=memory_tier,
                        memory_key=memory_key,
                        memory_value=memory_value,
                        source_session=session_id,
                        source_message_id=info.get("id"),
                        source_record_id=revision.get("current_match", {}).get(
                            "drawer_id"
                        ),
                        valid_from=filed_at,
                    )
                    continue
            if memory_tier == "working_session":
                dedupe_hash = self.core.working_session_dedupe_hash(role, text)
                if dedupe_hash in existing_working_hashes:
                    continue
            saved.append(
                self.core.repository.save_entry(
                    wing=session["wing"],
                    room=self.core.config.default_room,
                    content=content,
                    source_file=f"session:{session_id}",
                    metadata={
                        "type": "opencode_message",
                        "session_id": session_id,
                        "message_id": info.get("id"),
                        "role": role,
                        "reason": reason,
                        "directory": session["directory"],
                        "memory_tier": memory_tier,
                        "memory_key": memory_key,
                        "memory_value": memory_value,
                        "dedupe_hash": dedupe_hash,
                        "valid_from": filed_at,
                        "valid_to": None,
                        "session_order": next_order,
                    },
                )
            )
            saved_entry = saved[-1]
            if (
                memory_key
                and memory_value
                and memory_tier in {"user_preference", "project_memory"}
            ):
                scope = "user" if memory_tier == "user_preference" else "project"
                promotion = self.core.promoter.promote_saved_memory(
                    scope=scope,
                    memory_tier=memory_tier,
                    memory_key=memory_key,
                    memory_value=memory_value,
                    source_session=session_id,
                    source_message_id=info.get("id"),
                    source_record_id=saved_entry.get("drawer_id"),
                    valid_from=filed_at,
                )
            if dedupe_hash:
                existing_working_hashes.add(dedupe_hash)

        if messages:
            session["last_saved_message_id"] = messages[-1].get("info", {}).get("id")
        session["last_saved_order"] = next_order
        session["last_saved_at"] = datetime.now(timezone.utc).isoformat()
        self.core.runtime["last_flush_at"] = session["last_saved_at"]
        self.core._save_state(state)
        self.core._compact_working_session(session_id, session)
        return {
            "session_id": session_id,
            "directory": session["directory"],
            "wing": session["wing"],
            "saved": len(saved),
            "saved_drawer_ids": [item["drawer_id"] for item in saved],
            "last_saved_message_id": session.get("last_saved_message_id"),
            "reason": reason,
        }

    def compact_session(
        self, session_id: str, directory: str, messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self.flush_session(session_id, directory, messages, reason="compact")


__all__ = ["SessionLifecycleService"]
