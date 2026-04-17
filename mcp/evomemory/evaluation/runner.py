from __future__ import annotations


class BenchmarkRunner:
    def _scenario_summary(self, snapshot: dict) -> dict:
        current_beliefs = [
            item
            for item in snapshot.get("belief", {}).get("facts", [])
            if not item.get("valid_to")
        ]
        current_genes = [
            item
            for item in snapshot.get("governance", {}).get("genes", [])
            if not item.get("is_stale")
        ]
        current_capsules = [
            item
            for item in snapshot.get("governance", {}).get("capsules", [])
            if not item.get("is_stale")
        ]
        return {
            "captured_belief_keys": sorted(
                {
                    item.get("key")
                    for item in current_beliefs
                    if item.get("key") is not None
                }
            ),
            "gene_keys": sorted(
                {
                    item.get("key")
                    for item in current_genes
                    if item.get("key") is not None
                }
            ),
            "capsule_scopes": sorted(
                {
                    item.get("scope")
                    for item in current_capsules
                    if item.get("scope") is not None
                }
            ),
        }

    def run(self, snapshot: dict) -> dict:
        belief_count = int(snapshot.get("belief", {}).get("count", 0))
        governance = snapshot.get("governance", {})
        gene_count = int(governance.get("gene_count", 0))
        capsule_count = int(governance.get("capsule_count", 0))
        feedback_count = int(snapshot.get("feedback", {}).get("count", 0))
        metrics = snapshot.get("evaluation", {}).get("metrics", {})
        search_context_calls = int(metrics.get("search_context_calls", 0))
        enriched_searches = int(metrics.get("enriched_searches", 0))
        scenario_summary = self._scenario_summary(snapshot)

        checks = {
            "belief_present": belief_count > 0,
            "governance_present": gene_count > 0 and capsule_count > 0,
            "feedback_present": feedback_count > 0,
            "search_enrichment_present": search_context_calls > 0
            and enriched_searches > 0,
        }
        scenario_checks = {
            "response_language_captured": "response_language"
            in scenario_summary["captured_belief_keys"],
            "git_commit_gene_present": "git_commit_behavior"
            in scenario_summary["gene_keys"],
            "project_capsule_present": "project" in scenario_summary["capsule_scopes"],
            "search_enrichment_active": search_context_calls > 0
            and enriched_searches > 0,
        }
        score = sum(1 for passed in checks.values() if passed) + sum(
            1 for passed in scenario_checks.values() if passed
        )
        return {
            "score": score,
            "checks": checks,
            "scenario_checks": scenario_checks,
            "scenario_summary": scenario_summary,
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
