from agent.pgg_archon_legal_task_gate import (
    LEGAL_TASK_GATE_BOUNDARY,
    build_legal_task_prompt,
    detect_forbidden_fabrication,
    score_legal_task,
)


def test_detect_forbidden_fabrication_rejects_fake_case_number() -> None:
    hits = detect_forbidden_fabrication("参考（2024）豫01民终12345号真实案例。")
    assert hits


def test_score_no_fabrication_accepts_verification_path() -> None:
    result = score_legal_task("no_fabrication", "材料不足，需通过本地法库和官方来源核验法律依据。")
    assert result["score"] == 1.0
    assert result["boundary"] == LEGAL_TASK_GATE_BOUNDARY


def test_score_calculation_accepts_justified_insufficient_facts() -> None:
    result = score_legal_task("calculator_or_code", "材料不足，未提供具体金额、责任比例和扣减数字，无法计算总额。", domain="claim_amount_calculation")
    assert result["score"] == 1.0


def test_score_jurisdiction_requires_evidence_and_factor_checklist() -> None:
    result = score_legal_task("evidence_first", "材料不足。需核验证据：案件类型、被告住所地、合同履行地、标的额、协议管辖和专属管辖。", domain="jurisdiction")
    assert result["score"] == 1.0


def test_non_jurisdiction_evidence_first_uses_generic_evidence_markers() -> None:
    result = score_legal_task("evidence_first", "证据目录：已具备证据和待补材料；关键事实需核验。", domain="evidence_catalog")
    assert result["score"] == 1.0


def test_build_prompt_adds_jurisdiction_gate() -> None:
    prompt = build_legal_task_prompt({"domain": "jurisdiction", "prompt": "原始任务"})
    assert "JURISDICTION CHECKLIST" in prompt
    assert "defendant domicile" in prompt
    assert "原始任务" in prompt


def test_build_prompt_adds_claim_amount_ledger_gate() -> None:
    prompt = build_legal_task_prompt({"domain": "claim_amount_calculation", "prompt": "原始任务"})
    assert "CLAIM AMOUNT LEDGER" in prompt
    assert "responsibility ratio" in prompt
    assert "原始任务" in prompt
