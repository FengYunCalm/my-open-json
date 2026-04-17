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
        runtime_context = snapshot.get("runtime_context") or {}
        budget_policy = snapshot.get("context", {}).get("budget_policy") or {}
        budget_policy_diff = snapshot.get("context", {}).get("budget_policy_diff") or {}
        runtime_candidate_belief_keys = list(
            runtime_context.get("belief_memory_keys") or []
        )
        runtime_candidate_gene_keys = list(
            runtime_context.get("governance_gene_keys") or []
        )
        runtime_belief_keys = (
            list(runtime_context.get("displayed_belief_keys") or [])
            if "displayed_belief_keys" in runtime_context
            else runtime_candidate_belief_keys
        )
        runtime_gene_keys = (
            list(runtime_context.get("displayed_governance_gene_keys") or [])
            if "displayed_governance_gene_keys" in runtime_context
            else runtime_candidate_gene_keys
        )
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
            "runtime_block_length": int(
                runtime_context.get("system_block_length") or 0
            ),
            "runtime_block_char_limit": runtime_context.get("system_block_char_limit"),
            "runtime_candidate_belief_keys": runtime_candidate_belief_keys,
            "runtime_candidate_gene_keys": runtime_candidate_gene_keys,
            "runtime_belief_keys": runtime_belief_keys,
            "runtime_gene_keys": runtime_gene_keys,
            "runtime_capsule_scopes": (
                list(runtime_context.get("displayed_capsule_scopes") or [])
                if "displayed_capsule_scopes" in runtime_context
                else list(runtime_context.get("capsule_scopes") or [])
            ),
            "budget_policy": budget_policy,
            "budget_policy_diff": budget_policy_diff,
            "top_runtime_belief_key": (
                runtime_candidate_belief_keys[0]
                if runtime_candidate_belief_keys
                else None
            ),
            "top_runtime_gene_key": (
                runtime_candidate_gene_keys[0] if runtime_candidate_gene_keys else None
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
            "runtime_block_within_budget": (
                scenario_summary["runtime_block_char_limit"] is not None
                and scenario_summary["runtime_block_length"] > 0
                and scenario_summary["runtime_block_length"]
                <= scenario_summary["runtime_block_char_limit"]
            ),
            "runtime_top_belief_retained": (
                scenario_summary["top_runtime_belief_key"] is not None
                and scenario_summary["top_runtime_belief_key"]
                in scenario_summary["runtime_belief_keys"]
            ),
            "runtime_top_gene_retained": (
                scenario_summary["top_runtime_gene_key"] is not None
                and scenario_summary["top_runtime_gene_key"]
                in scenario_summary["runtime_gene_keys"]
            ),
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
