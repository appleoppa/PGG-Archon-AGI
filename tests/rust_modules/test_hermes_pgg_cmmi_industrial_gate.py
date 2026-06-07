from __future__ import annotations

import json


def test_cmmi_industrial_gate_sample_is_bounded_pass_with_live_hold() -> None:
    import hermes_pgg_cmmi_industrial_gate as gate

    evidence = json.loads(gate.sample_input_json())
    decision = json.loads(gate.evaluate_evidence_json(json.dumps(evidence)))

    assert "Super Evolution 18" in gate.version()
    assert decision["schema"] == "HermesPGGCMMIIndustrialGate/v1"
    assert decision["status"] == "PASS_BOUNDED_CMMI18_CORE_FUSION_LIVE_AUTOMATION_HOLD"
    assert decision["score"] >= 0.85
    assert "formal CMMI certification" in decision["boundary"]
    assert any("GitHub" in item or "Docker" in item for item in decision["recommended_next"])
    assert "live_automation_not_fully_authorized_or_not_run_0/5" in decision["gaps"]


def test_cmmi_industrial_gate_blocks_surface_only_probe_overclaim() -> None:
    import hermes_pgg_cmmi_industrial_gate as gate

    evidence = json.loads(gate.sample_input_json())
    evidence["industrial_loop"].update(
        {
            "gpt_plan_schema_present": False,
            "coding_diff_trace_schema_present": False,
            "pr_review_gate_schema_present": False,
            "automated_test_gate_schema_present": False,
            "github_release_gate_schema_present": False,
            "auto_report_schema_present": False,
        }
    )
    evidence["runtime"].update(
        {
            "rust_compile_passed": False,
            "python_import_smoke_passed": False,
            "pytest_passed": False,
            "manifest_readback_present": False,
            "skill_reference_present": False,
        }
    )

    decision = json.loads(gate.evaluate_evidence_json(json.dumps(evidence)))

    assert decision["status"] != "PASS_BOUNDED_CMMI18_CORE_FUSION_LIVE_AUTOMATION_HOLD"
    assert decision["score"] < 0.85
    assert any(gap.startswith("industrial_loop_schema_partial") for gap in decision["gaps"])
    assert any(gap.startswith("runtime_fusion_partial") for gap in decision["gaps"])


def test_cmmi_python_bridge_builds_current_evidence_without_provider_calls() -> None:
    from agent.pgg_archon_cmmi_industrial_gate import build_current_evidence

    evidence = build_current_evidence(
        rust_compile_passed=True,
        python_import_smoke_passed=True,
        pytest_passed=True,
        manifest_readback_present=True,
        skill_reference_present=True,
    )

    assert evidence["source"]["source_document_read"] is True
    assert evidence["llm"]["provider_calls_attempted"] >= 1
    assert evidence["llm"]["no_roleplay_provider_participation"] is True
    assert evidence["external_learning"]["github_api_repos_verified"] >= 5
    assert evidence["live_automation"]["production_publish_authorized"] is False
