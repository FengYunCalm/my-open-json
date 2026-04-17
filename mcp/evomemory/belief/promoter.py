from __future__ import annotations

from typing import Any


class MemoryPromoter:
    def __init__(
        self,
        belief_service: Any,
        governance_service: Any,
        evaluation_service: Any | None = None,
    ):
        self.belief_service = belief_service
        self.governance_service = governance_service
        self.evaluation_service = evaluation_service

    def promote_saved_memory(
        self,
        *,
        scope: str,
        memory_tier: str,
        memory_key: str,
        memory_value: str,
        source_session: str,
        source_message_id: str | None,
        source_record_id: str | None,
        valid_from: str,
        initial_source_count: int = 1,
    ) -> dict[str, Any]:
        promotion = self.belief_service.promote(
            scope=scope,
            key=memory_key,
            value=memory_value,
            memory_tier=memory_tier,
            source_session=source_session,
            source_message_id=source_message_id,
            source_record_id=source_record_id,
            valid_from=valid_from,
            initial_source_count=initial_source_count,
        )

        recorded_events = []
        gene = None
        capsule = None

        if promotion.get("created"):
            if self.evaluation_service is not None:
                self.evaluation_service.increment("belief_promotions")
            recorded_events.append(
                self.governance_service.record_event(
                    action="promote",
                    target_kind="belief",
                    target_id=promotion["fact"]["id"],
                    rationale=f"promoted from {memory_tier}",
                    source_record_id=source_record_id,
                )
            )
            gene_result = self.governance_service.ensure_gene_from_belief(
                promotion["fact"]
            )
            gene = gene_result["gene"]
            if gene_result.get("created"):
                if self.evaluation_service is not None:
                    self.evaluation_service.increment("gene_promotions")
                recorded_events.append(
                    self.governance_service.record_event(
                        action="promote",
                        target_kind="gene",
                        target_id=gene["id"],
                        rationale=f"derived from belief {promotion['fact']['id']}",
                        source_record_id=source_record_id,
                    )
                )
            capsule_result = self.governance_service.ensure_capsule_for_gene(
                scope,
                gene["id"],
            )
            capsule = capsule_result["capsule"]
            if capsule_result.get("created"):
                if self.evaluation_service is not None:
                    self.evaluation_service.increment("capsule_promotions")
                recorded_events.append(
                    self.governance_service.record_event(
                        action="promote",
                        target_kind="capsule",
                        target_id=capsule["id"],
                        rationale=f"created for scope {scope}",
                        source_record_id=source_record_id,
                    )
                )

        for superseded in promotion.get("superseded", []):
            if self.evaluation_service is not None:
                self.evaluation_service.increment("belief_supersedes")
                self.evaluation_service.increment("stale_beliefs")
            recorded_events.append(
                self.governance_service.record_event(
                    action="supersede",
                    target_kind="belief",
                    target_id=superseded["id"],
                    rationale=f"superseded by {promotion['fact']['id']}",
                    source_record_id=source_record_id,
                )
            )

        if promotion.get("superseded"):
            demoted = self.governance_service.demote_assets_for_superseded_beliefs(
                [item["id"] for item in promotion.get("superseded", [])]
            )
            for gene in demoted.get("genes", []):
                if self.evaluation_service is not None:
                    self.evaluation_service.increment("gene_demotions")
                recorded_events.append(
                    self.governance_service.record_event(
                        action="demote",
                        target_kind="gene",
                        target_id=gene["id"],
                        rationale=f"stale because source belief was superseded by {promotion['fact']['id']}",
                        source_record_id=source_record_id,
                    )
                )
            for capsule in demoted.get("capsules", []):
                if self.evaluation_service is not None:
                    self.evaluation_service.increment("capsule_demotions")
                recorded_events.append(
                    self.governance_service.record_event(
                        action="demote",
                        target_kind="capsule",
                        target_id=capsule["id"],
                        rationale=f"stale because underlying belief was superseded by {promotion['fact']['id']}",
                        source_record_id=source_record_id,
                    )
                )

        return {
            "belief": promotion["fact"],
            "created": promotion.get("created", False),
            "superseded": promotion.get("superseded", []),
            "gene": gene,
            "capsule": capsule,
            "events": recorded_events,
        }


__all__ = ["MemoryPromoter"]
