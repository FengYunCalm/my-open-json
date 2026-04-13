from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb

from mempalace.config import MempalaceConfig, sanitize_content, sanitize_name
from mempalace.knowledge_graph import KnowledgeGraph


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
PREVIEW_CHARS = 200
FETCH_BATCH_SIZE = 1000


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


def _preview_text(text: str, max_chars: int = PREVIEW_CHARS) -> str:
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 1] + "…"


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
    collection_name: str = "mempalace_drawers"
    state_path: Path | str = (
        Path.home() / ".config" / "opencode" / "mcp" / "mempalace_bridge_state.json"
    )
    wing_config_path: Path | str = Path.home() / ".mempalace" / "wing_config.json"
    default_room: str = "opencode-session"
    search_limit: int = 5
    max_block_chars: int = 2000
    min_meaningful_chars: int = 6

    def __post_init__(self):
        self.state_path = Path(self.state_path)
        self.wing_config_path = Path(self.wing_config_path)


class StateStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"sessions": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"sessions": {}}

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )


class MempalaceBackend:
    def __init__(self, config: BridgeConfig):
        self.bridge_config = config
        self.mempalace_config = MempalaceConfig()
        if config.palace_path:
            os.environ["MEMPALACE_PALACE_PATH"] = config.palace_path
        self.palace_path = config.palace_path or self.mempalace_config.palace_path
        self.collection_name = (
            config.collection_name or self.mempalace_config.collection_name
        )
        self._client: chromadb.PersistentClient | None = None
        self._collection = None
        self._kg = KnowledgeGraph(
            db_path=str(Path(self.palace_path) / "knowledge_graph.sqlite3")
        )

    def _client_for(self) -> chromadb.PersistentClient:
        if self._client is None:
            self._client = chromadb.PersistentClient(path=self.palace_path)
        return self._client

    def _collection_for(self, create: bool = False):
        if self._collection is not None:
            return self._collection
        client = self._client_for()
        if create:
            self._collection = client.get_or_create_collection(self.collection_name)
        else:
            self._collection = client.get_collection(self.collection_name)
        return self._collection

    def _make_where(
        self,
        *,
        wing: str | None = None,
        room: str | None = None,
        session_id: str | None = None,
        role: str | None = None,
        source_file: str | None = None,
    ) -> dict[str, Any] | None:
        conditions = []
        if wing is not None:
            conditions.append({"wing": wing})
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
            "source_file": metadata.get("source_file", ""),
            "session_id": metadata.get("session_id"),
            "message_id": metadata.get("message_id"),
            "role": metadata.get("role"),
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
        return [
            self._format_row(drawer_id=drawer_id, text=text, metadata=metadata)
            for drawer_id, text, metadata in zip(ids, documents, metadatas)
        ]

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
        payload = {
            "wing": wing,
            "room": room,
            "source_file": source_file,
            "chunk_index": 0,
            "added_by": "opencode-bridge",
            "filed_at": datetime.now(timezone.utc).isoformat(),
            **metadata,
        }
        collection.upsert(ids=[drawer_id], documents=[content], metadatas=[payload])
        return {"drawer_id": drawer_id, "wing": wing, "room": room, "metadata": payload}

    def status(self):
        try:
            collection = self._collection_for()
            total = collection.count()
        except Exception:
            total = 0
        return {"total_drawers": total, "palace_path": self.palace_path}

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
        for item in metadatas:
            wing = item.get("wing", "unknown")
            room = item.get("room", "unknown")
            taxonomy.setdefault(wing, {})
            taxonomy[wing][room] = taxonomy[wing].get(room, 0) + 1
        return taxonomy

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
    ) -> list[dict[str, Any]]:
        return self.query_drawers(
            wing=wing,
            room=room,
            session_id=session_id,
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
                    "last_filed_at": item.get("filed_at"),
                    "source_file": item.get("source_file", ""),
                },
            )
            entry["message_count"] += 1
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
        role: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        try:
            result = self._get_all(
                include=["documents", "metadatas"],
                where=self._make_where(session_id=session_id, role=role),
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
        self.state_store = StateStore(self.config.state_path)
        self.backend = backend or MempalaceBackend(self.config)

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
            "source_file": item.get("source_file"),
            "session_id": item.get("session_id"),
            "message_id": item.get("message_id"),
            "role": item.get("role"),
            "filed_at": item.get("filed_at"),
            "similarity": item.get("similarity", 0),
            "distance": item.get("distance"),
        }

    def _format_context_hit(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "text": item.get("text", ""),
            "preview": item.get("preview") or _preview_text(item.get("text", ""), 160),
            "wing": item.get("wing"),
            "room": item.get("room"),
            "source_file": item.get("source_file"),
            "session_id": item.get("session_id"),
            "message_id": item.get("message_id"),
            "role": item.get("role"),
            "similarity": item.get("similarity", 0),
        }

    def _build_system_block(self, wing: str, results: list[dict[str, Any]]) -> str:
        if not results:
            return ""
        lines = [f"MemPalace context for wing '{wing}':"]
        used = len(lines[0])
        for index, item in enumerate(results, start=1):
            header = (
                f"{index}. [{float(item.get('similarity', 0)):.2f}] "
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
        return "\n".join(lines)

    def health(self) -> dict[str, Any]:
        status = self.backend.status()
        return {"ok": True, **status}

    def start_session(self, session_id: str, directory: str) -> dict[str, Any]:
        state = self._load_state()
        sessions = state.setdefault("sessions", {})
        entry = sessions.setdefault(session_id, {})
        entry["directory"] = self._normalize_directory(directory)
        entry["wing"] = self.resolve_wing(directory)
        entry.setdefault("last_saved_message_id", None)
        entry.setdefault("last_saved_order", 0)
        self._save_state(state)
        return {
            "session_id": session_id,
            "wing": entry["wing"],
            "directory": entry["directory"],
        }

    def search_context(
        self, query: str, directory: str, session_id: str | None = None
    ) -> dict[str, Any]:
        wing = self.resolve_wing(directory)
        results = [
            self._format_context_hit(item)
            for item in self.backend.query_drawers(
                query=query, wing=wing, room=None, limit=self.config.search_limit
            )
            if item.get("text") and float(item.get("similarity", 0)) > 0
        ]
        return {
            "session_id": session_id,
            "query": query,
            "directory": self._normalize_directory(directory),
            "wing": wing,
            "results_count": len(results),
            "results": results,
            "system_block": self._build_system_block(wing, results),
        }

    def flush_session(
        self,
        session_id: str,
        directory: str,
        messages: list[dict[str, Any]],
        reason: str,
    ) -> dict[str, Any]:
        state = self._load_state()
        sessions = state.setdefault("sessions", {})
        session = sessions.setdefault(session_id, {})
        session.setdefault("directory", self._normalize_directory(directory))
        session.setdefault("wing", self.resolve_wing(directory))
        session.setdefault("last_saved_order", 0)
        new_messages = self._new_messages(
            messages, session.get("last_saved_message_id")
        )
        saved = []
        next_order = int(session.get("last_saved_order") or 0)

        for message in new_messages:
            info = message.get("info", {})
            role = info.get("role")
            if role not in VALID_ROLES:
                continue
            text = self._collect_text(message.get("parts", []))
            if not self._is_meaningful_text(text):
                continue
            next_order += 1
            content = f"{role.title()}:\n{text}"
            saved.append(
                self.backend.save_entry(
                    wing=session["wing"],
                    room=self.config.default_room,
                    content=content,
                    source_file=f"session:{session_id}",
                    metadata={
                        "type": "opencode_message",
                        "session_id": session_id,
                        "message_id": info.get("id"),
                        "role": role,
                        "reason": reason,
                        "directory": session["directory"],
                        "session_order": next_order,
                    },
                )
            )

        if messages:
            session["last_saved_message_id"] = messages[-1].get("info", {}).get("id")
        session["last_saved_order"] = next_order
        session["last_saved_at"] = datetime.now(timezone.utc).isoformat()
        self._save_state(state)
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

    def mcp_status(self) -> dict[str, Any]:
        payload = self.backend.status()
        payload.update(
            {"service": "mempalace-bridge", "state_path": str(self.config.state_path)}
        )
        return payload

    def mcp_list_wings(self) -> dict[str, Any]:
        return {"wings": self.backend.list_wings()}

    def mcp_list_rooms(self, wing: str | None = None) -> dict[str, Any]:
        try:
            safe_wing = _sanitize_optional_name(wing, "wing")
        except ValueError as exc:
            return {"error": str(exc)}
        return {
            "wing": safe_wing or "all",
            "rooms": self.backend.list_rooms(wing=safe_wing),
        }

    def mcp_get_taxonomy(self) -> dict[str, Any]:
        return {"taxonomy": self.backend.get_taxonomy()}

    def mcp_get_drawer(self, drawer_id: str) -> dict[str, Any]:
        result = self.backend.get_drawer(drawer_id)
        return result or {"error": f"Drawer not found: {drawer_id}"}

    def mcp_search(
        self,
        query: str,
        limit: int = 5,
        wing: str | None = None,
        room: str | None = None,
    ) -> dict[str, Any]:
        try:
            safe_wing = _sanitize_optional_name(wing, "wing")
            safe_room = _sanitize_optional_name(room, "room")
        except ValueError as exc:
            return {"error": str(exc)}
        results = [
            self._format_public_hit(item)
            for item in self.backend.query_drawers(
                query=query,
                wing=safe_wing,
                room=safe_room,
                limit=self._normalize_limit(limit, default=5),
            )
            if item.get("text") and float(item.get("similarity", 0)) > 0
        ]
        return {
            "query": query,
            "wing": safe_wing,
            "room": safe_room,
            "results": results,
        }

    def mcp_list_drawers(
        self,
        wing: str | None = None,
        room: str | None = None,
        session_id: str | None = None,
        role: str | None = None,
        source_file: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        try:
            safe_wing = _sanitize_optional_name(wing, "wing")
            safe_room = _sanitize_optional_name(room, "room")
            safe_role = _sanitize_optional_role(role)
        except ValueError as exc:
            return {"error": str(exc)}

        drawers = [
            self._format_public_hit(item)
            for item in self.backend.list_drawers(
                wing=safe_wing,
                room=safe_room,
                session_id=session_id,
                role=safe_role,
                source_file=source_file,
                limit=self._normalize_limit(limit),
                offset=self._normalize_offset(offset),
            )
        ]
        return {
            "wing": safe_wing,
            "room": safe_room,
            "session_id": session_id,
            "role": safe_role,
            "source_file": source_file,
            "count": len(drawers),
            "offset": self._normalize_offset(offset),
            "limit": self._normalize_limit(limit),
            "drawers": drawers,
        }

    def mcp_list_sessions(
        self,
        wing: str | None = None,
        room: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        try:
            safe_wing = _sanitize_optional_name(wing, "wing")
            safe_room = _sanitize_optional_name(room, "room")
        except ValueError as exc:
            return {"error": str(exc)}

        sessions = self.backend.list_sessions(
            wing=safe_wing,
            room=safe_room,
            limit=self._normalize_limit(limit),
            offset=self._normalize_offset(offset),
        )
        return {
            "wing": safe_wing,
            "room": safe_room,
            "count": len(sessions),
            "offset": self._normalize_offset(offset),
            "limit": self._normalize_limit(limit),
            "sessions": sessions,
        }

    def mcp_get_session_messages(
        self,
        session_id: str,
        role: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        try:
            safe_role = _sanitize_optional_role(role)
        except ValueError as exc:
            return {"error": str(exc)}

        messages = [
            self._format_public_hit(item)
            for item in self.backend.get_session_messages(
                session_id=session_id,
                role=safe_role,
                limit=self._normalize_limit(limit),
                offset=self._normalize_offset(offset),
            )
        ]
        return {
            "session_id": session_id,
            "role": safe_role,
            "count": len(messages),
            "offset": self._normalize_offset(offset),
            "limit": self._normalize_limit(limit),
            "messages": messages,
        }

    def mcp_kg_query(
        self, entity: str, as_of: str | None = None, direction: str = "both"
    ) -> dict[str, Any]:
        return self.backend.kg_query(entity, as_of=as_of, direction=direction)
