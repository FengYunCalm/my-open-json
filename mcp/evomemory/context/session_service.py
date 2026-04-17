from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


AUTO_REVISION_MIN_CONFIDENCE = 0.7


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
            if self.core.should_skip_memory_capture(role, text, memory_tier):
                self.core.evaluation_service.increment("skipped_low_signal_messages")
                if role == "assistant":
                    self.core.evaluation_service.increment(
                        "skipped_low_signal_assistant_messages"
                    )
                continue
            memory_key = self.core.derive_memory_key(memory_tier, text)
            memory_value = self.core.derive_memory_value(memory_key, text)
            if memory_tier in {"user_preference", "project_memory"} and (
                not memory_key or memory_value is None
            ):
                memory_tier = "working_session"
                memory_key = None
                memory_value = None
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
                    self.core.evaluation_service.increment(
                        "skipped_duplicate_long_term_memory"
                    )
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
                        initial_source_count=2,
                    )
                    continue
            if memory_tier == "working_session":
                dedupe_hash = self.core.working_session_dedupe_hash(role, text)
                if dedupe_hash in existing_working_hashes:
                    self.core.evaluation_service.increment(
                        "skipped_duplicate_working_session"
                    )
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
            self.core.evaluation_service.increment(f"saved_{memory_tier}")
            if dedupe_hash:
                existing_working_hashes.add(dedupe_hash)

        if messages:
            session["last_saved_message_id"] = messages[-1].get("info", {}).get("id")
        session["last_saved_order"] = next_order
        session["last_saved_at"] = datetime.now(timezone.utc).isoformat()
        self.core.runtime["last_flush_at"] = session["last_saved_at"]
        self.core._save_state(state)
        self.core._compact_working_session(session_id, session)
        maintenance: dict[str, Any] | None = None
        if reason == "compact":
            pending_revision = (
                self.core.belief_service.has_low_confidence_current_facts(
                    min_confidence=AUTO_REVISION_MIN_CONFIDENCE
                )
            )
            if pending_revision:
                revision = self.core.evomemory_run_revision(
                    min_confidence=AUTO_REVISION_MIN_CONFIDENCE
                )
                maintenance = maintenance or {}
                maintenance["revision"] = {
                    "revised_count": revision["revised_count"],
                    "reconciled_gene_count": revision["reconciled_gene_count"],
                    "reconciled_capsule_count": revision["reconciled_capsule_count"],
                }
            stale_belief_ids = list(
                dict.fromkeys(
                    item.get("belief_id")
                    for item in self.core.belief_service.stale_source_records()
                    if item.get("belief_id")
                )
            )
            reconcile_preview = (
                self.core.governance_service.preview_reconcile_stale_assets(
                    stale_belief_ids
                )
            )
            if reconcile_preview.get("genes") or reconcile_preview.get("capsules"):
                reconcile = self.core._reconcile_governance_assets(
                    stale_belief_ids,
                    rationale="reconciled stale governance asset during compact maintenance",
                    record_empty=False,
                )
                maintenance = maintenance or {}
                maintenance["reconcile"] = {
                    "reconciled_gene_count": reconcile["reconciled_gene_count"],
                    "reconciled_capsule_count": reconcile["reconciled_capsule_count"],
                }
            repair = self.core._repair_current_governance_assets(
                rationale="repaired missing current governance asset during compact maintenance",
                record_empty=False,
            )
            if repair.get("repaired_gene_count") or repair.get(
                "repaired_capsule_count"
            ):
                maintenance = maintenance or {}
                maintenance["repair"] = {
                    "repaired_gene_count": repair["repaired_gene_count"],
                    "repaired_capsule_count": repair["repaired_capsule_count"],
                }
        return {
            "session_id": session_id,
            "directory": session["directory"],
            "wing": session["wing"],
            "saved": len(saved),
            "saved_drawer_ids": [item["drawer_id"] for item in saved],
            "last_saved_message_id": session.get("last_saved_message_id"),
            "reason": reason,
            "maintenance": maintenance,
        }

    def compact_session(
        self, session_id: str, directory: str, messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self.flush_session(session_id, directory, messages, reason="compact")


__all__ = ["SessionLifecycleService"]
