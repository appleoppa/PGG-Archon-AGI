"""PGG ARIS Reflection — three-layer self-evolution reflection pipeline.

L1 deviation review: compare latest self-evolution loop status with expected goals.
L2 logic-hole review: inspect recent auto-fusion genes for precondition/constraint
    mismatches.
L3 architecture-boundary review: scan auto_fusion distribution and detect candidate
    pile-up / verified shortage.

Boundary: local JSON + SQLite reads only; no network, no provider/scheduler/core
mutation, no AGI/T5/ASI claims.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping

DEFAULT_DB = Path("/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")
DEFAULT_LATEST = Path("/Users/appleoppa/.hermes/data/self-evolution-loop/latest.json")
DEFAULT_LOG_DIR = Path("/Users/appleoppa/.hermes/data/pgg_aris_reflection")
BOUNDARY = "pgg_aris_reflection; local read-only reflection; no LLM/network; no AGI/T5/ASI claim"
SCHEMA = "PGGARISReflection/v1"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _json_loads_maybe(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return fallback


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    parsed = _json_loads_maybe(value, None)
    if isinstance(parsed, list):
        return [str(v) for v in parsed if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [p.strip() for p in re.split(r"[\n;；。]+", text) if p.strip()]


def _safe_ratio(num: float, den: float) -> float:
    return 0.0 if den <= 0 else num / den


class ArisReflector:
    """ARIS three-layer reflector embedded in the self-evolution loop."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB,
        *,
        latest_path: str | Path = DEFAULT_LATEST,
        log_dir: str | Path = DEFAULT_LOG_DIR,
        expected_min_fused: int = 1,
        expected_status: str = "PASS",
        max_l2_scan: int = 120,
    ) -> None:
        self.db_path = Path(db_path)
        self.latest_path = Path(latest_path)
        self.log_dir = Path(log_dir)
        self.expected_min_fused = expected_min_fused
        self.expected_status = expected_status
        self.max_l2_scan = max_l2_scan

    def run_reflection(self) -> dict[str, Any]:
        """Run L1/L2/L3 and return the required compact summary."""
        details: dict[str, Any] = {}
        errors: list[str] = []
        try:
            l1 = self._l1_deviation_review()
        except Exception as exc:
            l1 = {"deviation_score": 1.0, "issues": [f"l1_error:{type(exc).__name__}:{exc}"]}
            errors.append(l1["issues"][0])
        try:
            l2 = self._l2_logic_holes()
        except Exception as exc:
            l2 = [{"type": "l2_error", "detail": f"{type(exc).__name__}: {exc}"}]
            errors.append(l2[0]["detail"])
        try:
            l3 = self._l3_architecture_boundaries()
        except Exception as exc:
            l3 = [{"type": "l3_error", "detail": f"{type(exc).__name__}: {exc}"}]
            errors.append(l3[0]["detail"])

        recommendation = self._recommend(float(l1.get("deviation_score", 1.0)), l2, l3)
        result = {
            "schema": SCHEMA,
            "created_at": _now(),
            "l1_score": round(float(l1.get("deviation_score", 1.0)), 4),
            "l2_issues": l2,
            "l3_blockers": l3,
            "recommendation": recommendation,
            "errors": errors,
            "details": {"l1": l1, **details},
            "boundary": BOUNDARY,
        }
        self._write_log(result)
        return result

    # ── L1: 偏差复盘 ───────────────────────────────────────────────────

    def _l1_deviation_review(self) -> dict[str, Any]:
        latest = self._read_latest_json()
        issues: list[str] = []
        score = 0.0

        status = str(latest.get("status") or "UNKNOWN")
        if status != self.expected_status:
            issues.append(f"status_expected_{self.expected_status}_got_{status}")
            score += 0.35

        exit_code = latest.get("exit_code")
        if exit_code not in (0, "0", None):
            issues.append(f"exit_code_nonzero:{exit_code}")
            score += 0.20

        stdout = str(latest.get("stdout") or "")
        fused = self._extract_metric(stdout, [r"fused:\s*(\d+)", r"融合[^\n]*?([0-9]+)\s*new offspring"])
        promoted = self._extract_metric(stdout, [r"promoted:\s*(\d+)"])
        total = self._extract_metric(stdout, [r"总基因数:\s*(\d+)"])
        if fused is not None and fused < self.expected_min_fused:
            issues.append(f"fused_below_expected:{fused}<{self.expected_min_fused}")
            score += 0.20
        if fused is None and "fusion" in stdout.lower():
            issues.append("fusion_metric_unparseable")
            score += 0.10
        if total == 0:
            issues.append("total_gene_count_zero")
            score += 0.15
        if not self.latest_path.exists():
            issues.append("latest_json_missing")
            score = max(score, 0.80)

        started = latest.get("started_epoch")
        completed = latest.get("completed_epoch")
        if isinstance(started, (int, float)) and isinstance(completed, (int, float)) and completed < started:
            issues.append("completed_before_started")
            score += 0.15

        return {
            "schema": f"{SCHEMA}/L1",
            "deviation_score": min(1.0, score),
            "issues": issues,
            "observed": {
                "status": status,
                "exit_code": exit_code,
                "fused": fused,
                "promoted": promoted,
                "total_genes": total,
            },
        }

    def _read_latest_json(self) -> dict[str, Any]:
        if not self.latest_path.exists():
            return {}
        text = self.latest_path.read_text(encoding="utf-8", errors="replace")
        parsed = _json_loads_maybe(text, {})
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _extract_metric(text: str, patterns: list[str]) -> int | None:
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    return None
        return None

    # ── L2: 逻辑漏洞 ───────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.row_factory = sqlite3.Row
        return con

    def _columns(self, con: sqlite3.Connection) -> set[str]:
        return {row[1] for row in con.execute("PRAGMA table_info(evolution_genes)").fetchall()}

    def _l2_logic_holes(self) -> list[dict[str, Any]]:
        con = self._connect()
        try:
            cols = self._columns(con)
            id_col = "id" if "id" in cols else "gene_id"
            order_col = "created" if "created" in cols else "created_at" if "created_at" in cols else id_col
            select_cols = ", ".join(sorted(cols))

            if "origin" in cols:
                where = "origin = 'auto_fusion'"
            elif "absorbed_knowledge" in cols:
                where = "absorbed_knowledge LIKE '%auto_fusion%' OR gate_type LIKE '%fusion%' OR gate_type LIKE '%dream_mode%'"
            else:
                where = "category LIKE '%fusion%'"

            rows = con.execute(
                f"SELECT {select_cols} FROM evolution_genes WHERE {where} ORDER BY {order_col} DESC LIMIT ?",
                (self.max_l2_scan,),
            ).fetchall()
            issues: list[dict[str, Any]] = []
            for row in rows:
                issue = self._inspect_fusion_record(dict(row), id_col=id_col)
                if issue:
                    issues.extend(issue)
            return issues[:50]
        finally:
            con.close()

    def _inspect_fusion_record(self, row: Mapping[str, Any], *, id_col: str) -> list[dict[str, Any]]:
        gid = str(row.get(id_col) or "")
        absorbed = _json_loads_maybe(row.get("absorbed_knowledge"), {})
        if not isinstance(absorbed, dict):
            absorbed = {}
        preconditions = _as_list(row.get("preconditions") or absorbed.get("preconditions"))
        constraints = row.get("constraints") or absorbed.get("constraints") or row.get("boundary") or {}
        raw_constraints = _as_text(constraints).lower()
        raw_preconditions = "\n".join(preconditions).lower()
        validation = _as_text(row.get("validation") or absorbed.get("validation") or row.get("verification_status"))
        parent_ids = absorbed.get("parent_ids") or (absorbed.get("constraints") or {}).get("parents") or []

        issues: list[dict[str, Any]] = []
        contradiction_map = {
            "network": ["no network", "no_network", "禁止网络"],
            "llm": ["no llm", "no_llm", "禁止llm"],
            "write": ["read-only", "readonly", "no write", "no_write", "禁止写"],
            "delete": ["no delete", "no_delete", "禁止删"],
            "promote": ["no promote", "no_promote", "禁止晋升"],
        }
        for required, forbids in contradiction_map.items():
            if required in raw_preconditions and any(f in raw_constraints for f in forbids):
                issues.append({"gene_id": gid, "type": "precondition_constraint_conflict", "required": required})

        if "candidate" in raw_preconditions and "must_be_verified" in raw_constraints:
            issues.append({"gene_id": gid, "type": "candidate_vs_must_be_verified"})
        if not parent_ids:
            issues.append({"gene_id": gid, "type": "missing_parent_trace"})
        if not preconditions:
            issues.append({"gene_id": gid, "type": "missing_preconditions"})
        if "pending" not in validation.lower() and str(row.get("status") or "") == "candidate":
            issues.append({"gene_id": gid, "type": "candidate_without_pending_validation_marker"})
        return issues

    # ── L3: 架构边界 ───────────────────────────────────────────────────

    def _l3_architecture_boundaries(self) -> list[dict[str, Any]]:
        con = self._connect()
        try:
            cols = self._columns(con)
            if "origin" in cols:
                where = "origin = 'auto_fusion'"
            elif "absorbed_knowledge" in cols:
                where = "absorbed_knowledge LIKE '%auto_fusion%' OR gate_type LIKE '%fusion%' OR gate_type LIKE '%dream_mode%'"
            else:
                where = "category LIKE '%fusion%'"

            status_rows = con.execute(
                f"SELECT status, COUNT(*) AS n FROM evolution_genes WHERE {where} GROUP BY status"
            ).fetchall()
            dist = {str(r["status"]): int(r["n"]) for r in status_rows}
            total = sum(dist.values())
            candidate = dist.get("candidate", 0)
            verified = dist.get("verified", 0) + dist.get("active", 0)
            blockers: list[dict[str, Any]] = []
            if total == 0:
                blockers.append({"type": "no_auto_fusion_records", "severity": "medium", "distribution": dist})
                return blockers
            candidate_ratio = _safe_ratio(candidate, total)
            verified_ratio = _safe_ratio(verified, total)
            if candidate >= 50 and candidate_ratio >= 0.70:
                blockers.append(
                    {
                        "type": "candidate_pileup",
                        "severity": "high",
                        "candidate": candidate,
                        "total": total,
                        "candidate_ratio": round(candidate_ratio, 4),
                    }
                )
            if verified < 2 or verified_ratio < 0.10:
                blockers.append(
                    {
                        "type": "verified_shortage",
                        "severity": "high" if verified < 2 else "medium",
                        "verified_or_active": verified,
                        "total": total,
                        "verified_ratio": round(verified_ratio, 4),
                    }
                )
            rejected = dist.get("rejected", 0)
            if _safe_ratio(rejected, total) >= 0.50:
                blockers.append({"type": "fusion_rejection_dominance", "severity": "medium", "rejected": rejected, "total": total})
            if not blockers:
                blockers.append({"type": "no_l3_blocker_detected", "severity": "none", "distribution": dist, "total": total})
            return blockers
        finally:
            con.close()

    # ── recommendation/logging ──────────────────────────────────────────

    @staticmethod
    def _recommend(l1_score: float, l2_issues: list[dict[str, Any]], l3_blockers: list[dict[str, Any]]) -> str:
        serious_l3 = [b for b in l3_blockers if b.get("severity") in {"high", "medium"}]
        if l1_score >= 0.5:
            return "BLOCK_SELF_EVOLUTION_AND_REPAIR_L1_DEVIATION"
        if any(i.get("type") == "precondition_constraint_conflict" for i in l2_issues):
            return "PAUSE_AUTO_FUSION_AND_FIX_PRECONDITION_CONSTRAINT_LOGIC"
        if serious_l3:
            kinds = ",".join(str(b.get("type")) for b in serious_l3)
            return f"THROTTLE_DREAM_FUSION_AND_PRIORITIZE_VERIFICATION:{kinds}"
        if l2_issues:
            return "ALLOW_WITH_REVIEW:FIX_L2_TRACEABILITY_AND_PENDING_MARKERS"
        return "ALLOW_SELF_EVOLUTION_CONTINUE_WITH_ARIS_MONITORING"

    def _write_log(self, result: Mapping[str, Any]) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        stamp = time.strftime("%Y%m%dT%H%M%S")
        (self.log_dir / "latest.json").write_text(payload + "\n", encoding="utf-8")
        (self.log_dir / f"aris_reflection_{stamp}.json").write_text(payload + "\n", encoding="utf-8")


__all__ = ["ArisReflector"]


if __name__ == "__main__":
    print(json.dumps(ArisReflector().run_reflection(), ensure_ascii=False, indent=2, sort_keys=True))
