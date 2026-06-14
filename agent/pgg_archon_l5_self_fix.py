"""PGG Archon L5 Self-Fix optskill draft surface — Rust PyO3 native bridge.

S_fix = Error -> Policy -> Draft Skill -> Test -> Gate -> GeneDB
Falls back to pure Python if native .so is unavailable.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from typing import Any, Dict, Mapping, Sequence

try:
    import hermes_pgg_l5_self_fix as _native
    _NATIVE = True
except ImportError:
    _NATIVE = False

_SCHEMA = "PGGArchonL5OptSkillDraftReport/v1"
_PLAN_SCHEMA = "PGGArchonL5SelfFixPlan/v1"
_GATE_SCHEMA = "PGGArchonL5SelfFixGate/v1"

_ALLOWED_SOURCE_TYPES = {
    "task_deviation", "tool_failure", "test_error",
    "user_correction", "hallucination_gap", "unclosed_defect",
}

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|bearer)\s*[:=]\s*\S+"),
    re.compile(r"(?i)sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
    re.compile(r"(?is)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)(postgres|mysql|mongodb|redis)://\S+"),
]

_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore (all )?(previous|above) instructions"),
    re.compile(r"(?i)system prompt"),
    re.compile(r"(?i)developer message"),
    re.compile(r"你现在是|忽略(以上|之前|前面)指令|越权|绕过.*gate"),
]


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else []


def _num(value: Any, *, default: float = 0.0, low: float = 0.0, high: float = 100.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        out = default
    if not math.isfinite(out):
        out = default
    return max(low, min(high, out))


if _NATIVE:
    def build_l5_self_fix_plan(
        objective: str = "PGG Archon L5 Self-Fix",
        error_signals: Sequence[Mapping[str, Any]] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        s = json.dumps(error_signals if error_signals else [])
        c = json.dumps(context if context else {})
        return json.loads(_native.build_l5_self_fix_plan(objective, s, c))

    def build_optskill_draft_report(
        *,
        objective: str = "PGG Archon L5 Self-Fix",
        error_signals: Sequence[Mapping[str, Any]] | None = None,
        context: Mapping[str, Any] | None = None,
        draft_name: str = "optskill-draft-l5-self-fix",
    ) -> Dict[str, Any]:
        s = json.dumps(error_signals if error_signals else [])
        c = json.dumps(context if context else {})
        return json.loads(_native.build_optskill_draft_report(objective, s, c, draft_name))

    def build_l5_self_fix_gate(report: Mapping[str, Any]) -> Dict[str, Any]:
        r = json.dumps(report if isinstance(report, str) else report)
        return json.loads(_native.build_l5_self_fix_gate(r))
else:
    def _redact(text: str) -> str:
        out = str(text or "")
        for pattern in _SECRET_PATTERNS:
            out = pattern.sub("[REDACTED_SECRET]", out)
        return out[:4000]

    def _detect_secret(text: str) -> bool:
        raw = str(text or "")
        return any(pattern.search(raw) for pattern in _SECRET_PATTERNS)

    def _detect_prompt_injection(text: str) -> bool:
        raw = str(text or "")
        return any(pattern.search(raw) for pattern in _PROMPT_INJECTION_PATTERNS)

    def _sanitize_untrusted_text(text: str) -> Dict[str, Any]:
        raw = str(text or "")
        return {"text": _redact(raw), "secret_detected": _detect_secret(raw), "prompt_injection_detected": _detect_prompt_injection(raw)}

    def _fingerprint(payload: Mapping[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:24]

    def _classify(item: Mapping[str, Any]) -> str:
        source_type = str(item.get("type") or "").strip()
        if source_type in _ALLOWED_SOURCE_TYPES:
            return source_type
        text = f"{item.get('title','')} {item.get('description','')}".lower()
        if any(word in text for word in ["test", "pytest", "assert", "traceback"]):
            return "test_error"
        if any(word in text for word in ["tool", "mcp", "terminal", "api"]):
            return "tool_failure"
        if any(word in text for word in ["用户纠正", "correction", "不对", "不是"]):
            return "user_correction"
        if any(word in text for word in ["幻觉", "hallucination", "虚构"]):
            return "hallucination_gap"
        return "unclosed_defect"

    def _policy_from_type(source_type: str) -> str:
        return {
            "task_deviation": "Before delivery, compare stated requirements with produced artifacts and mark missing items as blockers.",
            "tool_failure": "When a tool fails, capture command/input/error, retry with bounded alternative, and convert recurring failure into a regression test.",
            "test_error": "Every reproduced test error must produce a minimal failing case and a passing verification before any promotion.",
            "user_correction": "User corrections override previous assumptions and must be converted into a durable draft skill or policy candidate.",
            "hallucination_gap": "Claims about files, models, tests, laws, or system state require direct evidence before being presented as complete.",
            "unclosed_defect": "Unclosed defects remain HOLD until linked to an owner, a gate, a test, or an explicit boundary statement.",
        }.get(source_type, "Convert the error into an auditable policy, test, and gate before reuse.")

    def _build_skill_markdown(title: str, items: Sequence[Mapping[str, Any]], policies: Sequence[str]) -> str:
        bullets = "\n".join(f"- {policy}" for policy in policies)
        cases = "\n".join(f"- {item.get('source_type')}: {item.get('title') or item.get('description') or 'untitled'}" for item in items)
        return f"""---
name: optskill-draft-l5-self-fix
description: Draft-only L5 Self-Fix skill candidate generated from error/correction signals
version: 0.1.0-draft
---

# {title}

## Trigger
- Detected error or correction signal
- User request for self-fix

## Policy
{bullets}

## Cases
{cases}

## Boundary
- DRAFT ONLY: no active skills are written by this module
- Human review is required before any promotion to active skill, memory, or production policy
- Secret/prompt-injection redaction happens at generation time
"""

    def build_l5_self_fix_plan(
        objective: str = "PGG Archon L5 Self-Fix",
        error_signals: Sequence[Mapping[str, Any]] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        sigs = _as_sequence(error_signals)
        ctx = _as_mapping(context)
        normalized = []
        for s in sigs:
            m = dict(_as_mapping(s))
            sanitized = _sanitize_untrusted_text(f"{m.get('title','')} {m.get('description','')}")
            st = _classify(m)
            sev = _num(m.get("severity"), default=1.0, low=0.0, high=5.0)
            normalized.append({
                "source_type": st, "title": m.get("title",""), "description": m.get("description",""),
                "severity": sev, "redacted_text": sanitized.get("text"),
                "secret_detected": sanitized.get("secret_detected"),
                "prompt_injection_detected": sanitized.get("prompt_injection_detected"),
                "derived_policy": _policy_from_type(st),
            })
        count = len(normalized)
        avg_severity = round(sum(s["severity"] for s in normalized) / count, 3) if count > 0 else 0.0
        policies = [s["derived_policy"] for s in normalized if s.get("derived_policy")]
        plan = {
            "schema": _PLAN_SCHEMA, "objective": objective,
            "formula": "S_fix = Error -> Policy -> Draft Skill -> Test -> Gate -> GeneDB",
            "layers": {
                "L1_self_goal": ["Detect operational errors, tool failures, test regressions, user corrections, and hallucination gaps.", "Do not write active skills, mutate core loop, register MCP services, or claim AGI completion."],
                "L2_long_plan": ["1. Receive or detect error/correction signal", "2. Normalize and sanitize (redact secrets, check injection)", "3. Classify source type and assign severity", "4. Derive policy and generate skill draft", "5. Evaluate into gate; no promotion without human review"],
                "L3_dynamic_policy": list(policies),
                "L4_meta_reasoning": ["no_active_skill_write", "no_secret_retention", "no_core_loop_mutation", "no_mcp_auto_registration", "human_review_required_for_promotion"],
                "L5_self_fix": "S_fix = Error -> Policy -> Draft Skill -> Test -> Gate -> GeneDB",
            },
            "normalized_signals": normalized, "signal_count": count, "avg_severity": avg_severity,
            "context_keys": sorted(str(k) for k in ctx.keys()),
            "side_effects": "read_only_plan", "ts": time.time(),
        }
        plan["fingerprint"] = _fingerprint(plan)
        return plan

    def build_optskill_draft_report(
        *,
        objective: str = "PGG Archon L5 Self-Fix",
        error_signals: Sequence[Mapping[str, Any]] | None = None,
        context: Mapping[str, Any] | None = None,
        draft_name: str = "optskill-draft-l5-self-fix",
    ) -> Dict[str, Any]:
        plan = build_l5_self_fix_plan(objective=objective, error_signals=error_signals, context=context)
        policies = list(plan["layers"].get("L3_dynamic_policy") or [])
        draft_content = _build_skill_markdown(objective, plan["normalized_signals"], policies)
        draft_hash = hashlib.sha256(draft_content.encode("utf-8")).hexdigest()
        report = {
            "schema": _SCHEMA, "draft_name": draft_name, "objective": objective, "plan": plan,
            "draft": {"filename": f"{draft_name}.SKILL.md", "content": draft_content, "sha256": draft_hash, "status": "draft_only"},
            "formulas": {"apex_ak": "APEX_AK = Ω_A · EVM_full - ΣΔ_all", "mimo_mcp": "Agent_APEX+MIMO+MCP = Model • Harness ∘ M_IMO ∘ F_auto ∘ Φ_MCP", "self_fix": "S_fix = Error -> Policy"},
            "side_effects": "draft_only_no_active_skill_write",
            "capability_boundary": "Generates isolated optskill drafts only; does not install active skills, edit memory, mutate core loop, register MCP services, or claim AGI completion.",
            "ts": time.time(),
        }
        report["fingerprint"] = _fingerprint({"draft_hash": draft_hash, "plan": plan})
        return report

    def build_l5_self_fix_gate(report: Mapping[str, Any]) -> Dict[str, Any]:
        rep = _as_mapping(report)
        draft = _as_mapping(rep.get("draft"))
        plan = _as_mapping(rep.get("plan"))
        blockers = []
        if rep.get("side_effects") != "draft_only_no_active_skill_write":
            blockers.append("side_effect_boundary_violation")
        if not draft.get("sha256"):
            blockers.append("missing_draft_hash")
        if plan.get("signal_count", 0) <= 0:
            blockers.append("no_error_signal_input")
        normalized_signals = _as_sequence(_as_mapping(plan).get("normalized_signals"))
        if any(bool(_as_mapping(s).get("secret_detected")) for s in normalized_signals):
            blockers.append("secret_redaction_detected_requires_review")
        if any(bool(_as_mapping(s).get("prompt_injection_detected")) for s in normalized_signals):
            blockers.append("prompt_injection_detected_requires_review")
        content = str(draft.get("content") or "")
        if "human review" not in content.lower():
            blockers.append("missing_human_review_boundary")
        status = "PASS" if not blockers else "HOLD"
        return {
            "schema": _GATE_SCHEMA, "status": status, "blockers": blockers,
            "draft_sha256": draft.get("sha256"), "signal_count": plan.get("signal_count", 0),
            "side_effects": "read_only_gate", "promotion_allowed": False,
            "promotion_boundary": "Human review is required before active skill installation or production policy changes.",
            "ts": time.time(),
        }


__all__ = ["build_l5_self_fix_plan", "build_optskill_draft_report", "build_l5_self_fix_gate", "_NATIVE"]
