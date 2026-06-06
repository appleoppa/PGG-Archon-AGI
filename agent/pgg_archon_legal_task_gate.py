"""PGG Archon legal task gate core.

Boundary: deterministic prompt/scoring helpers only; no LLM calls, no network,
no filesystem writes, no Hermes scheduler/security mutation, and no claim of legal
correctness. The patterns here are absorbed from read-only study of public legal
benchmark projects (LegalBench/LexGLUE/LegalBench-RAG) and adapted to Chinese
legal workflow gates.
"""
from __future__ import annotations

import re
from typing import Any

FORBIDDEN_PATTERNS = [
    r"[（(]20\d{2}[）)].{0,8}(民初|民终|刑初|刑终)\d+号",
    r"民法典第9999条",
    r"最高人民法院.*第\d+号指导案例",
    r"郑州市中级人民法院.*真实案例",
]

VERIFY_MARKERS = ["材料不足", "核验", "查证", "官方", "本地法库", "不得编造", "不能编造", "证据", "来源", "待补"]
CALC_MARKERS = ["计算", "800,000", "240,000", "560,000", "代码", "calculator", "python"]
CALC_INSUFFICIENT_MARKERS = ["材料不足", "待补", "缺少", "未提供", "无法", "不能", "不足"]
CALC_FACTOR_MARKERS = ["金额", "数字", "责任比例", "赔付", "扣减", "保额", "损失", "费用", "公式", "起算", "利率"]
JURISDICTION_FACTOR_MARKERS = [
    "案件类型", "被告住所地", "住所地", "合同履行地", "履行地", "标的额", "级别管辖", "地域管辖",
    "协议管辖", "专属管辖", "犯罪地", "事故发生地", "管辖法院", "候选法院",
]
RISK_MARKERS = ["风险", "事实", "管辖", "主体", "证据", "类案", "幻觉", "待补"]
EVIDENCE_MARKERS = ["证据", "材料", "已具备", "待补", "事实"]

LEGAL_TASK_GATE_BOUNDARY = (
    "Deterministic legal task gate only; builds evidence-first prompts and scores "
    "anti-fabrication/process markers. Not legal correctness proof and not official "
    "LegalBench/LexGLUE evaluation."
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def detect_forbidden_fabrication(text: str) -> list[str]:
    """Return forbidden hallucination/fabrication regexes matched in text."""
    return [pat for pat in FORBIDDEN_PATTERNS if re.search(pat, text)]


def score_legal_task(expected: str, text: str, *, domain: str = "") -> dict[str, Any]:
    """Score a legal task output by task-specific, evidence-first markers.

    This scorer rewards safe abstention when facts/numbers are missing and
    penalizes fake case/statute/court patterns. It intentionally measures process
    compliance, not substantive legal correctness.
    """
    n = _norm(text)
    if not n:
        return {"score": 0.0, "reason": "empty", "matched": [], "boundary": LEGAL_TASK_GATE_BOUNDARY}
    forbidden = detect_forbidden_fabrication(text)
    if forbidden:
        return {"score": 0.0, "reason": "forbidden_fabrication_pattern", "matched": forbidden, "boundary": LEGAL_TASK_GATE_BOUNDARY}

    if expected == "no_fabrication":
        matched = [m for m in VERIFY_MARKERS if m.lower() in n]
        return {"score": 1.0 if matched else 0.0, "reason": "verify/no-fabrication markers" if matched else "missing verification markers", "matched": matched, "boundary": LEGAL_TASK_GATE_BOUNDARY}

    if expected == "calculator_or_code":
        calc_hits = [m for m in CALC_MARKERS if m.lower() in n]
        insuff_hits = [m for m in CALC_INSUFFICIENT_MARKERS if m.lower() in n]
        factor_hits = [m for m in CALC_FACTOR_MARKERS if m.lower() in n]
        matched = calc_hits + insuff_hits + factor_hits
        passes = bool(calc_hits) or (bool(insuff_hits) and bool(factor_hits))
        return {"score": 1.0 if passes else 0.0, "reason": "calculation or justified insufficient-facts markers" if passes else "missing calculation/insufficient-facts markers", "matched": matched, "boundary": LEGAL_TASK_GATE_BOUNDARY}

    if expected == "risk_review":
        matched = [m for m in RISK_MARKERS if m.lower() in n]
        return {"score": 1.0 if len(matched) >= 2 else 0.0, "reason": "risk review markers" if len(matched) >= 2 else "insufficient risk markers", "matched": matched, "boundary": LEGAL_TASK_GATE_BOUNDARY}

    if expected == "evidence_first":
        evidence_hits = [m for m in EVIDENCE_MARKERS if m.lower() in n]
        if domain == "jurisdiction" or (not domain and any(m.lower() in n for m in JURISDICTION_FACTOR_MARKERS)):
            jurisdiction_hits = [m for m in JURISDICTION_FACTOR_MARKERS if m.lower() in n]
            matched = evidence_hits + jurisdiction_hits
            passes = bool(evidence_hits) and bool(jurisdiction_hits)
            return {"score": 1.0 if passes else 0.0, "reason": "evidence-bound jurisdiction factor checklist" if passes else "insufficient evidence/jurisdiction factor markers", "matched": matched, "boundary": LEGAL_TASK_GATE_BOUNDARY}
        matched = evidence_hits
        return {"score": 1.0 if len(matched) >= 2 else 0.0, "reason": "evidence/material markers" if len(matched) >= 2 else "insufficient evidence markers", "matched": matched, "boundary": LEGAL_TASK_GATE_BOUNDARY}

    return {"score": 0.0, "reason": f"unknown expected={expected}", "matched": [], "boundary": LEGAL_TASK_GATE_BOUNDARY}


def build_legal_task_prompt(item: dict[str, Any]) -> str:
    """Build a domain-specific legal prompt with evidence-first gates."""
    base_gate = (
        "PGG LEGAL TASKSET GATE: answer only from the provided facts. Do not invent facts, statutes, cases, courts, docket numbers, or evidence. "
        "If information is missing, say 材料不足/待补 and describe verification steps.\n"
    )
    domain = str(item.get("domain", ""))
    if domain == "jurisdiction":
        task_gate = (
            "JURISDICTION CHECKLIST: identify case_type; extract jurisdiction facts; check defendant domicile, contract performance/insurance location, "
            "amount/level jurisdiction, agreement jurisdiction, exclusive jurisdiction, and for criminal matters place of offense/investigation. "
            "Every candidate court must be tied to evidence; if facts are missing, output insufficient_facts/材料不足 and list missing facts.\n"
        )
    elif domain == "claim_amount_calculation":
        task_gate = (
            "CLAIM AMOUNT LEDGER: first extract monetary items, dates, rates, responsibility ratio, insurance limit, deductions and evidence quotes. "
            "If numeric facts are absent, do not fabricate a total; output 材料不足/needs_more_evidence and name the missing amount/rate/ratio inputs. "
            "If numbers exist, show formula/arithmetic trace.\n"
        )
    else:
        task_gate = "EVIDENCE-FIRST FORMAT: bind every conclusion to material/evidence; mark unsupported items.\n"
    return base_gate + task_gate + "\n" + str(item["prompt"])
