from __future__ import annotations


class BenchmarkRunner:
    def run(self, snapshot: dict) -> dict:
        belief_count = int(snapshot.get("belief", {}).get("count", 0))
        governance = snapshot.get("governance", {})
        gene_count = int(governance.get("gene_count", 0))
        capsule_count = int(governance.get("capsule_count", 0))
        feedback_count = int(snapshot.get("feedback", {}).get("count", 0))
        metrics = snapshot.get("evaluation", {}).get("metrics", {})
        search_context_calls = int(metrics.get("search_context_calls", 0))
        enriched_searches = int(metrics.get("enriched_searches", 0))

        checks = {
            "belief_present": belief_count > 0,
            "governance_present": gene_count > 0 and capsule_count > 0,
            "feedback_present": feedback_count > 0,
            "search_enrichment_present": search_context_calls > 0
            and enriched_searches > 0,
        }
        score = sum(1 for passed in checks.values() if passed)
        return {
            "score": score,
            "checks": checks,
            "snapshot_overview": {
                "belief_count": belief_count,
                "gene_count": gene_count,
                "capsule_count": capsule_count,
                "feedback_count": feedback_count,
                "search_context_calls": search_context_calls,
                "enriched_searches": enriched_searches,
            },
        }


__all__ = ["BenchmarkRunner"]
