"""Read-only bridge from real legal case files into PGG Archon evidence loops.

The bridge scans sanitized case-process artifacts and emits aggregate events,
failure samples, and task retrospectives. It never mutates original case files,
never stores raw sensitive content, and never marks legal deliverables as final.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from agent.apex_failure_sample_library import append_failure_sample, evidence_hash_from_text, load_failure_samples
from agent.apex_task_retrospective import append_task_retrospective

DEFAULT_CASE_ROOT = Path.home() / ".hermes" / "workspace" / "苹果中枢办案库"
DEFAULT_EVENTS_DIR = Path("workspace/case_experience_events")

_CASE_ID_RE = re.compile(r"PGG-[A-Z]+-\d{8}-\d{3}")


@dataclass(frozen=True)
class CaseExperience:
    case_id: str
    case_name: str
    case_dir: str
    current_stage: str
    status: str
    internal_report_path: str
    deliverable_allowed: bool
    gates: tuple[str, ...]
    issues: tuple[str, ...]
    evidence_hash: str

    def to_event(self) -> dict[str, Any]:
        return {
            "schema": "PGGCaseExperienceEvent/v1",
            "case_id": self.case_id,
            "case_name_hash": _hash(self.case_name),
            "case_dir_hash": _hash(self.case_dir),
            "current_stage": self.current_stage,
            "status": self.status,
            "internal_report_hash": _hash(self.internal_report_path),
            "delivered": self.deliverable_allowed,
            "delivery_blocked": not self.deliverable_allowed,
            "evidence_hash": self.evidence_hash,
            "artifact_hash": self.evidence_hash,
            "legal_basis": "initial_or_formal_review_present" if any("律法" in g or "法律" in g for g in self.gates) else "pending_review",
            "verification": "case_file_readback",
            "acceptance": "internal_report_generated" if self.internal_report_path else "missing_internal_report",
            "source": "case_experience_bridge",
            "gates": list(self.gates),
            "issue_codes": list(self.issues),
            "sensitive_content_stored": False,
        }


def _hash(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _read_text(path: Path, limit: int = 20000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except Exception:
        return ""


def _first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists() and path.is_file():
            return path
    return None


def _extract_case_id(name: str, text: str) -> str:
    for source in (name, text):
        m = _CASE_ID_RE.search(source or "")
        if m:
            return m.group(0)
    return "UNKNOWN-CASE"


def _extract_case_name(text: str, case_id: str, fallback: str) -> str:
    for marker in ("案件名称", "案件：", "案件"):
        for line in text.splitlines()[:80]:
            if marker in line and case_id not in line:
                cleaned = re.sub(r"[|#>*`：:]", " ", line).strip()
                cleaned = re.sub(r"\s+", " ", cleaned)
                if len(cleaned) >= 4:
                    return cleaned[:120]
    return fallback[:120]


def _detect_stage_status(text: str) -> tuple[str, str, bool, tuple[str, ...], tuple[str, ...]]:
    lower = text.lower()
    deliverable_allowed = not any(token in text for token in ("不可对外交付", "不能直接对外交付", "暂不建议直接对外交付", "对外交付：否"))
    gates: list[str] = []
    issues: list[str] = []
    if "证据" in text and any(t in text for t in ("Hold", "HOLD", "hold")):
        gates.append("evidence_gate_hold")
        issues.append("evidence_gate_hold")
    if "内部办案流程报告" in text or "内部办案报告" in text:
        gates.append("internal_report_generated")
    if "部门" in text and ("超时" in text or "异常" in text):
        gates.append("department_flow_exception_marked")
        issues.append("department_timeout_or_exception")
    if "CASE-" in text and "正式案号" in text:
        gates.append("case_number_corrected")
        issues.append("case_number_boundary_violation")
    if "金额" in text and any(t in text for t in ("不闭合", "差额", "不再采用", "修正")):
        gates.append("amount_recalculated")
        issues.append("amount_closure_required")
    elif any(t in text for t in ("差额", "不再采用", "修正为", "待付款")) and re.search(r"\d[\d,]*\.\d{2}元", text):
        gates.append("amount_recalculated")
        issues.append("amount_closure_required")
    if "类案" in text and any(t in text for t in ("未实检", "不得引用")):
        gates.append("case_law_not_verified")
        issues.append("legal_case_research_pending")
    if "法律依据" in text or "律法支持" in text:
        gates.append("legal_basis_review_present")
    if "正式流程已激活" in text or "已正式启动" in text:
        gates.append("case_opened")
    stage = "unknown"
    if "证据门禁" in text or "证据Gate" in text:
        stage = "evidence_gate_or_internal_analysis"
    if "巡视" in text:
        stage = "inspection_or_pre_delivery_review"
    status = "delivery_blocked" if not deliverable_allowed else "delivery_possible"
    if any("hold" in g.lower() for g in gates):
        status = "hold"
    return stage, status, deliverable_allowed, tuple(dict.fromkeys(gates)), tuple(dict.fromkeys(issues))


def discover_case_experiences(case_root: str | Path = DEFAULT_CASE_ROOT) -> list[CaseExperience]:
    root = Path(case_root)
    if not root.exists():
        return []
    experiences: list[CaseExperience] = []
    for case_dir in sorted([p for p in root.iterdir() if p.is_dir()]):
        report = _first_existing([
            case_dir / "11_生成文书" / "内部办案流程报告.md",
            case_dir / "12_内部报告" / "内部办案报告.md",
            case_dir / "内部办案报告.md",
        ])
        if report is None:
            continue
        text = _read_text(report)
        case_id = _extract_case_id(case_dir.name, text)
        case_name = _extract_case_name(text, case_id, case_dir.name)
        stage, status, deliverable_allowed, gates, issues = _detect_stage_status(text)
        evidence_hash = evidence_hash_from_text("\n".join([case_id, case_name, stage, status, "|".join(gates), "|".join(issues)]))
        experiences.append(CaseExperience(case_id, case_name, str(case_dir), stage, status, str(report), deliverable_allowed, gates, issues, evidence_hash))
    return experiences


def _failure_payloads_for_case(case: CaseExperience) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    base = f"{case.case_id}:{case.evidence_hash}"
    if "case_number_boundary_violation" in case.issues:
        payloads.append({
            "error_type": "case_number_boundary_violation",
            "trigger_scenario": "中枢预设或误用正式案号，未先由案件管理中心编号建档",
            "root_cause": "编号权边界执行不稳",
            "correct_action": "正式办案必须先由案件管理中心生成 PGG 编号，中枢只申请和核验",
            "auto_detection_rule": "detect_case_number_without_case_management_record",
            "next_intercept_method": "pre_case_opening_guard:block_non_case_management_case_id",
            "evidence": base + ":case_number",
        })
    if "department_timeout_or_exception" in case.issues:
        payloads.append({
            "error_type": "department_call_exception",
            "trigger_scenario": "部门调用超时或异常后由中枢补救",
            "root_cause": "部门调度鲁棒性不足，容易把补救稿误认为部门真实完成",
            "correct_action": "标注流程异常，区分真实部门回收与中枢补救稿",
            "auto_detection_rule": "detect_department_timeout_without_exception_label",
            "next_intercept_method": "pre_delivery_guard:require_department_call_status",
            "evidence": base + ":department_exception",
        })
    if "amount_closure_required" in case.issues:
        payloads.append({
            "error_type": "amount_not_closed_before_document",
            "trigger_scenario": "金额多版本或差额未解释时推进文书",
            "root_cause": "金额闭合门禁未前置",
            "correct_action": "强制列明总额、已付、扣减、待付、差额来源，不闭合则 HOLD",
            "auto_detection_rule": "detect_multiple_amount_versions_without_delta_explanation",
            "next_intercept_method": "pre_document_guard:amount_closure_required",
            "evidence": base + ":amount",
        })
    if "evidence_gate_hold" in case.issues:
        payloads.append({
            "error_type": "evidence_gate_hold_delivery_block",
            "trigger_scenario": "关键证据原件未核验时不能对外交付",
            "root_cause": "证据链不完整，法律判断只能内部预分析",
            "correct_action": "标注证据 Gate Hold，生成内部报告，等待 P0 证据补齐",
            "auto_detection_rule": "detect_final_delivery_claim_with_evidence_gate_hold",
            "next_intercept_method": "pre_delivery_guard:block_external_delivery_until_evidence_gate_pass",
            "evidence": base + ":evidence_hold",
        })
    if "legal_case_research_pending" in case.issues:
        payloads.append({
            "error_type": "case_law_not_verified",
            "trigger_scenario": "类案未实检时不得引用具体案例号",
            "root_cause": "法律依据与类案检索未完成正式核验",
            "correct_action": "仅标注初核方向，正式引用前由律法支持部实检",
            "auto_detection_rule": "detect_case_citation_without_verified_source",
            "next_intercept_method": "legal_basis_guard:require_verified_case_source",
            "evidence": base + ":case_law",
        })
    if case.status in {"hold", "delivery_blocked"} and "internal_report_generated" not in case.gates:
        payloads.append({
            "error_type": "missing_internal_report_when_delivery_blocked",
            "trigger_scenario": "不能对外交付但未生成内部办案报告",
            "root_cause": "交付闭环规则未自动触发",
            "correct_action": "不能对外交付时必须生成内部报告并同步桌面最终版",
            "auto_detection_rule": "detect_delivery_blocked_without_internal_report",
            "next_intercept_method": "case_close_guard:internal_report_required",
            "evidence": base + ":internal_report",
        })
    return payloads


def _retrospective_for_case(case: CaseExperience) -> dict[str, Any]:
    if "case_number_boundary_violation" in case.issues:
        why = "中枢越权预设正式案号，案件管理中心编号权没有前置。"
        next_change = "正式案号必须先通过案件管理中心，非 PGG 编号只能作为临时过程号。"
    elif "department_timeout_or_exception" in case.issues:
        why = "启动办案程序被降级或部门调度异常后需要补救，说明流程触发与回收门禁不够硬。"
        next_change = "用户说启动办案程序即自动触发案件管理中心编号和部门并行，并记录每个部门真实回收状态。"
    elif "amount_closure_required" in case.issues:
        why = "金额版本存在差异，金额闭合核算没有在文书前强制执行。"
        next_change = "金额类案件先通过总额、已付、扣减、待付、差额来源表，未闭合不得进入正式函件。"
    else:
        why = "真实案件进入了证据门禁，但自动进化事件桥尚未接入。"
        next_change = "将案卷门禁、内部报告、补证清单转为 PGG Archon 只读事件。"
    return {
        "task_id": case.case_id,
        "what_happened": f"案件 {case.case_id} 已形成内部报告，当前状态为 {case.status}，门禁包括 {', '.join(case.gates) or 'unknown'}。",
        "why": why,
        "next_change": next_change,
        "evidence_hash": case.evidence_hash,
    }


def run_case_experience_bridge(*, case_root: str | Path = DEFAULT_CASE_ROOT, events_dir: str | Path = DEFAULT_EVENTS_DIR, write_ledgers: bool = True) -> dict[str, Any]:
    cases = discover_case_experiences(case_root)
    events = [case.to_event() for case in cases]
    target_dir = Path(events_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    events_path = target_dir / "case_events.jsonl"
    summary_path = target_dir / "summary.json"
    with events_path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    failure_appends = []
    retrospective_appends = []
    if write_ledgers:
        existing_failure_hashes = {s.get("evidence_hash") for s in load_failure_samples()}
        for case in cases:
            for payload in _failure_payloads_for_case(case):
                sample_hash = evidence_hash_from_text(str(payload.get("evidence") or payload))
                if sample_hash in existing_failure_hashes:
                    continue
                payload = {**payload, "evidence_hash": sample_hash}
                failure_appends.append(append_failure_sample(payload))
                existing_failure_hashes.add(sample_hash)
            retrospective_appends.append(append_task_retrospective(_retrospective_for_case(case)))
    summary = {
        "schema": "PGGCaseExperienceBridgeSummary/v1",
        "status": "PASS" if cases else "UNKNOWN",
        "case_count": len(cases),
        "event_count": len(events),
        "failure_appended_count": len(failure_appends),
        "retrospective_appended_count": len(retrospective_appends),
        "events_path": str(events_path),
        "summary_path": str(summary_path),
        "side_effects": "writes_sanitized_evidence_ledgers_only",
        "cases": [{"case_id": c.case_id, "status": c.status, "issues": list(c.issues), "evidence_hash": c.evidence_hash} for c in cases],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


__all__ = [
    "CaseExperience",
    "discover_case_experiences",
    "run_case_experience_bridge",
]
