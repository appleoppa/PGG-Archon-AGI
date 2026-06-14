#!/usr/bin/env python3
"""PGG Dream Mode.

Four-phase local dream cycle for GeneDB pattern recognition:
REMINISCE -> SYNTHESIZE -> SIMULATE -> TRANSCEND.

Boundary: read-only GeneDB access; no external network; no LLM calls; no gene mutation.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

HOME = Path.home()
DB_PATH = HOME / ".hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3"


class DreamPhase(str, Enum):
    REMINISCE = "REMINISCE"
    SYNTHESIZE = "SYNTHESIZE"
    SIMULATE = "SIMULATE"
    TRANSCEND = "TRANSCEND"


@dataclass
class DreamCycleResult:
    schema: str = "PGGDreamCycle/v1"
    generated_at: str = ""
    db_path: str = ""
    phases: list[str] = field(default_factory=lambda: [p.value for p in DreamPhase])
    reminisce: dict[str, Any] = field(default_factory=dict)
    synthesize: dict[str, Any] = field(default_factory=dict)
    simulate: dict[str, Any] = field(default_factory=dict)
    transcend: dict[str, Any] = field(default_factory=dict)
    boundary: str = "read-only/local-only/no-external-llm/no-gene-mutation"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DreamCycle:
    """Four-stage PGG dream cycle over local GeneDB."""

    PHASES = [DreamPhase.REMINISCE, DreamPhase.SYNTHESIZE, DreamPhase.SIMULATE, DreamPhase.TRANSCEND]
    SECURITY_GATE_KEYWORDS = {
        "source": ["source", "来源", "引用", "reference", "evidence", "证据"],
        "verification": ["verify", "校验", "验证", "audit", "审计", "复核"],
        "boundary": ["boundary", "边界", "禁止", "不得", "只读", "local"],
        "hallucination": ["幻觉", "hallucination", "编造", "事实", "核验"],
        "credential": ["credential", "secret", "token", "密钥", "凭据"],
        "scheduler": ["cron", "launchd", "scheduler", "调度", "无人值守"],
        "memory": ["memory", "记忆", "固化", "manifest", "状态"],
        "case": ["case", "案件", "法律", "CMS", "trusted"],
        "quality": ["quality", "质量", "fitness", "门禁", "gate"],
        "rollback": ["rollback", "回滚", "backup", "备份", "恢复"],
    }

    STOPWORDS = {
        "the", "and", "for", "with", "that", "this", "from", "into", "must", "should",
        "not", "no", "none", "true", "false", "null", "local", "only", "pgg", "apex",
        "进行", "必须", "不得", "不能", "通过", "系统", "模块", "本地", "一个", "作为", "需要",
    }

    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path = Path(db_path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _rows(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    @classmethod
    def _tokens(cls, text: str) -> list[str]:
        raw = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}|[\u4e00-\u9fff]{2,}", text or "")
        return [t.lower() for t in raw if t.lower() not in cls.STOPWORDS and len(t) <= 40]

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"GeneDB not found: {self.db_path}")
        con = sqlite3.connect(str(self.db_path))
        con.row_factory = sqlite3.Row
        return con

    def reminisce(self, limit: int = 5000) -> dict[str, Any]:
        """Read GeneDB and identify cross-gene patterns without mutating data."""
        with self._connect() as con:
            cur = con.cursor()
            total = self._rows(cur, "SELECT COUNT(*) AS c FROM evolution_genes")[0]["c"]
            by_status = self._rows(
                cur,
                "SELECT COALESCE(status,'UNKNOWN') AS status, COUNT(*) AS count "
                "FROM evolution_genes GROUP BY COALESCE(status,'UNKNOWN') ORDER BY count DESC",
            )
            by_gate = self._rows(
                cur,
                "SELECT COALESCE(NULLIF(gate_type,''),'UNKNOWN') AS gate_type, COUNT(*) AS count, "
                "ROUND(AVG(COALESCE(fitness,0)),2) AS avg_fitness "
                "FROM evolution_genes GROUP BY COALESCE(NULLIF(gate_type,''),'UNKNOWN') "
                "ORDER BY count DESC LIMIT 25",
            )
            cross = self._rows(
                cur,
                "SELECT COALESCE(NULLIF(defect_name,''),'UNKNOWN') AS defect_name, "
                "COALESCE(NULLIF(gate_type,''),'UNKNOWN') AS gate_type, COUNT(*) AS count, "
                "ROUND(AVG(COALESCE(severity_rank,0)),2) AS avg_severity, "
                "ROUND(AVG(COALESCE(fitness,0)),2) AS avg_fitness "
                "FROM evolution_genes GROUP BY defect_name, gate_type "
                "HAVING count >= 2 ORDER BY count DESC, avg_fitness DESC LIMIT 40",
            )
            samples = self._rows(
                cur,
                "SELECT gene_id, gene_name, defect_name, gate_type, status, verification_status, "
                "fitness, absorbed_knowledge, repair_mechanism, reusable_rule, boundary, apex_variables "
                "FROM evolution_genes ORDER BY COALESCE(fitness,0) DESC, created_at DESC LIMIT ?",
                (limit,),
            )

        token_counts: Counter[str] = Counter()
        gate_tokens: dict[str, Counter[str]] = defaultdict(Counter)
        status_gate: Counter[str] = Counter()
        for row in samples:
            blob = " ".join(str(row.get(k) or "") for k in (
                "gene_name", "defect_name", "gate_type", "absorbed_knowledge",
                "repair_mechanism", "reusable_rule", "boundary", "apex_variables",
            ))
            toks = self._tokens(blob)
            token_counts.update(toks)
            gate = str(row.get("gate_type") or "UNKNOWN")[:80]
            gate_tokens[gate].update(toks)
            status_gate[f"{row.get('status') or 'UNKNOWN'}::{gate}"] += 1

        motifs = []
        for gate, counts in sorted(gate_tokens.items(), key=lambda kv: sum(kv[1].values()), reverse=True)[:12]:
            motifs.append({"gate_type": gate, "top_terms": counts.most_common(8)})

        return {
            "phase": DreamPhase.REMINISCE.value,
            "db_exists": True,
            "total_genes": total,
            "sampled_genes": len(samples),
            "by_status": by_status,
            "by_gate": by_gate,
            "cross_gene_patterns": cross,
            "top_global_terms": token_counts.most_common(30),
            "gate_motifs": motifs,
            "status_gate_pairs": status_gate.most_common(25),
        }

    def synthesize(self, reminisce: dict[str, Any]) -> dict[str, Any]:
        """Compress remembered patterns into reusable dream hypotheses."""
        top_terms = [term for term, _ in reminisce.get("top_global_terms", [])[:15]]
        gate_counts = reminisce.get("by_gate", [])
        status_counts = {r.get("status"): r.get("count", 0) for r in reminisce.get("by_status", [])}
        candidate_backlog = int(status_counts.get("candidate", 0) or 0)
        verified = int(status_counts.get("verified", 0) or 0)
        total = int(reminisce.get("total_genes", 0) or 0)
        dominant_gates = [r.get("gate_type") for r in gate_counts[:5]]
        hypotheses = []
        if candidate_backlog > verified:
            hypotheses.append("candidate backlog dominates verified genes; dream should prioritize evidence/verification gates")
        if any("dream" in str(g).lower() for g in dominant_gates):
            hypotheses.append("dream/fusion genes are prominent; fitness inflation and boundary checks need attention")
        if any(t in top_terms for t in ("verification", "audit", "验证", "审计")):
            hypotheses.append("verification/audit language is a cross-gene attractor")
        if any(t in top_terms for t in ("boundary", "边界", "禁止")):
            hypotheses.append("boundary preservation is a recurring repair mechanism")
        if not hypotheses:
            hypotheses.append("no single motif dominates; keep gate coverage broad and read-only")
        compression_ratio = round(len(top_terms) / max(total, 1), 6)
        return {
            "phase": DreamPhase.SYNTHESIZE.value,
            "dominant_gates": dominant_gates,
            "dream_terms": top_terms,
            "hypotheses": hypotheses,
            "compression_ratio": compression_ratio,
            "synthesis": "跨基因模式已压缩为门禁覆盖、验证优先、边界守恒三类梦境假设。",
        }

    def simulate(self, reminisce: dict[str, Any], synthesize: dict[str, Any]) -> dict[str, Any]:
        """Adversarial safety simulation: inspect gene-gate coverage."""
        text = json.dumps(reminisce, ensure_ascii=False).lower() + " " + json.dumps(synthesize, ensure_ascii=False).lower()
        coverage = {}
        for gate, words in self.SECURITY_GATE_KEYWORDS.items():
            hits = [w for w in words if w.lower() in text]
            coverage[gate] = {"covered": bool(hits), "hits": hits, "score": min(1.0, len(hits) / 3.0)}
        missing = [k for k, v in coverage.items() if not v["covered"]]
        weak = [k for k, v in coverage.items() if v["covered"] and v["score"] < 0.67]
        scenarios = [
            {
                "name": "fitness_inflation_attack",
                "question": "高 fitness/梦境融合基因是否绕过证据与验证门禁？",
                "covered_by": [g for g in ("verification", "quality", "source") if coverage[g]["covered"]],
                "residual_risk": "WATCH" if any(not coverage[g]["covered"] for g in ("verification", "quality", "source")) else "LOW",
            },
            {
                "name": "boundary_erosion_attack",
                "question": "自动闭环是否可能越过只读、本地、凭据、调度边界？",
                "covered_by": [g for g in ("boundary", "credential", "scheduler", "rollback") if coverage[g]["covered"]],
                "residual_risk": "WATCH" if any(not coverage[g]["covered"] for g in ("boundary", "credential")) else "LOW",
            },
            {
                "name": "hallucinated_completion_attack",
                "question": "状态字段/口号是否冒充真实完成？",
                "covered_by": [g for g in ("hallucination", "verification", "memory") if coverage[g]["covered"]],
                "residual_risk": "WATCH" if any(not coverage[g]["covered"] for g in ("hallucination", "verification")) else "LOW",
            },
        ]
        covered_count = sum(1 for v in coverage.values() if v["covered"])
        coverage_ratio = round(covered_count / max(len(coverage), 1), 4)
        return {
            "phase": DreamPhase.SIMULATE.value,
            "adversarial_scenarios": scenarios,
            "gate_coverage": coverage,
            "coverage_ratio": coverage_ratio,
            "missing_gates": missing,
            "weak_gates": weak,
            "status": "PASS_COVERAGE_BROAD" if coverage_ratio >= 0.8 and not missing else "WATCH_COVERAGE_GAPS",
        }

    def transcend(self, reminisce: dict[str, Any], synthesize: dict[str, Any], simulate: dict[str, Any]) -> dict[str, Any]:
        """Emit bounded dream-realm gain."""
        pattern_count = len(reminisce.get("cross_gene_patterns", []))
        motif_count = len(reminisce.get("gate_motifs", []))
        coverage_ratio = float(simulate.get("coverage_ratio", 0.0) or 0.0)
        hypotheses = len(synthesize.get("hypotheses", []))
        gain = round((math.log1p(pattern_count) * 0.35 + math.log1p(motif_count) * 0.25 + coverage_ratio * 0.30 + min(hypotheses, 5) / 5 * 0.10), 4)
        return {
            "phase": DreamPhase.TRANSCEND.value,
            "dream_realm_gain": gain,
            "gain_components": {
                "cross_patterns": pattern_count,
                "motifs": motif_count,
                "coverage_ratio": coverage_ratio,
                "hypotheses": hypotheses,
            },
            "transcendent_outputs": [
                "将跨基因共同词/门禁组合转化为下一轮本地审计线索。",
                "优先补齐 adversarial 模拟中 missing/weak 的安全门禁。",
                "保持 GeneDB 只读：梦境增益是观察和排序，不是自动晋升。",
            ],
            "status": "TRANSCEND_BOUNDED_GAIN_EMITTED",
        }

    def run(self, limit: int = 5000) -> dict[str, Any]:
        result = DreamCycleResult(generated_at=self._now(), db_path=str(self.db_path))
        try:
            result.reminisce = self.reminisce(limit=limit)
            result.synthesize = self.synthesize(result.reminisce)
            result.simulate = self.simulate(result.reminisce, result.synthesize)
            result.transcend = self.transcend(result.reminisce, result.synthesize, result.simulate)
        except Exception as exc:
            result.reminisce = {"phase": DreamPhase.REMINISCE.value, "error": f"{type(exc).__name__}: {exc}"}
            result.synthesize = {"phase": DreamPhase.SYNTHESIZE.value, "status": "SKIPPED"}
            result.simulate = {"phase": DreamPhase.SIMULATE.value, "status": "SKIPPED"}
            result.transcend = {"phase": DreamPhase.TRANSCEND.value, "status": "ERROR", "dream_realm_gain": 0.0}
        return result.to_dict()

    def status(self) -> dict[str, Any]:
        data = self.run(limit=1000)
        data["cli"] = "pgg-dream-mode status"
        return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pgg-dream-mode", description="PGG Dream Mode four-phase local cycle")
    sub = parser.add_subparsers(dest="command")
    p_status = sub.add_parser("status", help="run dream-mode status")
    p_status.add_argument("--db", default=str(DB_PATH))
    p_status.add_argument("--limit", type=int, default=1000)
    p_status.add_argument("--json", action="store_true", default=True)
    args = parser.parse_args(argv)
    if args.command in (None, "status"):
        cycle = DreamCycle(Path(getattr(args, "db", DB_PATH)))
        data = cycle.run(limit=getattr(args, "limit", 1000))
        print(json.dumps(data, ensure_ascii=False, indent=2))
        if "error" in data.get("reminisce", {}):
            return 2
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
