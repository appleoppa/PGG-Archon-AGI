"""PGG Archon / Apple Didi formula gate status panel.

This module turns the user's /goal rule into a deterministic, readable status
panel for important AGI/evolution/system tasks. It is intentionally read-only:
no provider calls, no network, no config writes, no scheduler/security boundary
mutation.

Boundary: a PASS/WATCH status here means the pre-task formula gate is explicit
and evidence-aware. It does not prove T5, full AGI, official benchmark success,
production routing performance, or legal correctness.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

SIX_DIMENSIONS = [
    "基础认知能力",
    "跨域通用适配能力",
    "自主智能体行动能力",
    "自主知识进化系统",
    "对齐、安全与价值理性",
    "现实环境落地性能",
]

EVOLVE_CHAIN = ["LDR(K)", "GapDetect", "CodeSelfFix", "HotReload", "TaskSolve", "KnowledgeSettle"]

TRUTHFUL_BOUNDARY = (
    "Formula gate panel only: makes the AGI/evolution working rule explicit and evidence-aware. "
    "Not T5 proof, not full AGI, not official external benchmark, not legal correctness, "
    "and not production takeover evidence."
)

GOAL_FORMULA_RULE = {
    "source": "/goal",
    "north_star": "总纲1：AGI L0-L5 六维评估框架",
    "execution_chain": "总纲2：Agent_Evolve = LDR(K) → GapDetect → CodeSelfFix → HotReload → TaskSolve → KnowledgeSettle",
    "target": "持续逼近 T5/L5，但每轮只声明已验证工程门禁；不得把内部状态冒充 T5/full AGI",
    "truth_boundary": TRUTHFUL_BOUNDARY,
}

TASK_DIMENSION_HINTS = {
    "evolution": ["基础认知能力", "自主知识进化系统", "对齐、安全与价值理性", "现实环境落地性能"],
    "agi": ["基础认知能力", "跨域通用适配能力", "自主智能体行动能力", "自主知识进化系统", "对齐、安全与价值理性", "现实环境落地性能"],
    "system": ["自主智能体行动能力", "对齐、安全与价值理性", "现实环境落地性能"],
    "legal": ["基础认知能力", "跨域通用适配能力", "对齐、安全与价值理性", "现实环境落地性能"],
    "coding": ["自主智能体行动能力", "现实环境落地性能", "对齐、安全与价值理性"],
    "general": ["基础认知能力", "对齐、安全与价值理性"],
}

@dataclass(frozen=True)
class FormulaGateDimension:
    name: str
    active: bool
    check: str


def _load_manifest_summary(manifest_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(manifest_path).expanduser() if manifest_path else Path.home() / ".hermes" / "data" / "EVOLUTION_MANIFEST.json"
    if not path.exists():
        return {"present": False, "path": str(path), "latest_pass_keys": [], "latest_keys": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"present": True, "path": str(path), "error": repr(exc), "latest_pass_keys": [], "latest_keys": []}
    def sort_key(item: tuple[str, Any]) -> tuple[str, str]:
        key, value = item
        if isinstance(value, dict):
            stamp = str(value.get("created_at") or value.get("generated_at") or value.get("timestamp") or "")
        else:
            stamp = ""
        return (stamp, key)

    latest_items = sorted(((k, v) for k, v in data.items() if k.startswith("latest_")), key=sort_key)[-12:]
    latest_keys = [k for k, _ in latest_items]
    def status_family(value: Any) -> str:
        status = str(value.get("status") or "") if isinstance(value, dict) else ""
        if status == "PASS":
            return "PASS"
        if status.startswith("PASS_"):
            return "PASS_FAMILY"
        if status.startswith("WATCH"):
            return "WATCH"
        if status.startswith("PARTIAL"):
            return "PARTIAL"
        if status.startswith("BLOCK") or status.startswith("FAIL") or status.startswith("ERROR"):
            return "BLOCK_OR_ERROR"
        return "UNKNOWN"

    latest_pass_keys = [k for k, v in latest_items if status_family(v) in {"PASS", "PASS_FAMILY"}]
    latest_exact_pass_keys = [k for k, v in latest_items if status_family(v) == "PASS"]
    status_counts: dict[str, int] = {}
    for _, v in latest_items:
        fam = status_family(v)
        status_counts[fam] = status_counts.get(fam, 0) + 1
    return {
        "present": True,
        "path": str(path),
        "latest_keys": latest_keys,
        "latest_pass_keys": latest_pass_keys,
        "latest_exact_pass_keys": latest_exact_pass_keys,
        "latest_pass_count": len(latest_pass_keys),
        "latest_exact_pass_count": len(latest_exact_pass_keys),
        "latest_status_counts": status_counts,
        "sort": "created_at/generated_at/timestamp fallback key",
    }


def classify_task_type(task: str = "") -> str:
    text = (task or "").lower()
    if any(k in text for k in ["agi", "pgg", "archon", "t5", "总纲", "进化", "evolution", "apex"]):
        return "agi" if any(k in text for k in ["agi", "t5", "总纲"]) else "evolution"
    if any(k in text for k in ["法律", "办案", "legal", "诉讼", "合同", "法院"]):
        return "legal"
    if any(k in text for k in ["系统", "runtime", "web", "router", "hermes", "配置", "服务"]):
        return "system"
    if any(k in text for k in ["代码", "rust", "python", "测试", "commit", "编译"]):
        return "coding"
    return "general"


def build_formula_gate_status(
    task: str,
    *,
    target_tier: str = "T4-oriented engineering formula gate; not T5 proof",
    manifest_path: str | Path | None = None,
    explicit: bool = True,
) -> dict[str, Any]:
    """Build a human-readable /goal formula gate status for a task.

    The output is meant to be shown before important work and read back after
    verification. It binds 总纲1 six-dimensional AGI evaluation with 总纲2
    Agent_Evolve stages, while preserving truthful boundaries.
    """
    task_type = classify_task_type(task)
    active_dims = set(TASK_DIMENSION_HINTS.get(task_type, TASK_DIMENSION_HINTS["general"]))
    dimensions = [
        FormulaGateDimension(
            name=name,
            active=name in active_dims,
            check=("本轮显式纳入" if name in active_dims else "本轮轻量观察"),
        )
        for name in SIX_DIMENSIONS
    ]
    manifest = _load_manifest_summary(manifest_path)
    chain = [
        {"stage": "LDR(K)", "check": "读取任务、记忆/技能、Manifest 或相关代码证据"},
        {"stage": "GapDetect", "check": "列出短板、风险、overclaim/安全边界"},
        {"stage": "CodeSelfFix", "check": "若有低风险可回滚缺口，执行补丁/配置/流程修复"},
        {"stage": "HotReload", "check": "运行测试、smoke、读回或服务/状态验证"},
        {"stage": "TaskSolve", "check": "交付用户真实目标，不以文件存在冒充完成"},
        {"stage": "KnowledgeSettle", "check": "必要时写入 Manifest / memory / skill / reference，并读回"},
    ]
    evidence_gates = {
        "manifest_present": bool(manifest.get("present")),
        "latest_pass_count": manifest.get("latest_pass_count", 0),
        "latest_exact_pass_count": manifest.get("latest_exact_pass_count", 0),
        "explicit_formula_gate": explicit,
        "truth_boundary_present": True,
    }
    missing = [k for k, v in evidence_gates.items() if not v]
    status = "PASS" if explicit and manifest.get("present") and not missing else "WATCH"
    if not task.strip():
        status = "WATCH"
        missing.append("task_description")
    return {
        "schema": "PGGArchonFormulaGateStatus/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": task,
        "task_type": task_type,
        "status": status,
        "target_tier": target_tier,
        "goal_formula_rule": GOAL_FORMULA_RULE,
        "six_dimensions": [asdict(d) for d in dimensions],
        "agent_evolve_chain": chain,
        "evidence_gates": evidence_gates,
        "missing_gates": sorted(set(missing)),
        "manifest_summary": manifest,
        "defect_reduction_focus": [
            "减少公式不可见导致的用户感知失败",
            "减少过度宣称：T5/full AGI/官方评测/法律正确性",
            "减少未验证即完成、文件存在冒充能力、provider 角色混淆",
        ],
        "report_template": {
            "pre_task": "【公式门禁】总纲1六维映射 + 总纲2闭环阶段 + T目标 + 真实性边界",
            "post_task": "【闭环复盘】LDR / GapDetect / Fix / Verify / TaskSolve / KnowledgeSettle / -ΣΔ_all",
        },
        "boundary": TRUTHFUL_BOUNDARY,
    }


def render_formula_gate_status(status: dict[str, Any]) -> str:
    active = [d["name"] for d in status.get("six_dimensions", []) if d.get("active")]
    chain = " → ".join(stage["stage"] for stage in status.get("agent_evolve_chain", []))
    missing = status.get("missing_gates") or []
    goal = status.get("goal_formula_rule") or {}
    return "\n".join([
        "【公式门禁状态】",
        f"/goal：{goal.get('north_star', '总纲1')}；{goal.get('execution_chain', '总纲2')}",
        f"状态：{status.get('status')} | 任务类型：{status.get('task_type')} | 目标：{status.get('target_tier')}",
        f"总纲1六维：{', '.join(active) if active else '未激活'}",
        f"总纲2闭环：{chain}",
        f"证据：Manifest={'有' if status.get('evidence_gates', {}).get('manifest_present') else '缺'}；latest PASS族={status.get('evidence_gates', {}).get('latest_pass_count', 0)}；exact PASS={status.get('evidence_gates', {}).get('latest_exact_pass_count', 0)}；缺口={missing or '无'}",
        f"边界：{status.get('boundary')}",
    ])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("task", nargs="*", default=["general"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    panel = build_formula_gate_status(" ".join(args.task))
    if args.json:
        print(json.dumps(panel, ensure_ascii=False, indent=2))
    else:
        print(render_formula_gate_status(panel))
