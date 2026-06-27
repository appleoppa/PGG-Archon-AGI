#!/usr/bin/env python3
"""PGG APEX Token Gate.

Three-factor token quality gate:
APEX_score(t) = M(t) * D(t) * J(t)
MIP筛选 -> task relevance M(t)
DTR校验 -> reasoning depth D(t)
ThreeWayStability -> stability J(t)

Boundary: deterministic local scoring; no external LLM/network.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TokenScore:
    schema: str = "PGGApexTokenGateScore/v1"
    generated_at: str = ""
    task: str = ""
    token: str = ""
    M: float = 0.0
    D: float = 0.0
    J: float = 0.0
    APEX_score: float = 0.0
    decision: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    formula: str = "APEX_score(t)=M(t)*D(t)*J(t)"
    boundary: str = "local deterministic scoring; no external LLM/network"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ApexTokenGate:
    """APEX minimal token gate with MIP, DTR and ThreeWayStability factors."""

    REASONING_MARKERS = [
        "because", "therefore", "so", "if", "then", "however", "but", "unless", "evidence",
        "verify", "risk", "boundary", "rollback", "test", "validate", "原因", "因此", "所以", "如果",
        "但是", "然而", "证据", "验证", "风险", "边界", "回滚", "测试", "复核",
    ]
    CONSTRAINT_MARKERS = ["must", "no", "not", "only", "不得", "不能", "只", "必须", "禁止", "边界"]
    EVIDENCE_MARKERS = ["file", "path", "line", "db", "sqlite", "json", "log", "output", "文件", "路径", "日志", "证据", "输出"]
    STOPWORDS = {"the", "and", "for", "with", "that", "this", "from", "into", "to", "of", "in", "on", "a", "an", "is", "are", "进行", "一个", "这个", "需要"}

    def __init__(self, threshold: float = 0.35) -> None:
        self.threshold = float(threshold)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _tokens(cls, text: str) -> list[str]:
        toks = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{1,}|[\u4e00-\u9fff]{1,}", text or "")
        return [t.lower() for t in toks if t.lower() not in cls.STOPWORDS]

    @staticmethod
    def _clip01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def mip_score(self, task: str, token: str) -> tuple[float, dict[str, Any]]:
        """MIP screening: deterministic task relevance proxy."""
        task_tokens = self._tokens(task)
        token_tokens = self._tokens(token)
        if not task_tokens or not token_tokens:
            return 0.0, {"reason": "empty task/token", "overlap": []}
        task_counter = Counter(task_tokens)
        token_counter = Counter(token_tokens)
        overlap = sorted((set(task_counter) & set(token_counter)), key=lambda x: (task_counter[x] + token_counter[x], x), reverse=True)
        weighted_overlap = sum(min(task_counter[t], token_counter[t]) for t in overlap)
        precision = weighted_overlap / max(sum(token_counter.values()), 1)
        recall = weighted_overlap / max(sum(task_counter.values()), 1)
        f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        phrase_bonus = 0.0
        task_lower = task.lower()
        token_lower = token.lower()
        for phrase in re.findall(r"[A-Za-z0-9_\-\u4e00-\u9fff]{3,}", task_lower):
            if phrase in token_lower:
                phrase_bonus += 0.03
        score = self._clip01(f1 + min(0.25, phrase_bonus))
        return round(score, 4), {"precision": round(precision, 4), "recall": round(recall, 4), "overlap": overlap[:20], "phrase_bonus": round(min(0.25, phrase_bonus), 4)}

    def dtr_score(self, token: str) -> tuple[float, dict[str, Any]]:
        """DTR validation: reasoning depth proxy."""
        lower = (token or "").lower()
        length = len(token or "")
        marker_hits = [m for m in self.REASONING_MARKERS if m.lower() in lower]
        constraint_hits = [m for m in self.CONSTRAINT_MARKERS if m.lower() in lower]
        evidence_hits = [m for m in self.EVIDENCE_MARKERS if m.lower() in lower]
        structure_hits = len(re.findall(r"(^|\n)\s*(\d+\.|[-*]|[一二三四五六七八九十]+[、.])", token or ""))
        depth = 0.0
        depth += min(0.30, math.log1p(length) / math.log(2000) * 0.30)
        depth += min(0.25, len(marker_hits) * 0.04)
        depth += min(0.20, len(constraint_hits) * 0.05)
        depth += min(0.15, len(evidence_hits) * 0.04)
        depth += min(0.10, structure_hits * 0.025)
        return round(self._clip01(depth), 4), {
            "length": length,
            "reasoning_markers": marker_hits,
            "constraint_markers": constraint_hits,
            "evidence_markers": evidence_hits,
            "structure_hits": structure_hits,
        }

    def three_way_stability(self, task: str, token: str) -> tuple[float, dict[str, Any]]:
        """Three-way stability from three deterministic judges/views."""
        mip, mip_details = self.mip_score(task, token)
        dtr, dtr_details = self.dtr_score(token)
        token_tokens = self._tokens(token)
        unique_ratio = len(set(token_tokens)) / max(len(token_tokens), 1)
        contradiction_penalty = 0.0
        lower = (token or "").lower()
        contradictory_pairs = [("pass", "fail"), ("完成", "未完成"), ("安全", "风险"), ("允许", "禁止")]
        contradictions = []
        for a, b in contradictory_pairs:
            if a in lower and b in lower:
                contradiction_penalty += 0.08
                contradictions.append([a, b])
        judge_a_relevance = mip
        judge_b_depth = dtr
        judge_c_consistency = self._clip01(0.55 + unique_ratio * 0.35 - contradiction_penalty)
        judges = [judge_a_relevance, judge_b_depth, judge_c_consistency]
        mean = sum(judges) / 3
        variance = sum((x - mean) ** 2 for x in judges) / 3
        stability = self._clip01(mean * (1.0 - min(0.75, variance * 2.0)))
        return round(stability, 4), {
            "judges": {
                "relevance_view": round(judge_a_relevance, 4),
                "depth_view": round(judge_b_depth, 4),
                "consistency_view": round(judge_c_consistency, 4),
            },
            "variance": round(variance, 6),
            "unique_ratio": round(unique_ratio, 4),
            "contradictions": contradictions,
            "mip_overlap": mip_details.get("overlap", []),
            "dtr_markers": dtr_details.get("reasoning_markers", []),
        }

    def score(self, task: str, token: str) -> dict[str, Any]:
        m, m_details = self.mip_score(task, token)
        d, d_details = self.dtr_score(token)
        j, j_details = self.three_way_stability(task, token)
        apex = round(m * d * j, 6)
        decision = "PASS" if apex >= self.threshold else "WATCH"
        return TokenScore(
            generated_at=self._now(),
            task=task,
            token=token,
            M=m,
            D=d,
            J=j,
            APEX_score=apex,
            decision=decision,
            details={"MIP": m_details, "DTR": d_details, "ThreeWayStability": j_details, "threshold": self.threshold},
        ).to_dict()

    def status(self) -> dict[str, Any]:
        return {
            "schema": "PGGApexTokenGateStatus/v1",
            "generated_at": self._now(),
            "class": "ApexTokenGate",
            "formula": "APEX_score(t)=M(t)*D(t)*J(t)",
            "factors": {
                "M(t)": "MIP task relevance score",
                "D(t)": "DTR reasoning depth score",
                "J(t)": "ThreeWayStability stability score",
            },
            "threshold": self.threshold,
            "boundary": "local deterministic scoring; no external LLM/network",
        }


def _read_arg_or_file(value: str | None, file_value: str | None) -> str:
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    return value or ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pgg-apex-token-gate", description="PGG APEX minimal token gate")
    sub = parser.add_subparsers(dest="command")
    p_score = sub.add_parser("score", help="score a token against a task")
    p_score.add_argument("--task", default="", help="task text")
    p_score.add_argument("--token", default="", help="token/candidate text")
    p_score.add_argument("--task-file", default=None)
    p_score.add_argument("--token-file", default=None)
    p_score.add_argument("--threshold", type=float, default=0.35)
    p_status = sub.add_parser("status", help="show gate status/formula")
    p_status.add_argument("--threshold", type=float, default=0.35)
    args = parser.parse_args(argv)
    if args.command in (None, "status"):
        threshold = getattr(args, "threshold", 0.35)
        print(json.dumps(ApexTokenGate(threshold=threshold).status(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "score":
        task = _read_arg_or_file(args.task, args.task_file)
        token = _read_arg_or_file(args.token, args.token_file)
        data = ApexTokenGate(threshold=args.threshold).score(task, token)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0 if data["decision"] == "PASS" else 2
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
