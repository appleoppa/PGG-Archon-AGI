from __future__ import annotations

from agent.pgg_archon_benchmark_and_gene_gates import (
    coral_parallel_workspace_mini_benchmark,
    evaluate_all,
    gene_fusion_synergy_gate,
    gepa_prompt_evolution_mini_benchmark,
    reflexion_discovery_gate,
)


def packet():
    return {
        "gepa_benchmark": {
            "baseline_prompt": "answer with reasoning",
            "reflective_feedback": ["must cite evidence", "avoid AGI claims"],
            "candidate_variants": [
                {"prompt": "answer with reasoning and cite evidence"},
                {"prompt": "answer with reasoning, cite evidence, avoid AGI claims, include rollback"},
            ],
            "validation_cases": [
                {"id": "evidence", "required_terms": ["evidence"], "forbidden_terms": []},
                {"id": "boundary", "required_terms": ["avoid agi claims"], "forbidden_terms": ["full agi"]},
                {"id": "rollback", "required_terms": ["rollback"], "forbidden_terms": []},
            ],
        },
        "coral_benchmark": {
            "agents": ["researcher", "builder", "auditor"],
            "workspaces": ["wt_a", "wt_b", "wt_c"],
            "experiments": [
                {"id": "a", "score_delta": 0.05, "complexity_delta": 0.02, "regression_passed": True},
                {"id": "b", "score_delta": -0.01, "complexity_delta": 0.01, "regression_passed": True},
            ],
            "cross_agent_audit": "auditor reviews selected patch",
            "conflict_resolution": "reject conflicting shared edits",
        },
        "gene_fusion": {
            "parents": [{"id": "gepa", "score": 0.72}, {"id": "coral", "score": 0.76}],
            "offspring": {"id": "gepa_coral", "score": 0.86},
            "complexity_penalty": 0.03,
            "harmrate_penalty": 0.02,
            "regression_evidence": "mini-suite pass",
            "rollback_plan": "git revert scoped commit",
        },
        "reflexion_discovery": {
            "traces": [
                {"observation": "metadata-only blocks promotion", "lesson": "full text + benchmark required", "signals_match": ["metadata_only"], "validation": ["source card"]},
                {"observation": "parallel merge can regress", "lesson": "require final regression gate", "signals_match": ["parallel_merge"], "validation": ["pytest"]},
            ],
            "auto_promote": False,
        },
    }


def test_gepa_mini_benchmark_passes_and_blocks_no_variants():
    out = gepa_prompt_evolution_mini_benchmark(packet()["gepa_benchmark"])
    assert out["status"] == "PASS"
    assert out["benchmark_regression_passed"] is True
    bad = dict(packet()["gepa_benchmark"])
    bad["candidate_variants"] = []
    assert gepa_prompt_evolution_mini_benchmark(bad)["status"] == "BLOCK"


def test_coral_mini_benchmark_blocks_shared_mutation():
    out = coral_parallel_workspace_mini_benchmark(packet()["coral_benchmark"])
    assert out["status"] == "PASS"
    bad = dict(packet()["coral_benchmark"])
    bad["shared_workspace_mutation"] = True
    ev = coral_parallel_workspace_mini_benchmark(bad)
    assert ev["status"] == "BLOCK"
    assert "shared_workspace_mutation_not_allowed" in ev["errors"]


def test_gene_fusion_synergy_gate_rejects_multiplier():
    out = gene_fusion_synergy_gate(packet()["gene_fusion"])
    assert out["status"] == "PASS"
    assert out["fusion_allowed"] is True
    bad = dict(packet()["gene_fusion"])
    bad["uses_arbitrary_multiplier"] = True
    ev = gene_fusion_synergy_gate(bad)
    assert ev["status"] == "BLOCK"
    assert "arbitrary_multiplier_not_allowed" in ev["errors"]


def test_reflexion_discovery_candidate_only():
    out = reflexion_discovery_gate(packet()["reflexion_discovery"])
    assert out["status"] == "PASS"
    assert out["candidate_count"] == 2
    assert out["promotion_performed"] is False
    assert all(c["status"] == "candidate" for c in out["candidates"])


def test_evaluate_all_passes(tmp_path):
    out = evaluate_all(packet(), output_dir=tmp_path)
    assert out["status"] == "PASS"
    assert out["blocked"] == []
    assert out["promotion_performed"] is False
    assert "output_path" in out
