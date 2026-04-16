from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Scope = Literal["session", "user", "project", "agent", "global"]
Plane = Literal["context", "belief", "governance"]
Kind = Literal["event", "fact", "preference", "summary", "rule", "gene", "capsule"]
EvolutionAction = Literal["promote", "demote", "supersede", "confirm"]
EvolutionTargetKind = Literal["belief", "gene", "capsule"]


@dataclass(slots=True)
class MemoryRecord:
    scope: Scope
    plane: Plane
    kind: Kind
    key: str
    value: str
    source: str | None = None
    source_type: str | None = None
    source_session: str | None = None
    confidence: float | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    superseded_by: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Gene:
    id: str
    summary: str
    confidence: float | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Capsule:
    id: str
    summary: str
    gene_ids: list[str] = field(default_factory=list)
    confidence: float | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EvolutionEvent:
    id: str
    action: EvolutionAction
    target_kind: EvolutionTargetKind
    target_id: str
    source_record_id: str | None = None
    rationale: str | None = None
    created_at: str | None = None
