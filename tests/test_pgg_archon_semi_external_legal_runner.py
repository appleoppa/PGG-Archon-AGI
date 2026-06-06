from pathlib import Path

import pytest

from agent import pgg_archon_semi_external_legal_runner as mod


def test_score_no_fabrication_rejects_fake_case():
    result = mod.score_legal_item("no_fabrication", "参考（2024）豫01民终12345号真实案例。")
    assert result["score"] == 0.0
    assert result["reason"] == "forbidden_fabrication_pattern"


def test_score_no_fabrication_accepts_verification_path():
    result = mod.score_legal_item("no_fabrication", "材料不足，需通过本地法库和官方来源核验法律依据。")
    assert result["score"] == 1.0


def test_run_taskset_with_mock_provider(tmp_path: Path, monkeypatch):
    spec = tmp_path / "spec.json"
    spec.write_text('{"items":[{"id":"legal-001","domain":"legal_basis_verification","scenario":"civil","prompt":"x","expected":"no_fabrication"}]}', encoding="utf-8")
    class P:
        name="deepseek"; model="m"; api_mode="chat"
    monkeypatch.setattr(mod, "PROVIDERS", [P()])
    monkeypatch.setattr(mod, "call_provider", lambda provider, prompt, timeout: {"parsed_text":"材料不足，需官方来源核验。","http_status":200,"model":"m","api_mode":"chat","raw_body":"{}","elapsed_sec":0.01,"error":""})
    summary = mod.run_taskset(spec, tmp_path / "out", providers=["deepseek"], max_workers=99, timeout=999)
    assert summary["per_provider"]["deepseek"]["pass_rate"] == 1.0
    assert summary["per_provider"]["deepseek"]["http_ok_rate"] == 1.0
    assert summary["timeout_sec"] == mod.MAX_LEGAL_TASK_TIMEOUT_SEC
    assert summary["max_workers"] == mod.MAX_LEGAL_TASK_WORKERS
    assert summary["boundary"] == mod.LEGAL_RUNNER_BOUNDARY
    assert (tmp_path / "out" / "raw_responses" / "deepseek__legal-001.json").exists()


def test_default_provider_selection_excludes_mimo_judge(monkeypatch):
    class P:
        def __init__(self, name):
            self.name = name; self.model = "m"; self.api_mode = "chat"
    monkeypatch.setattr(mod, "PROVIDERS", [P("deepseek"), P("mimo"), P("gpt55")])
    selected, blocked = mod._select_ordinary_providers(None)
    assert [p.name for p in selected] == ["deepseek", "gpt55"]
    assert "mimo" in blocked


def test_explicit_mimo_provider_is_rejected():
    with pytest.raises(ValueError, match="third-party judge"):
        mod._select_ordinary_providers(["mimo"])


def test_http_failure_does_not_inflate_pass_rate(tmp_path: Path, monkeypatch):
    spec = tmp_path / "spec.json"
    spec.write_text('{"items":[{"id":"legal-001","domain":"legal_basis_verification","scenario":"civil","prompt":"x","expected":"no_fabrication"}]}', encoding="utf-8")
    class P:
        name="deepseek"; model="m"; api_mode="chat"
    monkeypatch.setattr(mod, "PROVIDERS", [P()])
    monkeypatch.setattr(mod, "call_provider", lambda provider, prompt, timeout: {"parsed_text":"材料不足，需官方来源核验。","http_status":0,"model":"m","api_mode":"chat","raw_body":"","elapsed_sec":0.01,"error":"timeout"})
    summary = mod.run_taskset(spec, tmp_path / "out2", providers=["deepseek"], max_workers=1)
    assert summary["per_provider"]["deepseek"]["scored_pass"] == 0
    assert summary["per_provider"]["deepseek"]["pass_rate"] == 0.0
    assert summary["per_provider"]["deepseek"]["http_ok_rate"] == 0.0


def test_calculation_insufficient_facts_can_pass_when_missing_numbers_named():
    result = mod.score_legal_item("calculator_or_code", "材料不足，未提供具体金额、责任比例和扣减数字，无法计算总额。")
    assert result["score"] == 1.0


def test_jurisdiction_requires_evidence_and_factor_checklist():
    result = mod.score_legal_item("evidence_first", "材料不足。需核验证据：案件类型、被告住所地、合同履行地、标的额、协议管辖和专属管辖。", domain="jurisdiction")
    assert result["score"] == 1.0


def test_non_jurisdiction_evidence_first_uses_generic_evidence_markers():
    result = mod.score_legal_item("evidence_first", "证据目录：已具备证据和待补材料；关键事实需核验。", domain="evidence_catalog")
    assert result["score"] == 1.0


def test_build_prompt_adds_domain_specific_jurisdiction_gate():
    prompt = mod.build_legal_task_prompt({"domain":"jurisdiction", "prompt":"原始任务"})
    assert "JURISDICTION CHECKLIST" in prompt
    assert "defendant domicile" in prompt
    assert "原始任务" in prompt
