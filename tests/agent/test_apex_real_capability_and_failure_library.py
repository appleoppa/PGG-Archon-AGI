from __future__ import annotations

import json

from agent.apex_failure_sample_library import (
    append_failure_sample,
    build_detection_rule,
    build_failure_sample_library_status,
    load_failure_samples,
    redact_sensitive_text,
)
from agent.apex_low_risk_autonomy_candidates import generate_autonomy_candidates
from agent.apex_multi_model_evidence_ledger import build_multi_model_evidence_ledger
from agent.apex_real_capability_metrics import METRIC_IDS, build_real_capability_metrics_summary
from agent.apex_task_retrospective import append_task_retrospective, build_task_retrospective_status
from agent.apex_v3_unified_score import build_apex_v3_unified_score_report


def _perfect_status():
    return {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "quality_gate": {"status": "PASS", "evidence_bundle": {"valid": True}, "missing_blocking_evidence": []},
        "health_report": {"status": "OK"},
        "cron_dryrun": {"bad_lines": 0, "unique_keys": 1, "total_lines": 1},
        "era_report": {"status": "PASS", "selected_path_id": "safe"},
        "co_scientist_report": {"status": "PASS"},
        "co_scientist_gene_candidate": {"status": "READY", "gene_library_written": False},
        "gene_lifecycle_gate": {"status": "PASS", "issues": [], "gene_count": 1},
        "gep_report": {"status": "PASS", "safety_pipeline": {"actual_execution_allowed": False, "runtime_allowed": False}},
        "formula_report": {"status": "PASS", "live_params_used": True},
        "skill_registry_policy": {"status": "PASS"},
        "pending_rollbacks": 0,
        "promotion_lifecycle_gate": {"status": "PASS"},
        "flow_reward_report": {"valid": True, "status": "PASS", "selected_path_id": "p1", "score_delta": 0.1},
        "switch_cost_report": {"valid": True, "status": "PASS"},
        "meta_evolution_report": {"valid": True, "status": "PASS", "signals": {"strategy_ledger": True, "shadow_replay": True, "drift_sensor": True, "cost_sensor": True}},
        "cross_domain_core_gene_gate": {"status": "PASS"},
    }


def test_real_capability_metrics_missing_data_does_not_fabricate_scores():
    summary = build_real_capability_metrics_summary({})
    assert summary["schema"] == "ApexRealCapabilityMetrics/v1"
    assert summary["status"] == "UNKNOWN"
    assert summary["overall_score"] is None
    assert summary["metric_count"] == 9
    assert tuple(summary["metrics"].keys()) == METRIC_IDS
    assert summary["claims"]["agi_complete"] is False


def test_real_capability_metrics_uses_safe_aggregate_events_and_libraries():
    summary = build_real_capability_metrics_summary({
        "events": [
            {"source": "court", "evidence_hash": "h1", "fact_checked": True},
            {"tool_call": "pytest", "test_result": "pass", "artifact_hash": "h2"},
            {"legal_basis": "民法典", "law_checked": True, "hash": "h3"},
            {"delivered": True, "commit_sha": "abc", "remote_head": "abc", "evidence_hash": "h4"},
        ],
        "failure_samples": [{"error_type": "x", "next_intercept_method": "guard", "evidence_hash": "h5"}],
        "task_retrospectives": [{"what_happened": "x", "why": "y", "next_change": "z", "evidence_hash": "h6"}],
        "autonomy_candidates": [{"candidate_type": "skill_draft", "status": "REVIEW_REQUIRED", "review_required": True, "evidence_hash": "h7"}],
        "multi_model_ledger": [{"provider": "gpt", "model": "m", "status": "RECORDED", "decision": "hold", "evidence_hash": "h8"}],
    })
    assert summary["known_metric_count"] == 9
    assert summary["metrics"]["factual_grounding"]["status"] in {"PASS", "WATCH"}
    assert summary["metrics"]["evidence_chain"]["evidence_count"] >= 1


def test_failure_sample_append_only_and_schema(tmp_path):
    first = append_failure_sample({
        "error_type": "把报告当完成",
        "trigger_scenario": "文件存在后直接宣布闭环",
        "root_cause": "缺少测试和读回",
        "correct_action": "必须补验收证据",
        "raw_content": "api_key=SECRET123 user@example.com 13800138000",
    }, library_dir=tmp_path)
    second = append_failure_sample({
        "error_type": "reference_only 当 trusted skill",
        "trigger_scenario": "技能未验证",
        "root_cause": "信任边界错误",
        "correct_action": "阻断正式技能晋级",
    }, library_dir=tmp_path)
    assert first["bytes_before"] == 0
    assert second["bytes_after"] > first["bytes_after"]
    records = load_failure_samples(library_dir=tmp_path)
    assert len(records) == 2
    assert all(r["sensitive_content_stored"] is False for r in records)
    assert build_failure_sample_library_status(library_dir=tmp_path)["status"] == "PASS"


def test_sensitive_content_is_redacted_before_storage(tmp_path):
    result = append_failure_sample({
        "error_type": "泄露风险",
        "trigger_scenario": "日志包含 token=abc123",
        "root_cause": "未脱敏",
        "correct_action": "保存 hash 和脱敏摘要",
        "raw_content": "Bearer sk-test-token password=hunter2 11010519491231002X",
    }, library_dir=tmp_path)
    text = json.dumps(result["record"], ensure_ascii=False)
    assert "sk-test-token" not in text
    assert "hunter2" not in text
    assert "11010519491231002X" not in text
    assert "[REDACTED]" in text


def test_feishu_malformed_format_sample_generates_detection_rule():
    rule = build_detection_rule("飞书格式混乱", "用户要求法律办案汇报但标题层级错乱", "markdown 表格破裂")
    assert "feishu" in rule
    assert "ordered headings" in rule


def test_guards_detect_report_only_reference_only_fake_models_and_agi_claims():
    assert "without_acceptance_evidence" in build_detection_rule("文件存在", "把报告当完成", "无测试")
    assert "reference_only" in build_detection_rule("reference_only", "冒充 trusted skill", "未验证")
    assert "unverified_model_call" in build_detection_rule("虚构 GPT-Claude 调用", "多模型互补", "无 ledger")
    assert "agi_completion_claim" in build_detection_rule("AGI 完成声明", "统一评分 100", "无外部真值")


def test_unified_score_exposes_new_read_only_statuses():
    report = build_apex_v3_unified_score_report(_perfect_status())
    assert report["real_capability_metrics"]["schema"] == "ApexRealCapabilityMetrics/v1"
    assert report["failure_sample_library"]["side_effects"] == "read_only_status"
    assert report["task_retrospective_status"]["side_effects"] == "read_only_status"
    assert report["multi_model_evidence_ledger"]["external_calls_made"] is False
    assert report["agi_completion_claim"] is False
    assert report["allows_autonomous_promotion"] is False


def test_task_retrospective_three_questions_append_only(tmp_path):
    result = append_task_retrospective({
        "task_id": "t1",
        "what_happened": "完成低风险本地补齐",
        "why": "真实能力指标缺少样本闭环",
        "next_change": "下次先检查 failure library",
    }, library_dir=tmp_path)
    assert result["record"]["questions"] == ["what_happened", "why", "next_change"]
    assert build_task_retrospective_status(library_dir=tmp_path)["status"] == "PASS"


def test_low_risk_autonomy_candidates_are_review_only():
    result = generate_autonomy_candidates({
        "failure_samples": [{"error_type": "x"}],
        "real_capability_metrics": {"status": "WATCH"},
    })
    assert result["candidate_count"] == 2
    assert result["formal_skill_written"] is False
    assert result["formal_memory_written"] is False
    assert all(c["review_required"] is True for c in result["candidates"])


def test_multi_model_ledger_reads_existing_reviews_without_external_calls(tmp_path):
    review = tmp_path / "gpt_claude_next_stage_review.json"
    review.write_text(json.dumps({"provider": "gpt", "model": "reviewer", "content": "不允许 autonomous promotion"}, ensure_ascii=False), encoding="utf-8")
    ledger = build_multi_model_evidence_ledger(review_dir=tmp_path)
    assert ledger["status"] == "PASS"
    assert ledger["external_calls_made"] is False
    assert ledger["raw_responses_stored"] is False
    assert ledger["entries"][0]["decision"] == "hold_or_guarded_next_stage"
