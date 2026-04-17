from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import chromadb
except (
    ModuleNotFoundError
):  # pragma: no cover - exercised in lightweight import contexts
    chromadb = None

try:
    from mempalace.config import MempalaceConfig, sanitize_content, sanitize_name
    from mempalace.knowledge_graph import KnowledgeGraph
except (
    ModuleNotFoundError
):  # pragma: no cover - exercised in lightweight import contexts
    MempalaceConfig = None

    def sanitize_content(value: str, _field_name: str | None = None) -> str:
        return value

    def sanitize_name(value: str, _field_name: str | None = None) -> str:
        return value

    class KnowledgeGraph:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "The EvoMemory backend requires the underlying knowledge graph package. Install the package before using the live backend."
            )


from evomemory.domain.memory_policy import (
    classify_memory_tier,
    derive_memory_key,
    derive_memory_value,
)
from evomemory.context.query_service import ContextQueryService
from evomemory.context.repository import ContextRepository
from evomemory.context.session_service import SessionLifecycleService
from evomemory.belief import BeliefPlaneService, MemoryPromoter, MemoryReviser
from evomemory.evaluation import EvaluationPlaneService
from evomemory.governance import GovernancePlaneService
from evomemory.runtime import RuntimeOrchestrator
from evomemory.infrastructure.state.session_state import SessionStateStore


SKIP_TEXTS = {
    "ok",
    "okay",
    "yes",
    "no",
    "thanks",
    "thank you",
    "continue",
    "start",
    "go",
}
VALID_ROLES = {"user", "assistant"}
VALID_MEMORY_TIERS = {"working_session", "user_preference", "project_memory"}
PREVIEW_CHARS = 200
FETCH_BATCH_SIZE = 1000
EVOMEMORY_HOME_DIRNAME = ".evomemory"
LEGACY_HOME_DIRNAME = ".mempalace"
EVOMEMORY_PALACE_ENV = "EVOMEMORY_PALACE_PATH"
LEGACY_PALACE_ENV = "MEMPALACE_PALACE_PATH"
EVOMEMORY_COLLECTION_NAME = "evomemory_drawers"
LEGACY_COLLECTION_NAME = "mempalace_drawers"
LEGACY_STATE_FILENAME = "mempalace_bridge_state.json"
EVOMEMORY_STATE_FILENAME = "evomemory_bridge_state.sqlite3"


def _default_evomemory_home(home: Path | None = None) -> Path:
    return (home or Path.home()) / EVOMEMORY_HOME_DIRNAME


def _default_legacy_home(home: Path | None = None) -> Path:
    return (home or Path.home()) / LEGACY_HOME_DIRNAME


def _ensure_legacy_symlink(legacy_path: Path, target_path: Path) -> None:
    if legacy_path.is_symlink():
        if legacy_path.resolve() == target_path.resolve():
            return
        legacy_path.unlink()
    elif legacy_path.exists():
        return
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.symlink_to(target_path, target_is_directory=target_path.is_dir())


def _migrate_legacy_path(legacy_path: Path, resolved: Path) -> Path:
    resolved.parent.mkdir(parents=True, exist_ok=True)
    if resolved.exists():
        _ensure_legacy_symlink(legacy_path, resolved)
        return resolved
    if legacy_path.exists() and not legacy_path.is_symlink():
        legacy_path.replace(resolved)
        _ensure_legacy_symlink(legacy_path, resolved)
    return resolved


def _resolve_state_path(state_path: Path) -> Path:
    resolved = Path(state_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    legacy_state_path = resolved.with_name(LEGACY_STATE_FILENAME)
    if (
        resolved.name == EVOMEMORY_STATE_FILENAME
        and not resolved.exists()
        and legacy_state_path.exists()
    ):
        legacy_state_path.replace(resolved)
    return resolved


def _resolve_palace_path(
    palace_path: str | Path | None,
    *,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    env = env or os.environ
    home = home or Path.home()
    if palace_path:
        resolved = Path(palace_path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved
    if env.get(EVOMEMORY_PALACE_ENV):
        resolved = Path(env[EVOMEMORY_PALACE_ENV])
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved
    if env.get(LEGACY_PALACE_ENV):
        resolved = Path(env[LEGACY_PALACE_ENV])
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved
    return _migrate_legacy_path(
        _default_legacy_home(home) / "palace",
        _default_evomemory_home(home) / "palace",
    )


def _resolve_wing_config_path(
    wing_config_path: Path, *, home: Path | None = None
) -> Path:
    home = home or Path.home()
    legacy_config_path = _default_legacy_home(home) / "wing_config.json"
    default_config_path = _default_evomemory_home(home) / "wing_config.json"
    if wing_config_path == default_config_path:
        return _migrate_legacy_path(legacy_config_path, wing_config_path)
    wing_config_path.parent.mkdir(parents=True, exist_ok=True)
    return wing_config_path


def _sanitize_optional_name(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return sanitize_name(value, field_name)


def _sanitize_optional_role(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in VALID_ROLES:
        raise ValueError("role must be one of: assistant, user")
    return normalized


def _sanitize_optional_memory_tier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in VALID_MEMORY_TIERS:
        raise ValueError(
            "memory_tier must be one of: project_memory, user_preference, working_session"
        )
    return normalized


def _preview_text(text: str, max_chars: int = PREVIEW_CHARS) -> str:
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 1] + "…"


def _working_session_dedupe_hash(role: str, text: str) -> str:
    normalized = " ".join((text or "").split()).strip().lower()
    return hashlib.sha1(f"{role}\n{normalized}".encode("utf-8")).hexdigest()


def _summary_sort_key(item: dict[str, Any]) -> tuple[int, str]:
    metadata = item.get("metadata", {})
    return (
        _safe_order(metadata.get("session_order")) or 0,
        item.get("message_id") or "",
    )


def _core_memory_sort_key(item: dict[str, Any]) -> tuple[int, int, float, str]:
    tier_priority = {"user_preference": 0, "project_memory": 1}.get(
        item.get("memory_tier"), 9
    )
    key_priority = {
        "response_language": 0,
        "response_detail": 1,
        "code_change_permission": 2,
        "implementation_mode_preference": 3,
        "git_commit_behavior": 4,
        "test_execution_behavior": 5,
    }.get(item.get("memory_key"), 9)
    scope_priority = int(item.get("_scope_priority", 9))
    recency_text = item.get("valid_from") or item.get("filed_at") or ""
    try:
        recency = -datetime.fromisoformat(
            recency_text.replace("Z", "+00:00")
        ).timestamp()
    except ValueError:
        recency = 0.0
    return (
        tier_priority,
        key_priority,
        scope_priority,
        recency,
        item.get("message_id") or "",
    )


def _safe_similarity(distance: float | int | None) -> float:
    if distance is None:
        return 0.0
    return round(max(0.0, 1 - float(distance)), 3)


def _safe_order(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metadata.items() if value is not None}


def _message_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    metadata = item.get("metadata", {})
    session_order = _safe_order(metadata.get("session_order"))
    if session_order is not None:
        return (
            0,
            session_order,
            metadata.get("message_id", ""),
            item.get("drawer_id", ""),
        )
    return (
        1,
        metadata.get("filed_at", ""),
        metadata.get("message_id", ""),
        item.get("drawer_id", ""),
    )


@dataclass(slots=True)
class BridgeConfig:
    palace_path: str | None = None
    collection_name: str = EVOMEMORY_COLLECTION_NAME
    state_path: Path | str = (
        Path.home() / ".config" / "opencode" / "mcp" / EVOMEMORY_STATE_FILENAME
    )
    wing_config_path: Path | str = (
        Path.home() / EVOMEMORY_HOME_DIRNAME / "wing_config.json"
    )
    default_room: str = "opencode-session"
    search_limit: int = 5
    core_memory_limit: int = 6
    max_block_chars: int = 2000
    min_meaningful_chars: int = 6
    working_session_compact_threshold: int = 8
    working_session_retain_count: int = 4

    def __post_init__(self):
        self.palace_path = str(_resolve_palace_path(self.palace_path))
        self.state_path = _resolve_state_path(Path(self.state_path))
        self.wing_config_path = _resolve_wing_config_path(Path(self.wing_config_path))


class EvoMemoryBackend:
    def __init__(self, config: BridgeConfig):
        if MempalaceConfig is None:
            raise RuntimeError(
                "The EvoMemory backend requires the underlying memory package. Install it before using the live backend."
            )
        self.bridge_config = config
        self.library_config = MempalaceConfig()
        if config.palace_path:
            os.environ[EVOMEMORY_PALACE_ENV] = config.palace_path
            os.environ[LEGACY_PALACE_ENV] = config.palace_path
        self.palace_path = config.palace_path or self.library_config.palace_path
        self.collection_name = (
            config.collection_name or self.library_config.collection_name
        )
        self._client: chromadb.PersistentClient | None = None
        self._collection = None
        self._kg = KnowledgeGraph(
            db_path=str(Path(self.palace_path) / "knowledge_graph.sqlite3")
        )

    def _client_for(self) -> chromadb.PersistentClient:
        if self._client is not None:
            return self._client
        if chromadb is None:
            raise RuntimeError(
                "chromadb is required to initialize the EvoMemory backend. Install chromadb before using the live backend."
            )
        self._client = chromadb.PersistentClient(path=self.palace_path)
        return self._client

    def _collection_for(self, create: bool = False):
        if self._collection is not None:
            return self._collection
        client = self._client_for()
        try:
            self._collection = client.get_collection(self.collection_name)
        except Exception:
            if not create and self.collection_name == LEGACY_COLLECTION_NAME:
                raise
            self._collection = client.get_or_create_collection(self.collection_name)
        if self.collection_name != LEGACY_COLLECTION_NAME:
            self._migrate_legacy_collection(client, self._collection)
        return self._collection

    def _collection_has_rows(self, collection: Any) -> bool:
        try:
            rows = collection.get(include=["documents", "metadatas"], limit=1, offset=0)
        except TypeError:
            rows = collection.get(include=["documents", "metadatas"])
        return bool(rows.get("ids", []))

    def _migrate_legacy_collection(self, client: Any, target_collection: Any) -> None:
        try:
            legacy_collection = client.get_collection(LEGACY_COLLECTION_NAME)
        except Exception:
            return
        if self._collection_has_rows(target_collection):
            return
        offset = 0
        while True:
            batch = legacy_collection.get(
                include=["documents", "metadatas"],
                limit=FETCH_BATCH_SIZE,
                offset=offset,
            )
            ids = batch.get("ids", [])
            if not ids:
                break
            target_collection.upsert(
                ids=ids,
                documents=batch.get("documents", []),
                metadatas=batch.get("metadatas", []),
            )
            offset += len(ids)

    def _make_where(
        self,
        *,
        wing: str | None = None,
        directory: str | None = None,
        memory_tier: str | None = None,
        room: str | None = None,
        session_id: str | None = None,
        role: str | None = None,
        source_file: str | None = None,
    ) -> dict[str, Any] | None:
        conditions = []
        if wing is not None:
            conditions.append({"wing": wing})
        if directory is not None:
            conditions.append({"directory": directory})
        if memory_tier is not None:
            conditions.append({"memory_tier": memory_tier})
        if room is not None:
            conditions.append({"room": room})
        if session_id is not None:
            conditions.append({"session_id": session_id})
        if role is not None:
            conditions.append({"role": role})
        if source_file is not None:
            conditions.append({"source_file": source_file})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _get_all(
        self, *, include: list[str], where: dict[str, Any] | None = None
    ) -> dict[str, list[Any]]:
        collection = self._collection_for()
        merged: dict[str, list[Any]] = {"ids": []}
        for key in include:
            merged[key] = []

        offset = 0
        while True:
            kwargs: dict[str, Any] = {
                "include": include,
                "limit": FETCH_BATCH_SIZE,
                "offset": offset,
            }
            if where:
                kwargs["where"] = where
            batch = collection.get(**kwargs)
            ids = batch.get("ids", [])
            if not ids:
                break
            merged["ids"].extend(ids)
            for key in include:
                merged[key].extend(batch.get(key, []))
            offset += len(ids)
        return merged

    def _format_row(
        self,
        *,
        drawer_id: str,
        text: str,
        metadata: dict[str, Any],
        distance: float | int | None = None,
    ) -> dict[str, Any]:
        return {
            "drawer_id": drawer_id,
            "text": text,
            "preview": _preview_text(text),
            "wing": metadata.get("wing", "unknown"),
            "room": metadata.get("room", "unknown"),
            "directory": metadata.get("directory"),
            "source_file": metadata.get("source_file", ""),
            "session_id": metadata.get("session_id"),
            "message_id": metadata.get("message_id"),
            "role": metadata.get("role"),
            "memory_tier": metadata.get("memory_tier"),
            "dedupe_hash": metadata.get("dedupe_hash"),
            "filed_at": metadata.get("filed_at"),
            "distance": round(float(distance), 4) if distance is not None else None,
            "similarity": _safe_similarity(distance),
            "metadata": metadata,
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
    ) -> list[dict[str, Any]]:
        collection = self._collection_for()
        where = self._make_where(
            wing=wing,
            directory=directory,
            memory_tier=memory_tier,
            room=room,
            session_id=session_id,
            role=role,
            source_file=source_file,
        )

        if query:
            kwargs: dict[str, Any] = {
                "query_texts": [query],
                "n_results": max(1, limit + offset),
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                kwargs["where"] = where
            result = collection.query(**kwargs)
            ids = result.get("ids", [[]])[0]
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            rows = [
                self._format_row(
                    drawer_id=drawer_id, text=text, metadata=metadata, distance=distance
                )
                for drawer_id, text, metadata, distance in zip(
                    ids, documents, metadatas, distances
                )
            ]
            if current_only:
                rows = [row for row in rows if not row.get("valid_to")]
            elif historical_only:
                rows = [row for row in rows if row.get("valid_to")]
            return rows[offset : offset + limit]

        kwargs = {
            "include": ["documents", "metadatas"],
            "limit": limit,
            "offset": offset,
        }
        if where:
            kwargs["where"] = where
        result = collection.get(**kwargs)
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        rows = [
            self._format_row(drawer_id=drawer_id, text=text, metadata=metadata)
            for drawer_id, text, metadata in zip(ids, documents, metadatas)
        ]
        if current_only:
            rows = [row for row in rows if not row.get("valid_to")]
        elif historical_only:
            rows = [row for row in rows if row.get("valid_to")]
        return rows

    def search(self, query: str, wing: str | None, room: str | None, limit: int):
        return self.query_drawers(query=query, wing=wing, room=room, limit=limit)

    def save_entry(
        self,
        *,
        wing: str,
        room: str,
        content: str,
        source_file: str,
        metadata: dict[str, Any],
    ):
        wing = sanitize_name(wing, "wing")
        room = sanitize_name(room, "room")
        content = sanitize_content(content)
        collection = self._collection_for(create=True)
        digest = hashlib.sha256(
            json.dumps(
                {
                    "wing": wing,
                    "room": room,
                    "source_file": source_file,
                    "message_id": metadata.get("message_id"),
                    "content": content,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:24]
        drawer_id = f"drawer_{wing}_{room}_{digest}"
        payload = _normalize_metadata(
            {
                "wing": wing,
                "room": room,
                "source_file": source_file,
                "chunk_index": 0,
                "added_by": "opencode-bridge",
                "filed_at": datetime.now(timezone.utc).isoformat(),
                **metadata,
            }
        )
        collection.upsert(ids=[drawer_id], documents=[content], metadatas=[payload])
        return {"drawer_id": drawer_id, "wing": wing, "room": room, "metadata": payload}

    def invalidate_memory_conflicts(
        self,
        *,
        wing: str,
        directory: str,
        memory_tier: str,
        memory_key: str,
        valid_to: str,
    ) -> int:
        result = self._get_all(
            include=["documents", "metadatas"],
            where=self._make_where(
                wing=wing,
                directory=directory,
                memory_tier=memory_tier,
            ),
        )
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        update_ids = []
        update_docs = []
        update_metas = []
        for drawer_id, document, metadata in zip(ids, documents, metadatas):
            if metadata.get("memory_key") != memory_key:
                continue
            if metadata.get("valid_to"):
                continue
            updated = dict(metadata)
            updated["valid_to"] = valid_to
            update_ids.append(drawer_id)
            update_docs.append(document)
            update_metas.append(updated)

        if update_ids:
            self._collection_for(create=True).upsert(
                ids=update_ids,
                documents=update_docs,
                metadatas=update_metas,
            )
        return len(update_ids)

    def invalidate_drawers(self, *, drawer_ids: list[str], valid_to: str) -> int:
        if not drawer_ids:
            return 0
        result = self._collection_for().get(
            ids=drawer_ids, include=["documents", "metadatas"]
        )
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        update_ids = []
        update_docs = []
        update_metas = []
        for drawer_id, document, metadata in zip(ids, documents, metadatas):
            if metadata.get("valid_to"):
                continue
            updated = dict(metadata)
            updated["valid_to"] = valid_to
            update_ids.append(drawer_id)
            update_docs.append(document)
            update_metas.append(updated)

        if update_ids:
            self._collection_for(create=True).upsert(
                ids=update_ids,
                documents=update_docs,
                metadatas=update_metas,
            )
        return len(update_ids)

    def status(self):
        try:
            collection = self._collection_for()
            total = collection.count()
        except Exception:
            total = 0
        return {"total_drawers": total, "palace_path": self.palace_path}

    def memory_stats(self) -> dict[str, Any]:
        try:
            metadatas = self._get_all(include=["metadatas"]).get("metadatas", [])
        except Exception:
            metadatas = []

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
        for item in metadatas:
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
        try:
            metadatas = self._get_all(include=["metadatas"]).get("metadatas", [])
        except Exception:
            return {}
        wings: dict[str, int] = {}
        for item in metadatas:
            wing = item.get("wing", "unknown")
            wings[wing] = wings.get(wing, 0) + 1
        return wings

    def list_rooms(self, wing: str | None = None):
        try:
            metadatas = self._get_all(
                include=["metadatas"], where=self._make_where(wing=wing)
            ).get("metadatas", [])
        except Exception:
            return {}
        rooms: dict[str, int] = {}
        for item in metadatas:
            room = item.get("room", "unknown")
            rooms[room] = rooms.get(room, 0) + 1
        return rooms

    def get_taxonomy(self):
        try:
            metadatas = self._get_all(include=["metadatas"]).get("metadatas", [])
        except Exception:
            return {}
        taxonomy: dict[str, dict[str, int]] = {}
        taxonomy_by_memory_tier: dict[str, dict[str, dict[str, int]]] = {}
        taxonomy_by_memory_key: dict[str, dict[str, dict[str, int]]] = {}
        for item in metadatas:
            wing = item.get("wing", "unknown")
            room = item.get("room", "unknown")
            taxonomy.setdefault(wing, {})
            taxonomy[wing][room] = taxonomy[wing].get(room, 0) + 1
            memory_tier = item.get("memory_tier") or "unknown"
            taxonomy_by_memory_tier.setdefault(memory_tier, {})
            taxonomy_by_memory_tier[memory_tier].setdefault(wing, {})
            taxonomy_by_memory_tier[memory_tier][wing][room] = (
                taxonomy_by_memory_tier[memory_tier][wing].get(room, 0) + 1
            )
            memory_key = item.get("memory_key")
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
    ) -> list[dict[str, Any]]:
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

    def get_drawer(self, drawer_id: str):
        try:
            result = self._collection_for().get(
                ids=[drawer_id], include=["documents", "metadatas"]
            )
        except Exception:
            return None
        if not result.get("ids"):
            return None
        metadata = result["metadatas"][0]
        return {
            "drawer_id": result["ids"][0],
            "content": result["documents"][0],
            "wing": metadata.get("wing", ""),
            "room": metadata.get("room", ""),
            "metadata": metadata,
        }

    def list_sessions(
        self,
        *,
        wing: str | None = None,
        room: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        try:
            metadatas = self._get_all(
                include=["metadatas"], where=self._make_where(wing=wing, room=room)
            ).get("metadatas", [])
        except Exception:
            return []

        sessions: dict[str, dict[str, Any]] = {}
        for item in metadatas:
            session_id = item.get("session_id")
            if not session_id:
                continue
            entry = sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "wing": item.get("wing", "unknown"),
                    "room": item.get("room", "unknown"),
                    "message_count": 0,
                    "current_message_count": 0,
                    "historical_message_count": 0,
                    "memory_tier_counts": {},
                    "current_memory_tier_counts": {},
                    "historical_memory_tier_counts": {},
                    "last_filed_at": item.get("filed_at"),
                    "source_file": item.get("source_file", ""),
                },
            )
            entry["message_count"] += 1
            memory_tier = item.get("memory_tier") or "unknown"
            entry["memory_tier_counts"][memory_tier] = (
                entry["memory_tier_counts"].get(memory_tier, 0) + 1
            )
            if item.get("valid_to"):
                entry["historical_message_count"] += 1
                entry["historical_memory_tier_counts"][memory_tier] = (
                    entry["historical_memory_tier_counts"].get(memory_tier, 0) + 1
                )
            else:
                entry["current_message_count"] += 1
                entry["current_memory_tier_counts"][memory_tier] = (
                    entry["current_memory_tier_counts"].get(memory_tier, 0) + 1
                )
            filed_at = item.get("filed_at")
            if filed_at and (
                entry["last_filed_at"] is None or filed_at > entry["last_filed_at"]
            ):
                entry["last_filed_at"] = filed_at

        rows = sorted(
            sessions.values(),
            key=lambda item: (item.get("last_filed_at") or "", item["session_id"]),
            reverse=True,
        )
        return rows[offset : offset + limit]

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
    ) -> list[dict[str, Any]]:
        try:
            result = self._get_all(
                include=["documents", "metadatas"],
                where=self._make_where(
                    session_id=session_id, memory_tier=memory_tier, role=role
                ),
            )
        except Exception:
            return []

        rows = [
            self._format_row(drawer_id=drawer_id, text=text, metadata=metadata)
            for drawer_id, text, metadata in zip(
                result.get("ids", []),
                result.get("documents", []),
                result.get("metadatas", []),
            )
        ]
        if current_only:
            rows = [row for row in rows if not row.get("valid_to")]
        elif historical_only:
            rows = [row for row in rows if row.get("valid_to")]
        rows.sort(key=_message_sort_key)
        return rows[offset : offset + limit]

    def kg_query(self, entity: str, as_of: str | None = None, direction: str = "both"):
        query_direction = "outgoing" if direction == "both" else direction
        facts = self._kg.query_entity(entity, as_of=as_of, direction=query_direction)
        return {
            "entity": entity,
            "as_of": as_of,
            "direction": direction,
            "facts": facts,
            "count": len(facts),
        }


class BridgeCore:
    def __init__(self, config: BridgeConfig | None = None, backend: Any | None = None):
        self.config = config or BridgeConfig()
        self.state_store = SessionStateStore(self.config.state_path)
        self.repository = ContextRepository(backend or EvoMemoryBackend(self.config))
        self.backend = self.repository.backend
        self.runtime = {
            "last_search_at": None,
            "last_flush_at": None,
            "last_compaction_at": None,
            "last_compaction_session_id": None,
            "last_compaction_compacted_count": 0,
            "last_compaction_summary_drawer_id": None,
        }
        self._runtime = self.runtime
        self.valid_roles = VALID_ROLES
        self.classify_memory_tier = classify_memory_tier
        self.derive_memory_key = derive_memory_key
        self.derive_memory_value = derive_memory_value
        self.working_session_dedupe_hash = _working_session_dedupe_hash
        self.sanitize_optional_name = _sanitize_optional_name
        self.sanitize_optional_role = _sanitize_optional_role
        self.sanitize_optional_memory_tier = _sanitize_optional_memory_tier
        self.session_service = SessionLifecycleService(self)
        self.query_service = ContextQueryService(self)
        self.belief_service = BeliefPlaneService(self.config.state_path)
        self.governance_service = GovernancePlaneService(self.config.state_path)
        self.evaluation_service = EvaluationPlaneService(self.config.state_path)
        self.reviser = MemoryReviser(self.repository)
        self.promoter = MemoryPromoter(
            self.belief_service,
            self.governance_service,
            self.evaluation_service,
        )
        self.runtime_orchestrator = RuntimeOrchestrator(self, self.evaluation_service)

    def _load_state(self) -> dict[str, Any]:
        return self.state_store.load()

    def _save_state(self, state: dict[str, Any]) -> None:
        self.state_store.save(state)

    def _normalize_directory(self, directory: str) -> str:
        normalized = (directory or "").replace("\\", "/").rstrip("/")
        return normalized or "/"

    def _load_aliases(self) -> dict[str, str]:
        if not self.config.wing_config_path.exists():
            return {}
        try:
            payload = json.loads(
                self.config.wing_config_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            return {}
        aliases = payload.get("aliases", {})
        return {self._normalize_directory(path): wing for path, wing in aliases.items()}

    def resolve_wing(self, directory: str) -> str:
        normalized = self._normalize_directory(directory)
        aliases = self._load_aliases()
        for path, wing in aliases.items():
            if normalized == path or normalized.startswith(path + "/"):
                return sanitize_name(wing, "wing")
        fallback = Path(normalized).name or "ubuntu-opencode"
        safe = "".join(
            ch if ch.isalnum() or ch in {"-", "_", ".", " "} else "-" for ch in fallback
        )
        return sanitize_name(safe, "wing")

    def _is_meaningful_text(self, text: str) -> bool:
        normalized = text.strip().lower()
        if not normalized or "<command-message>" in normalized:
            return False
        if normalized in SKIP_TEXTS:
            return False
        return len(normalized) >= self.config.min_meaningful_chars

    def _collect_text(self, parts: list[dict[str, Any]]) -> str:
        chunks = []
        for part in parts or []:
            if part.get("type") != "text":
                continue
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
        return "\n\n".join(chunks).strip()

    def _new_messages(
        self, messages: list[dict[str, Any]], last_saved_message_id: str | None
    ):
        if not last_saved_message_id:
            return messages
        found = False
        collected = []
        for message in messages:
            message_id = message.get("info", {}).get("id")
            if found:
                collected.append(message)
            elif message_id == last_saved_message_id:
                found = True
        return collected if found else messages

    def _normalize_limit(self, limit: int, default: int = 20) -> int:
        if not isinstance(limit, int):
            return default
        return max(1, min(limit, 100))

    def _normalize_offset(self, offset: int) -> int:
        if not isinstance(offset, int):
            return 0
        return max(0, offset)

    def _format_public_hit(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "drawer_id": item.get("drawer_id"),
            "text": item.get("text", ""),
            "preview": item.get("preview") or _preview_text(item.get("text", "")),
            "wing": item.get("wing"),
            "room": item.get("room"),
            "directory": item.get("directory"),
            "source_file": item.get("source_file"),
            "session_id": item.get("session_id"),
            "message_id": item.get("message_id"),
            "role": item.get("role"),
            "memory_tier": item.get("memory_tier"),
            "memory_key": item.get("memory_key"),
            "memory_value": item.get("memory_value"),
            "valid_from": item.get("valid_from"),
            "valid_to": item.get("valid_to"),
            "working_summary": item.get("working_summary") is True,
            "filed_at": item.get("filed_at"),
            "similarity": item.get("similarity", 0),
            "distance": item.get("distance"),
        }

    def _format_context_hit(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "drawer_id": item.get("drawer_id"),
            "text": item.get("text", ""),
            "preview": item.get("preview") or _preview_text(item.get("text", ""), 160),
            "wing": item.get("wing"),
            "room": item.get("room"),
            "directory": item.get("directory"),
            "source_file": item.get("source_file"),
            "session_id": item.get("session_id"),
            "message_id": item.get("message_id"),
            "role": item.get("role"),
            "memory_tier": item.get("memory_tier"),
            "memory_key": item.get("memory_key"),
            "memory_value": item.get("memory_value"),
            "valid_from": item.get("valid_from"),
            "valid_to": item.get("valid_to"),
            "working_summary": item.get("working_summary") is True,
            "filed_at": item.get("filed_at"),
            "search_tier": item.get("search_tier"),
            "similarity": item.get("similarity", 0),
        }

    def _append_block_lines(
        self,
        lines: list[str],
        used: int,
        title: str,
        items: list[dict[str, Any]],
        mode: str,
    ) -> int:
        if not items:
            return used
        if lines:
            lines.append("")
            used += 1
        lines.append(title)
        used += len(title)
        for index, item in enumerate(items, start=1):
            drawer_id = item.get("drawer_id") or "?"
            if mode == "core":
                header = (
                    f"{index}. [{item.get('memory_tier') or 'memory'}] "
                    f"drawer={drawer_id} src={item.get('source_file') or '?'}"
                )
            else:
                tier = item.get("search_tier") or "memory"
                header = (
                    f"{index}. [{float(item.get('similarity', 0)):.2f}][{tier}] "
                    f"drawer={drawer_id} "
                    f"room={item.get('room') or 'unknown'} "
                    f"role={item.get('role') or 'unknown'} "
                    f"src={item.get('source_file') or '?'}"
                )
            if used + len(header) + 1 > self.config.max_block_chars:
                break
            lines.append(header)
            used += len(header) + 1

            remaining = self.config.max_block_chars - used - 4
            if remaining <= 0:
                break
            body = _preview_text(item.get("text", ""), max_chars=remaining)
            if not body:
                continue
            line = f"   {body}"
            lines.append(line)
            used += len(line) + 1
        return used

    def _build_system_block(
        self,
        wing: str,
        results: list[dict[str, Any]],
        core_memory: list[dict[str, Any]] | None = None,
        core_memory_truncated_count: int = 0,
        context_truncated_count: int = 0,
    ) -> str:
        if not results and not core_memory:
            return ""
        lines: list[str] = []
        used = 0
        used = self._append_block_lines(
            lines, used, "Core memory:", core_memory or [], "core"
        )
        if core_memory_truncated_count > 0:
            notice = f"   ... {core_memory_truncated_count} more core memories omitted"
            if used + len(notice) + 1 <= self.config.max_block_chars:
                lines.append(notice)
                used += len(notice) + 1
        if context_truncated_count > 0:
            notice = f"   ... {context_truncated_count} more context memories omitted"
            if used + len(notice) + 1 <= self.config.max_block_chars:
                if lines:
                    lines.append("")
                    used += 1
                lines.append(notice)
                used += len(notice) + 1
        used = self._append_block_lines(
            lines,
            used,
            f"EvoMemory context for wing '{wing}':",
            results,
            "context",
        )
        return "\n".join(lines)

    def _core_memory_results(
        self, directory: str, wing: str
    ) -> tuple[list[dict[str, Any]], int, int]:
        tiers = [
            ({"directory": directory, "memory_tier": "user_preference"}, 0),
            ({"wing": wing, "memory_tier": "user_preference"}, 1),
            ({"directory": directory, "memory_tier": "project_memory"}, 2),
            ({"wing": wing, "memory_tier": "project_memory"}, 3),
        ]
        candidates = []
        for filters, scope_priority in tiers:
            rows = self.repository.query_drawers(query=None, limit=3, **filters)
            for row in rows:
                if not row.get("text"):
                    continue
                if row.get("valid_to"):
                    continue
                candidates.append({**row, "_scope_priority": scope_priority})

        deduped = []
        seen_keys = set()
        for item in sorted(candidates, key=_core_memory_sort_key):
            dedupe_key = item.get("memory_key") or item.get("drawer_id")
            if not dedupe_key or dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            deduped.append(item)
        total_count = len(deduped)
        limit = max(0, int(self.config.core_memory_limit or 0))
        if limit:
            deduped = deduped[:limit]
        else:
            deduped = []
        formatted = [self._format_context_hit(item) for item in deduped]
        return formatted, total_count, max(0, total_count - len(formatted))

    def _tiered_context_results(
        self, query: str, directory: str, wing: str, session_id: str | None = None
    ) -> tuple[list[dict[str, Any]], int, int]:
        limit = max(1, int(self.config.search_limit or 0))
        tier_fetch_limit = max(limit * 4, 10)
        tiers = []
        if session_id:
            tiers.append(("session", {"session_id": session_id}))
        tiers.append(("directory", {"directory": directory}))
        tiers.append(("wing", {"wing": wing}))
        tiers.append(("global", {}))

        seen = set()
        results = []
        for tier_name, filters in tiers:
            rows = self.repository.query_drawers(
                query=query,
                limit=tier_fetch_limit,
                current_only=True,
                **filters,
            )
            for row in rows:
                drawer_id = row.get("drawer_id")
                if not drawer_id or drawer_id in seen:
                    continue
                if not row.get("text") or float(row.get("similarity", 0)) <= 0:
                    continue
                seen.add(drawer_id)
                results.append({**row, "search_tier": tier_name})
        total_count = len(results)
        if limit:
            results = results[:limit]
        else:
            results = []
        return results, total_count, max(0, total_count - len(results))

    def _build_working_session_summary_content(self, rows: list[dict[str, Any]]) -> str:
        lines = ["Working session summary:"]
        for row in sorted(rows, key=_summary_sort_key):
            preview = _preview_text(row.get("text", ""), max_chars=120)
            if preview:
                lines.append(f"- {preview}")
        return "\n".join(lines)

    def _compact_working_session(
        self, session_id: str, session: dict[str, Any]
    ) -> None:
        threshold = max(0, int(self.config.working_session_compact_threshold or 0))
        retain_count = max(0, int(self.config.working_session_retain_count or 0))
        if threshold <= 0:
            return

        rows = self.repository.get_session_messages(
            session_id=session_id,
            memory_tier="working_session",
            current_only=True,
            limit=1000,
            offset=0,
        )
        summary_rows = [row for row in rows if row.get("working_summary")]
        detail_rows = [row for row in rows if not row.get("working_summary")]
        if len(detail_rows) <= threshold:
            return

        compressible = detail_rows[:-retain_count] if retain_count else detail_rows
        if not compressible:
            return

        rows_to_compact = summary_rows + compressible
        valid_to = datetime.now(timezone.utc).isoformat()
        self.repository.invalidate_drawers(
            drawer_ids=[
                row["drawer_id"] for row in rows_to_compact if row.get("drawer_id")
            ],
            valid_to=valid_to,
        )

        compressed_orders = [
            _safe_order(row.get("metadata", {}).get("session_order")) or 0
            for row in compressible
        ]
        start_order = min(compressed_orders) if compressed_orders else 0
        end_order = max(compressed_orders) if compressed_orders else 0
        summary_id = f"summary_{session_id}_{start_order}_{end_order}"

        summary = self.repository.save_entry(
            wing=session["wing"],
            room=self.config.default_room,
            content=self._build_working_session_summary_content(rows_to_compact),
            source_file=f"session:{session_id}",
            metadata={
                "type": "opencode_message",
                "session_id": session_id,
                "message_id": summary_id,
                "role": "assistant",
                "reason": "working_session_compaction",
                "directory": session["directory"],
                "memory_tier": "working_session",
                "memory_key": "working_session_summary",
                "memory_value": session_id,
                "dedupe_hash": None,
                "working_summary": True,
                "valid_from": valid_to,
                "valid_to": None,
                "session_order": end_order,
                "summary_start_order": start_order,
                "summary_end_order": end_order,
                "summary_count": len(rows_to_compact),
            },
        )
        self.runtime["last_compaction_at"] = valid_to
        self.runtime["last_compaction_session_id"] = session_id
        self.runtime["last_compaction_compacted_count"] = len(rows_to_compact)
        self.runtime["last_compaction_summary_drawer_id"] = summary["drawer_id"]

    def health(self) -> dict[str, Any]:
        return self.query_service.health()

    def start_session(self, session_id: str, directory: str) -> dict[str, Any]:
        return self.session_service.start_session(session_id, directory)

    def search_context(
        self, query: str, directory: str, session_id: str | None = None
    ) -> dict[str, Any]:
        return self.query_service.search_context(
            query, directory, session_id=session_id
        )

    def flush_session(
        self,
        session_id: str,
        directory: str,
        messages: list[dict[str, Any]],
        reason: str,
    ) -> dict[str, Any]:
        return self.session_service.flush_session(
            session_id, directory, messages, reason
        )

    def compact_session(
        self, session_id: str, directory: str, messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self.session_service.compact_session(session_id, directory, messages)

    def mcp_status(self) -> dict[str, Any]:
        return self.query_service.mcp_status()

    def debug_status(self) -> dict[str, Any]:
        return self.query_service.debug_status()

    def mcp_list_wings(self) -> dict[str, Any]:
        return self.query_service.mcp_list_wings()

    def mcp_list_rooms(self, wing: str | None = None) -> dict[str, Any]:
        return self.query_service.mcp_list_rooms(wing=wing)

    def mcp_get_taxonomy(self) -> dict[str, Any]:
        return self.query_service.mcp_get_taxonomy()

    def mcp_get_drawer(self, drawer_id: str) -> dict[str, Any]:
        return self.query_service.mcp_get_drawer(drawer_id)

    def mcp_search(
        self,
        query: str,
        limit: int = 5,
        wing: str | None = None,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        room: str | None = None,
    ) -> dict[str, Any]:
        return self.query_service.mcp_search(
            query=query,
            limit=limit,
            wing=wing,
            memory_tier=memory_tier,
            current_only=current_only,
            historical_only=historical_only,
            room=room,
        )

    def mcp_list_drawers(
        self,
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
    ) -> dict[str, Any]:
        return self.query_service.mcp_list_drawers(
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

    def mcp_list_sessions(
        self,
        wing: str | None = None,
        room: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self.query_service.mcp_list_sessions(
            wing=wing,
            room=room,
            limit=limit,
            offset=offset,
        )

    def mcp_get_session_messages(
        self,
        session_id: str,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        role: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self.query_service.mcp_get_session_messages(
            session_id=session_id,
            memory_tier=memory_tier,
            current_only=current_only,
            historical_only=historical_only,
            role=role,
            limit=limit,
            offset=offset,
        )

    def mcp_kg_query(
        self, entity: str, as_of: str | None = None, direction: str = "both"
    ) -> dict[str, Any]:
        return self.query_service.mcp_kg_query(entity, as_of=as_of, direction=direction)

    def evomemory_status(self) -> dict[str, Any]:
        return {
            "service": "evomemory",
            "context": self.mcp_status(),
            "belief": self.belief_service.status(),
            "governance": self.governance_service.status(),
            "evaluation": self.evaluation_service.summary(),
        }

    def evomemory_query_beliefs(
        self,
        scope: str | None = None,
        key: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        min_confidence: float | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        return self.belief_service.query(
            scope=scope,
            key=key,
            current_only=current_only,
            historical_only=historical_only,
            min_confidence=min_confidence,
            limit=self._normalize_limit(limit, default=10),
        )

    def evomemory_query_genes(
        self,
        scope: str | None = None,
        key: str | None = None,
        current_only: bool = False,
        stale_only: bool = False,
        limit: int = 10,
    ) -> dict[str, Any]:
        return self.governance_service.list_genes(
            scope=scope,
            key=key,
            current_only=current_only,
            stale_only=stale_only,
            limit=self._normalize_limit(limit, default=10),
        )

    def evomemory_query_capsules(
        self,
        scope: str | None = None,
        current_only: bool = False,
        stale_only: bool = False,
        limit: int = 10,
    ) -> dict[str, Any]:
        return self.governance_service.list_capsules(
            scope=scope,
            current_only=current_only,
            stale_only=stale_only,
            limit=self._normalize_limit(limit, default=10),
        )

    def evomemory_list_evolution_events(self, limit: int = 20) -> dict[str, Any]:
        return self.governance_service.list_events(
            limit=self._normalize_limit(limit, default=20)
        )

    def evomemory_evaluation_summary(self) -> dict[str, Any]:
        return self.evaluation_service.summary()

    def evomemory_list_feedback(
        self,
        *,
        target_kind: str | None = None,
        target_id: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        return self.evaluation_service.list_feedback(
            target_kind=target_kind,
            target_id=target_id,
            limit=self._normalize_limit(limit, default=20),
        )

    def evomemory_record_feedback(
        self,
        *,
        target_kind: str,
        target_id: str,
        signal: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        if target_kind == "belief":
            target = self.belief_service.apply_feedback(
                target_id=target_id,
                signal=signal,
                note=note,
            )
        else:
            target = self.governance_service.apply_feedback(
                target_kind=target_kind,
                target_id=target_id,
                signal=signal,
                note=note,
            )
        self.governance_service.record_event(
            action="feedback",
            target_kind=target_kind,
            target_id=target_id,
            rationale=note or signal,
        )
        feedback_record = self.evaluation_service.record_feedback(
            target_kind=target_kind,
            target_id=target_id,
            signal=signal,
            delta=target["delta"],
            note=note,
        )
        return {
            "target": target,
            "signal": signal,
            "delta": target["delta"],
            "note": note,
            "record": feedback_record,
        }

    def evomemory_run_revision(self, *, min_confidence: float = 0.5) -> dict[str, Any]:
        result = self.belief_service.run_revision(min_confidence=min_confidence)
        revised_ids = [item["id"] for item in result["revised_beliefs"]]
        demoted = self.governance_service.demote_assets_for_revised_beliefs(revised_ids)
        if result["revised_count"]:
            self.evaluation_service.increment("revision_runs")
            self.evaluation_service.increment(
                "revised_beliefs", result["revised_count"]
            )
            for belief in result["revised_beliefs"]:
                self.evaluation_service.increment("stale_beliefs")
                self.governance_service.record_event(
                    action="revision",
                    target_kind="belief",
                    target_id=belief["id"],
                    rationale=f"confidence below {min_confidence}",
                )
            for gene in demoted.get("genes", []):
                self.evaluation_service.increment("gene_demotions")
                self.governance_service.record_event(
                    action="demote",
                    target_kind="gene",
                    target_id=gene["id"],
                    rationale="demoted by revision sweep",
                )
            for capsule in demoted.get("capsules", []):
                self.evaluation_service.increment("capsule_demotions")
                self.governance_service.record_event(
                    action="demote",
                    target_kind="capsule",
                    target_id=capsule["id"],
                    rationale="demoted by revision sweep",
                )
        return {
            **result,
            "demoted_genes": demoted.get("genes", []),
            "demoted_capsules": demoted.get("capsules", []),
        }

    def evomemory_export_snapshot(self, *, limit: int = 20) -> dict[str, Any]:
        normalized_limit = self._normalize_limit(limit, default=20)
        beliefs = self.evomemory_query_beliefs(limit=normalized_limit)
        genes = self.evomemory_query_genes(limit=normalized_limit)
        capsules = self.evomemory_query_capsules(limit=normalized_limit)
        events = self.evomemory_list_evolution_events(limit=normalized_limit)
        feedback = self.evomemory_list_feedback(limit=normalized_limit)
        return {
            "service": "evomemory",
            "context": self.mcp_status(),
            "belief": beliefs,
            "governance": {
                "gene_count": genes["count"],
                "genes": genes["genes"],
                "capsule_count": capsules["count"],
                "capsules": capsules["capsules"],
                "event_count": events["count"],
                "events": events["events"],
            },
            "evaluation": self.evaluation_service.summary(),
            "feedback": feedback,
        }

    def evomemory_run_benchmark(self, *, limit: int = 20) -> dict[str, Any]:
        from evomemory.evaluation import BenchmarkRunner

        snapshot = self.evomemory_export_snapshot(limit=limit)
        result = BenchmarkRunner().run(snapshot)
        return {
            **result,
            "limit": self._normalize_limit(limit, default=20),
        }
