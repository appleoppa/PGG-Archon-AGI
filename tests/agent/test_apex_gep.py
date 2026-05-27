from __future__ import annotations

from agent.apex_gep import (
    REQUIRED_GEP_COMPONENTS,
    build_gep_capability_index,
    build_gep_report_from_runtimeos_status,
    build_gep_safety_pipeline,
    build_question_gate_report,
    build_validator_gate_report,
    is_infra_question_context,
)


def test_gep_capability_index_warns_on_obfuscated_archived_components():
    report = build_gep_capability_index()
    assert report["schema"] == "ApexRuntimeOSGEPCapabilityIndex/v1"
    assert report["status"] == "WARN"
    assert report["component_count"] == len(REQUIRED_GEP_COMPONENTS)
    assert report["counts"]["archived_obfuscated"] >= 1
    assert report["side_effects"] == "read_only_report"
    assert "JavaScript is not executed" in report["boundary"]


def test_gep_capability_index_blocks_missing_component():
    report = build_gep_capability_index({"questionGenerator": {"status": "readable_archived", "role": "q"}})
    assert report["status"] == "BLOCK"
    assert any(item["code"] == "missing_component" for item in report["issues"])


def test_question_gate_accepts_non_infra_question_with_signals():
    report = build_question_gate_report([
        {"question": "How can a repair loop be broken with a new architecture?", "priority": 3, "signals": ["repair_loop"]}
    ])
    assert report["schema"] == "ApexRuntimeOSGEPQuestionGate/v1"
    assert report["status"] == "PASS"
    assert report["accepted_count"] == 1
    assert report["accepted"][0]["signal_count"] == 1


def test_question_gate_suppresses_infra_and_duplicate_questions():
    question = "How to fix 429 rate limit invalid api key failure?"
    report = build_question_gate_report([
        {"question": question, "priority": 2, "signals": ["recurring_error"]},
        {"question": question, "priority": 2, "signals": ["recurring_error"]},
    ])
    codes = {item["code"] for item in report["issues"]}
    assert report["status"] == "BLOCK"
    assert "infra_question_suppressed" in codes
    assert "duplicate_question" in codes
    assert is_infra_question_context(question) is True


def test_validator_gate_requires_all_safety_guards():
    blocked = build_validator_gate_report({})
    assert blocked["status"] == "BLOCK"
    assert {item["code"] for item in blocked["issues"]} >= {
        "validator_disabled",
        "preflight_missing",
        "sandbox_missing",
        "tasks_only_guard_missing",
        "max_tasks_out_of_range",
    }
    passed = build_validator_gate_report({
        "enabled": True,
        "preflight_ok": True,
        "sandbox_ok": True,
        "tasks_only": True,
        "max_tasks_per_cycle": 2,
    })
    assert passed["status"] == "PASS"
    assert passed["issues"] == []


def test_gep_safety_pipeline_keeps_archived_components_on_hold():
    index = build_gep_capability_index()
    pipeline = build_gep_safety_pipeline(index)
    assert pipeline["schema"] == "ApexRuntimeOSGEPSafetyPipeline/v1"
    assert pipeline["status"] == "HOLD"
    assert pipeline["runtime_allowed"] is False
    assert "deobfuscation_review" in pipeline["hold_reasons"]
    assert "runtime_execution" in pipeline["hold_reasons"]
    assert pipeline["side_effects"] == "read_only_report"
    assert "no external repositories" in pipeline["boundary"]


def test_gep_report_from_runtimeos_status_is_read_only():
    report = build_gep_report_from_runtimeos_status({"schema": "ApexRuntimeOSAutonomyStatus/v1"})
    assert report["schema"] == "ApexRuntimeOSGEPReport/v1"
    assert report["status"] == "WARN"
    assert report["capability_index"]["component_count"] == len(REQUIRED_GEP_COMPONENTS)
    assert report["safety_pipeline"]["runtime_allowed"] is False
    assert report["question_gate"]["status"] == "BLOCK"
    assert report["validator_gate"]["status"] == "BLOCK"
    assert report["side_effects"] == "read_only_report"
