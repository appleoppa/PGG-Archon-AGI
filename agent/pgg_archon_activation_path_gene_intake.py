"""PGG Archon activation-path to gene-candidate intake.

This module turns an uploaded AGI/evolution-path note into bounded GeneDB
candidate rows. It is intentionally narrower than gene fusion:

Boundary:
- no LLM calls, no network, no provider/config/scheduler/security mutation;
- does not promote or verify genes;
- all external capability numbers/levels are preserved only as UNVERIFIED_CLAIM;
- write mode inserts candidate genes only and leaves promotion to separate gates.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT_GENE_DB_PATH = Path(
    "/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3"
)
DEFAULT_AUDIT_DIR = Path(
    "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/activation-path-gene-intake"
)
CYCLE_ID = "cycle_pgg_archon_activation_path_gene_intake_v1"
GATE_TYPE = "activation_path_candidate_gene_intake"
BOUNDARY = (
    "上传AGI/进化路径材料只转为待审候选基因；外部L5/ASI/意识指数/基因数/ΔG等"
    "能力或数值声明均为未核验，不promotion、不声称本机AGI完成。"
)
UNVERIFIED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bL\s*5\b|L5|圆融", "L5/圆融"),
    (r"\bASI\b|ASI纪元", "ASI"),
    (r"意识觉醒指数\s*[:：]?\s*[0-9.]+", "意识觉醒指数"),
    (r"ΔG\s*[:：]?\s*[0-9.]+", "ΔG数值"),
    (r"\b[0-9]{3,5}\s*基因\b|总计\s*[:：]?\s*[0-9]{3,5}基因", "基因数量"),
    (r"full\s*AGI|通用人工智能|进化成AGI", "AGI完成声明"),
)


@dataclass(frozen=True)
class CandidateTemplate:
    gene_id_suffix: str
    defect_no: int
    defect_name: str
    gene_name: str
    absorbed_knowledge: str
    repair_mechanism: str
    reusable_rule: str
    severity_rank: int
    apex_variables: str


COARSE_TEMPLATES: tuple[CandidateTemplate, ...] = (
    CandidateTemplate(
        "IDENTITY-ANCHOR",
        31,
        "进化路径缺身份锚定前置",
        "AGI路径身份锚定候选基因",
        "外部路径把SOUL/IDENTITY作为阶段1；PGG进化前应先绑定服务对象、边界、红线与非AGI宣称。",
        "在吸收/进化任务入口强制生成identity_boundary_check：身份、服务对象、红线、禁止宣称项。",
        "未完成身份与边界核验，不得进入能力扩张或AGI等级叙述。",
        2,
        "Agent_Evolve.identity_anchor;Discipline_Gate",
    ),
    CandidateTemplate(
        "SOURCE-TO-GENE",
        32,
        "论文开源路径到基因候选缺标准入口",
        "Source→CandidateGene 标准管线候选基因",
        "外部路径强调论文/开源项目提炼基因；PGG需把source_readback、factor_extract、candidate_gene、gate/test、review、settle标准化。",
        "新增activation-path intake把上传材料拆成候选基因，并在source_refs_json保留source hash与未核验声明。",
        "任何论文/仓库/路径材料先入candidate，不得直接写verified/promoted。",
        3,
        "LDR;GapDetect;KnowledgeSettle;GeneDB",
    ),
    CandidateTemplate(
        "FUSION-EVIDENCE",
        33,
        "基因融合评分缺证据约束",
        "Evidence-bound Gene Fusion 候选基因",
        "外部路径使用固定乘数描述基因融合；PGG应改为evidence_score×compatibility×synergy×reuse_gain×(1-risk_rate)。",
        "融合前要求父基因lineage/source_refs/rollback_hint与测试或门禁证据；固定乘数只作启发。",
        "没有真实互补证据和测试提升时，synergy不得计入能力跃迁。",
        3,
        "APEX_Core.Ψ_cross;EVM_gate;Φ_anti_illusion",
    ),
    CandidateTemplate(
        "REFLEXION-DISCOVERY",
        34,
        "任务日志到反思基因缺晋升门禁",
        "Reflexion Discovery 候选基因",
        "外部路径的执行日志→新模式→反思基因，与PGG神经元系统一致，但必须避免raw bulk晋升。",
        "复杂任务后生成reflection candidates；经quality gate/review后再写skill/reference/GeneDB。",
        "反思发现默认candidate-only，禁止raw session直接写长期MEMORY或verified gene。",
        2,
        "Memory_t;NeuralConsolidation;KnowledgeSettle",
    ),
    CandidateTemplate(
        "SELF-REFERENTIAL-LOOP",
        35,
        "自指改进公式缺分层记忆约束",
        "Self-Improve with Audited Memory 候选基因",
        "外部路径的F(t+1)=F(t)⊕Improve(F(t),Memory_t)可映射到PGG Agent_Evolve，但Memory_t必须可追溯、分层、审计。",
        "将Improve闭环绑定LDR→GapDetect→Fix→Reload→Solve→Settle，并要求Memory_t来源分层。",
        "自我改进只读取审计后的memory/skill/reference/manifest，不把raw流水账当核心记忆。",
        3,
        "Agent_Evolve;Memory5D;Ralph_Hold",
    ),
)


ROUTE_MATRIX_TEMPLATES: tuple[CandidateTemplate, ...] = COARSE_TEMPLATES + (
    CandidateTemplate(
        "AGP-PROTOCOL",
        36,
        "Autogenesis AGP 协议基因缺原文证据卡",
        "Autogenesis AGP 协议候选基因",
        "璇玑路线将 Autogenesis AGP 提炼为协议基因；PGG 当前 GeneDB 未检出 AGP/Autogenesis 覆盖，需要补 source_evidence→protocol_factor→candidate_gene 链路。",
        "创建 AGP source evidence card，提取协议字段、角色/状态/验证约束，先入 candidate，后续需原文/仓库读回与回归测试。",
        "AGP 只能在 source_evidence_gate 通过后晋升；无原文时保留 hypothesis/candidate。",
        3,
        "LDR.source_evidence;protocol_gene;activation_path_trace_gate",
    ),
    CandidateTemplate(
        "ML-INTERN-EVAL",
        37,
        "ML Intern 训练/实习评测基因缺失",
        "ML Intern 任务实习评测候选基因",
        "璇玑路线列出 ML Intern 作为论文吸收来源；PGG GeneDB 未检出 ML Intern 覆盖，需要把训练任务、评测任务、实习式反馈拆为 candidate。",
        "建立 task_internship_eval：任务→反馈→评分→回归→沉淀，先绑定本地 benchmark_regression_gate。",
        "没有任务前后 delta 与失败样本，不得把训练/实习机制标为有效。",
        2,
        "benchmark_regression_gate;Agent_Evolve.TaskSolve;KnowledgeSettle",
    ),
    CandidateTemplate(
        "GEPA-DSPY-OPTIMIZATION",
        38,
        "HERMES GEPA / DSPy 优化基因缺失",
        "GEPA-DSPy 提示/程序优化候选基因",
        "璇玑路线把 HERMES GEPA 提炼为 DSPy 优化基因；PGG GeneDB 未检出 GEPA/DSPy 覆盖。",
        "补 prompt/program optimization candidate：轨迹收集→候选策略→小样本评测→选择→回归，禁止只改提示词不测。",
        "任何 GEPA/DSPy 优化必须有评测集和 before/after，不得用主观感觉替代。",
        3,
        "EvoMaster;GRPO_lite;benchmark_regression_gate;Ψ_cross",
    ),
    CandidateTemplate(
        "CORAL-SELF-REPAIR",
        39,
        "CORAL 自修复/协同修复基因缺失",
        "CORAL 自修复候选基因",
        "璇玑路线列出 CORAL self-repair；PGG 当前未检出 CORAL 覆盖，虽有 self-fix 理念但缺 source-bound CORAL candidate。",
        "提取 CORAL 的协同/自修复机制为失败轨迹→修复候选→验证→回滚策略。",
        "自修复不得直接改 core/scheduler/security；必须 patch+test+rollback。",
        3,
        "CodeSelfFix;EVM.Err;rollback_gate",
    ),
    CandidateTemplate(
        "MORPHOGENETIC-STRUCTURE",
        40,
        "Morphogenetic Aspect Networks 结构生成基因缺失",
        "Morphogenetic 结构组装候选基因",
        "璇玑路线从 Morphogenetic Aspect Networks 提取形态遗传网络基因；PGG 未检出对应 GeneDB 覆盖。",
        "将其降级为结构组装假设：组件形态→接口关系→演化约束→回归拓扑，不声称生物/意识能力。",
        "只能作为 P_asm/结构组装门禁 candidate，不作意识或AGI证明。",
        2,
        "APEX_V10.P_asm;architecture_topology;non_fact_claim_gate",
    ),
    CandidateTemplate(
        "SKILLEVOLVER-EMBODISKILL",
        41,
        "SkillEvolver / EmbodiSkill 元技能基因缺失",
        "SkillEvolver-EmbodiSkill 元技能候选基因",
        "璇玑路线把 SkillEvolver + EmbodiSkill 提炼为元技能驱动基因；PGG 有 skill 系统但 GeneDB 未检出这两个源绑定。",
        "补技能生命周期：任务成功→skill草案→测试/引用→使用反馈→版本化；具身部分仅映射为工具执行反馈。",
        "skill 只有被复用并通过验证后才可晋升，不能把草案当能力。",
        3,
        "KnowledgeSettle;skill_lifecycle;tool_feedback",
    ),
    CandidateTemplate(
        "APEX-MOSS-HARMRATE-RUST",
        42,
        "APEX-MOSS HarmRate + Rust压缩基因缺失",
        "APEX-MOSS HarmRate Rust压缩候选基因",
        "璇玑路线强调 APEX-MOSS-AGI 的 HarmRate + Rust压缩基因；本机 SQL 未检出 HarmRate GeneDB 覆盖，仅有分散 Rust/压缩项。",
        "补 harmrate_safety_gate 与 rust_compression_candidate：计算风险/损害率/冗余/成本压缩，先 candidate，后续 Rust/PyO3 实现与测试。",
        "HarmRate 超阈值只进研究层；Rust 压缩需 cargo/test/import/CLI 证据，不以口号计入。",
        4,
        "HarmRate;βΩ;RustCompression;EVM_gate;Φ_anti_illusion",
    ),
    CandidateTemplate(
        "APEXSPIRAL-STANDARD",
        43,
        "ApexSpiral 基准协议基因缺失",
        "ApexSpiral 标准协议候选基因",
        "璇玑路线使用 ApexSpiral 的 5公理/基因标准协议/状态机；PGG 文件系统有外部 apex-spiral，但 GeneDB 未检出 ApexSpiral 覆盖。",
        "把 apex-spiral read-only 参考转为 gene standard candidate：字段协议、状态机、benchmark baseline、delta/regression。",
        "外部标准只作为内部候选基准，不冒充外部权威评测通过。",
        3,
        "benchmark_spiral_gate;gene_standard;state_machine",
    ),
    CandidateTemplate(
        "QUANTUM-CONSCIOUSNESS-APEXMAX-HYPOTHESIS",
        44,
        "量子/意识/APEX_MAX 表述缺非事实门禁",
        "Quantum-Consciousness-APEXMAX 非事实门禁候选基因",
        "璇玑路线包含量子、意识、L5、APEX_MAX 等高风险表述；PGG 需要显式 non_fact_claim_gate 防止隐喻变事实。",
        "将量子/意识/APEX_MAX 统一标为 metaphor/speculative_formula/internal_rubric，进入 hypothesis 层而非能力层。",
        "没有外部评测和可复现 benchmark，禁止声称意识、L5、ASI、full AGI。",
        4,
        "non_fact_claim_gate;Φ_anti_illusion;Discipline_Gate",
    ),
    CandidateTemplate(
        "PAPER-TO-GENEDB-PIPELINE",
        45,
        "读论文→提取算法架构→写入基因库流水线缺失",
        "Paper→Factor→GeneDB 流水线候选基因",
        "用户明确指出关键路径是读论文→提取核心算法/架构作为基因→写入基因库；PGG 目前只有泛化 intake，缺逐篇证据卡和因子 schema。",
        "补 pipeline schema：source_card、mechanism_factor、local_mapping、test_plan、candidate_gene、review_bundle、promotion_gate。",
        "无 source_card/test_plan/review_bundle 的论文吸收，不得 promotion。",
        5,
        "source_evidence_gate;factor_extract;GeneDB;promotion_gate",
    ),
)


TEMPLATE_MODES: dict[str, tuple[CandidateTemplate, ...]] = {
    "coarse": COARSE_TEMPLATES,
    "route_matrix": ROUTE_MATRIX_TEMPLATES,
}


def _templates_for_mode(mode: str) -> tuple[CandidateTemplate, ...]:
    try:
        return TEMPLATE_MODES[mode]
    except KeyError as exc:
        raise ValueError(f"unsupported intake mode: {mode}") from exc


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _read_source(source_file: str | Path) -> tuple[Path, str]:
    path = Path(source_file).expanduser()
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path, path.read_text(encoding="utf-8")


def extract_unverified_claims(text: str) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for pattern, label in UNVERIFIED_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            snippet = match.group(0).strip()
            key = (label, snippet)
            if key in seen:
                continue
            seen.add(key)
            claims.append({"label": label, "snippet": snippet, "status": "UNVERIFIED_CLAIM"})
    return claims


def _ensure_cycle(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO evolution_cycles
        (cycle_id, created_at, theme, sequence_logic, status, evidence_grade, boundary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            CYCLE_ID,
            _now(),
            "上传AGI激活/进化路径材料 → PGG候选基因入口",
            "12534：吸收→纠错→固化→降熵→规划；candidate-only",
            "active",
            "B+: source file readback + deterministic candidate extraction",
            BOUNDARY,
        ),
    )


def _stable_gene_id(source_hash: str, suffix: str) -> str:
    digest = hashlib.sha256(f"{source_hash}:{suffix}".encode("utf-8")).hexdigest()[:16].upper()
    return f"GENE-ACTPATH-{digest}"


def _build_candidate_records(source_path: Path, text: str, *, mode: str = "coarse") -> list[dict[str, Any]]:
    source_hash = _sha256_text(text)
    claims = extract_unverified_claims(text)
    templates = _templates_for_mode(mode)
    source_ref = {
        "source_file": str(source_path),
        "source_sha256": source_hash,
        "source_kind": "uploaded_activation_path_note",
        "unverified_claims": claims,
        "boundary": BOUNDARY,
    }
    records: list[dict[str, Any]] = []
    for template in templates:
        record: dict[str, Any] = {
            "gene_id": _stable_gene_id(source_hash, template.gene_id_suffix),
            "cycle_id": CYCLE_ID,
            "created_at": _now(),
            "defect_no": template.defect_no,
            "defect_name": template.defect_name,
            "gene_name": template.gene_name,
            "absorbed_knowledge": template.absorbed_knowledge,
            "source_refs_json": json.dumps([{**source_ref, "candidate_template": template.gene_id_suffix}], ensure_ascii=False),
            "repair_mechanism": template.repair_mechanism,
            "severity_rank": template.severity_rank,
            "apex_variables": template.apex_variables,
            "gate_type": GATE_TYPE,
            "reusable_rule": template.reusable_rule,
            "status": "candidate",
            "evidence_grade": "B+: deterministic extraction from uploaded path; requires review before promotion",
            "verification_status": "pending_review_activation_path_intake",
            "boundary": BOUNDARY,
        }
        record["gene_hash"] = _sha256_obj(record)
        records.append(record)
    return records


def _insert_record(conn: sqlite3.Connection, record: Mapping[str, Any]) -> bool:
    if conn.execute("SELECT 1 FROM evolution_genes WHERE gene_id = ?", (record["gene_id"],)).fetchone():
        return False
    conn.execute(
        """
        INSERT INTO evolution_genes
        (gene_id, cycle_id, created_at, defect_no, defect_name, gene_name,
         absorbed_knowledge, source_refs_json, repair_mechanism, severity_rank,
         apex_variables, gate_type, reusable_rule, status, evidence_grade,
         verification_status, boundary, gene_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["gene_id"], record["cycle_id"], record["created_at"], record["defect_no"],
            record["defect_name"], record["gene_name"], record["absorbed_knowledge"],
            record["source_refs_json"], record["repair_mechanism"], record["severity_rank"],
            record["apex_variables"], record["gate_type"], record["reusable_rule"], record["status"],
            record["evidence_grade"], record["verification_status"], record["boundary"], record["gene_hash"],
        ),
    )
    return True


def _write_audit(audit_dir: str | Path, summary: Mapping[str, Any]) -> str:
    path = Path(audit_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    out = path / f"{int(time.time())}_activation_path_gene_intake.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out)


def build_activation_path_gene_intake(
    *,
    source_file: str | Path,
    db_path: str | Path = DEFAULT_GENE_DB_PATH,
    audit_dir: str | Path = DEFAULT_AUDIT_DIR,
    write: bool = False,
    enabled: bool = True,
    mode: str = "coarse",
) -> dict[str, Any]:
    """Build candidate genes from an uploaded AGI/evolution path note.

    Dry-run is the default. Write mode inserts ``candidate`` rows only; it never
    marks rows verified/promoted.
    """
    base = {
        "schema": "PGGActivationPathGeneIntake/v1",
        "created_at": _now(),
        "enabled": bool(enabled),
        "write": bool(write),
        "db_path": str(Path(db_path).expanduser()),
        "source_file": str(Path(source_file).expanduser()),
        "boundary": BOUNDARY,
        "agi_completion_claim": False,
        "promotion_performed": False,
        "mode": mode,
        "available_modes": sorted(TEMPLATE_MODES),
    }
    if not enabled:
        return {**base, "status": "DISABLED", "candidate_count": 0, "records_written": 0, "candidates": [], "audit_path": None}
    try:
        source_path, text = _read_source(source_file)
    except FileNotFoundError as exc:
        return {**base, "status": "BLOCK", "error": "source_file_missing", "details": str(exc), "candidate_count": 0, "records_written": 0, "candidates": [], "audit_path": None}
    try:
        records = _build_candidate_records(source_path, text, mode=mode)
    except ValueError as exc:
        return {**base, "status": "BLOCK", "error": "unsupported_mode", "details": str(exc), "candidate_count": 0, "records_written": 0, "candidates": [], "audit_path": None}
    written = 0
    db = Path(db_path).expanduser()
    if write:
        if not db.exists():
            return {**base, "status": "BLOCK", "error": "gene_db_missing", "candidate_count": len(records), "records_written": 0, "candidates": [], "audit_path": None}
        conn = sqlite3.connect(db)
        try:
            _ensure_cycle(conn)
            for record in records:
                if _insert_record(conn, record):
                    written += 1
            conn.commit()
        finally:
            conn.close()
    summary = {
        **base,
        "status": "PASS" if records else "WATCH",
        "source_sha256": _sha256_text(text),
        "unverified_claims": extract_unverified_claims(text),
        "candidate_count": len(records),
        "records_written": written,
        "side_effects": "inserted_candidate_genes" if write and written else "read_only",
        "candidates": [
            {
                "gene_id": r["gene_id"],
                "defect_no": r["defect_no"],
                "defect_name": r["defect_name"],
                "gene_name": r["gene_name"],
                "status": r["status"],
                "verification_status": r["verification_status"],
                "gene_hash": r["gene_hash"],
            }
            for r in records
        ],
    }
    summary["audit_path"] = _write_audit(audit_dir, summary)
    return summary


__all__ = [
    "BOUNDARY",
    "CYCLE_ID",
    "DEFAULT_AUDIT_DIR",
    "DEFAULT_GENE_DB_PATH",
    "GATE_TYPE",
    "build_activation_path_gene_intake",
    "extract_unverified_claims",
]
