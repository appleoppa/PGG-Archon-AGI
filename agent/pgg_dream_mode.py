"""PGG Dream Mode — adversarial multi-pattern gene dream synthesis.

Implements a local-only four-stage loop for PGG Archon:
1. REMINISCE: read active/verified genes from GeneDB and discover cross-patterns
   with lightweight TF-IDF style similarity.
2. SYNTHESIZE: rule-based fusion of compatible parent patterns. LLM calls are
   intentionally not used because the surrounding LLM APIs are timeout-prone.
   Fitness formula: F_offspring = sqrt(F_A * F_B) * 1.5
3. SIMULATE: validate precondition/constraint compatibility.
4. TRANSCEND: write candidate offspring genes back to GeneDB and emit logs.

Boundary: local SQLite/file operations only; no network, no provider changes, no
AGI/T5/ASI claims.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT_DB = Path("/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")
DEFAULT_LOG_DIR = Path("/Users/appleoppa/.hermes/data/pgg_dream_mode")
BOUNDARY = "pgg_dream_mode; local GeneDB synthesis; rule-based fusion; no LLM/network; no AGI/T5/ASI claim"
SCHEMA = "PGGDreamMode/v1"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def _json_loads_maybe(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return fallback


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, tuple):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, dict):
        return [json.dumps(value, ensure_ascii=False, sort_keys=True)]
    text = str(value).strip()
    if not text:
        return []
    parsed = _json_loads_maybe(text, None)
    if isinstance(parsed, list):
        return [str(v).strip() for v in parsed if str(v).strip()]
    if isinstance(parsed, dict):
        return [json.dumps(parsed, ensure_ascii=False, sort_keys=True)]
    parts = re.split(r"[\n;；。]+", text)
    return [p.strip() for p in parts if p.strip()]


def _uniq(items: Iterable[Any], *, limit: int | None = None) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for item in items:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            out.append(item)
        if limit is not None and len(out) >= limit:
            break
    return out


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9_\-]{2,}|[\u4e00-\u9fff]", text.lower())
    return words or [text.lower()] if text else []


def _cosine(a: Counter[str], b: Counter[str], idf: Mapping[str, float]) -> float:
    common = set(a) & set(b)
    numerator = sum((a[t] * idf.get(t, 1.0)) * (b[t] * idf.get(t, 1.0)) for t in common)
    na = math.sqrt(sum((v * idf.get(t, 1.0)) ** 2 for t, v in a.items()))
    nb = math.sqrt(sum((v * idf.get(t, 1.0)) ** 2 for t, v in b.items()))
    if na == 0 or nb == 0:
        return 0.0
    return numerator / (na * nb)


class DreamEngine:
    """Four-stage local dream synthesis engine for PGG genes."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB,
        *,
        log_dir: str | Path = DEFAULT_LOG_DIR,
        max_parents: int = 80,
        max_offspring: int = 24,
        min_similarity: float = 0.08,
    ) -> None:
        self.db_path = Path(db_path)
        self.log_dir = Path(log_dir)
        self.max_parents = max_parents
        self.max_offspring = max_offspring
        self.min_similarity = min_similarity

    def run_full_cycle(self) -> dict[str, Any]:
        """Run REMINISCE→SYNTHESIZE→SIMULATE→TRANSCEND.

        Returns a compact result required by the caller:
        {synth_count, new_genes, errors}
        """
        errors: list[str] = []
        new_genes: list[str] = []
        started = _now()
        patterns: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []
        simulated: list[dict[str, Any]] = []

        try:
            genes = self._reminisce()
            patterns = self._discover_patterns(genes)
            candidates = self._synthesize(patterns)
            simulated = self._simulate(candidates)
            new_genes = self._transcend([g for g in simulated if g.get("simulation", {}).get("compatible")])
        except Exception as exc:  # keep API stable for unattended loop callers
            errors.append(f"{type(exc).__name__}: {exc}")

        result = {
            "schema": SCHEMA,
            "started_at": started,
            "completed_at": _now(),
            "synth_count": len(new_genes),
            "new_genes": new_genes,
            "errors": errors,
            "stage_counts": {
                "patterns": len(patterns),
                "synthesized": len(candidates),
                "simulated": len(simulated),
            },
            "boundary": BOUNDARY,
        }
        self._write_log(result)
        # Required shape, with extra fields retained for observability.
        return result

    # ── Stage 1: REMINISCE ──────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.row_factory = sqlite3.Row
        return con

    def _columns(self, con: sqlite3.Connection) -> set[str]:
        return {row[1] for row in con.execute("PRAGMA table_info(evolution_genes)").fetchall()}

    def _reminisce(self) -> list[dict[str, Any]]:
        con = self._connect()
        try:
            cols = self._columns(con)
            id_col = "id" if "id" in cols else "gene_id"
            fitness_expr = "COALESCE(fitness, 0)" if "fitness" in cols else "0"
            select_cols = ", ".join(sorted(cols))
            rows = con.execute(
                f"SELECT {select_cols} FROM evolution_genes "
                f"WHERE status IN ('active','verified') "
                f"ORDER BY {fitness_expr} DESC LIMIT ?",
                (self.max_parents,),
            ).fetchall()
            genes = [self._row_to_standard_gene(dict(row), id_col=id_col) for row in rows]
            return [g for g in genes if g.get("id")]
        finally:
            con.close()

    def _row_to_standard_gene(self, row: Mapping[str, Any], *, id_col: str) -> dict[str, Any]:
        absorbed = _json_loads_maybe(row.get("absorbed_knowledge"), {})
        if not isinstance(absorbed, dict):
            absorbed = {}

        gid = str(row.get(id_col) or absorbed.get("id") or "").strip()
        category = str(row.get("category") or absorbed.get("category") or row.get("gate_type") or "dream_pattern").strip()
        signals = _as_list(row.get("signals_match") or absorbed.get("signals_match"))
        if not signals:
            signals = _as_list([row.get("defect_name"), row.get("gene_name"), row.get("gate_type")])
        preconditions = _as_list(row.get("preconditions") or absorbed.get("preconditions"))
        if not preconditions:
            preconditions = ["source gene status is active_or_verified"]
        strategy = _as_list(row.get("strategy") or absorbed.get("strategy") or row.get("repair_mechanism") or row.get("reusable_rule"))
        constraints = row.get("constraints") or absorbed.get("constraints") or {}
        if not isinstance(constraints, dict):
            constraints = {"raw_constraints": str(constraints)}
        validation = _as_list(row.get("validation") or absorbed.get("validation") or row.get("verification_status"))
        fitness = row.get("fitness") if row.get("fitness") is not None else absorbed.get("fitness", 0)
        try:
            fitness_f = float(0 if fitness is None else fitness)
        except Exception:
            fitness_f = 0.0
        return {
            "type": str(row.get("type") or absorbed.get("type") or "pgg_gene"),
            "id": gid,
            "category": category or "dream_pattern",
            "signals_match": _uniq(signals, limit=20),
            "preconditions": _uniq(preconditions, limit=20),
            "strategy": _uniq(strategy, limit=30),
            "constraints": constraints,
            "validation": _uniq(validation, limit=20),
            "status": str(row.get("status") or ""),
            "fitness": fitness_f,
        }

    def _discover_patterns(self, genes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        docs: list[str] = []
        vectors: list[Counter[str]] = []
        for gene in genes:
            doc = " ".join(
                [gene.get("category", "")]
                + gene.get("signals_match", [])
                + gene.get("preconditions", [])
                + gene.get("strategy", [])
                + gene.get("validation", [])
            )
            docs.append(doc)
            vectors.append(Counter(_tokens(doc)))
        df = Counter(t for vec in vectors for t in vec.keys())
        n = max(1, len(vectors))
        idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}

        patterns: list[dict[str, Any]] = []
        for i, left in enumerate(genes):
            for j in range(i + 1, len(genes)):
                right = genes[j]
                if left.get("id") == right.get("id"):
                    continue
                # Cross-mode: prefer different categories, but allow high-sim same-category pairs.
                similarity = _cosine(vectors[i], vectors[j], idf)
                cross_category = left.get("category") != right.get("category")
                if similarity >= self.min_similarity and (cross_category or similarity >= self.min_similarity * 2):
                    patterns.append(
                        {
                            "parents": [left, right],
                            "similarity": round(similarity, 6),
                            "cross_category": cross_category,
                        }
                    )
        patterns.sort(key=lambda p: (p["cross_category"], p["similarity"], sum(g.get("fitness", 0) for g in p["parents"])), reverse=True)
        return patterns[: self.max_offspring * 3]

    # ── Stage 2: SYNTHESIZE ─────────────────────────────────────────────

    def _synthesize(self, patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        used_pairs: set[str] = set()
        for pattern in patterns:
            a, b = pattern["parents"]
            pair_key = "|".join(sorted([a["id"], b["id"]]))
            if pair_key in used_pairs:
                continue
            used_pairs.add(pair_key)
            fa = max(float(a.get("fitness") or 0), 1.0)
            fb = max(float(b.get("fitness") or 0), 1.0)
            offspring_fitness = math.sqrt(fa * fb) * 1.5
            oid = "dream_auto_fusion_" + _hash({"parents": [a["id"], b["id"]], "formula": "sqrt_product_x1.5"})[:16]
            gene = {
                "type": "pgg_gene",
                "id": oid,
                "category": f"dream_fusion:{a.get('category')}+{b.get('category')}",
                "signals_match": _uniq(a.get("signals_match", []) + b.get("signals_match", []), limit=30),
                "preconditions": _uniq(a.get("preconditions", []) + b.get("preconditions", []), limit=30),
                "strategy": _uniq(
                    [
                        "Dream Mode rule fusion: identify shared latent signal, then apply both parent repair strategies under compatibility gate.",
                        *a.get("strategy", []),
                        *b.get("strategy", []),
                    ],
                    limit=40,
                ),
                "constraints": {
                    "origin": "auto_fusion",
                    "dream_mode": True,
                    "parents": [a["id"], b["id"]],
                    "parent_categories": [a.get("category"), b.get("category")],
                    "parent_constraints": [a.get("constraints", {}), b.get("constraints", {})],
                    "fusion_formula": "sqrt(F_A * F_B) * 1.5",
                    "similarity": pattern.get("similarity"),
                    "boundary": BOUNDARY,
                },
                "validation": _uniq(
                    [
                        "pending_review_dream_mode_candidate",
                        "simulated_precondition_constraint_compatibility_required",
                        *a.get("validation", []),
                        *b.get("validation", []),
                    ],
                    limit=30,
                ),
                "status": "candidate",
                "fitness": round(offspring_fitness, 3),
                "created": _now(),
                "origin": "auto_fusion",
                "parent_ids": [a["id"], b["id"]],
            }
            gene["gene_hash"] = _hash({k: v for k, v in gene.items() if k != "gene_hash"})
            out.append(gene)
            if len(out) >= self.max_offspring:
                break
        return out

    # ── Stage 3: SIMULATE ───────────────────────────────────────────────

    def _simulate(self, genes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for gene in genes:
            issues = self._compatibility_issues(gene)
            gene["simulation"] = {
                "compatible": not issues,
                "issues": issues,
                "checked_at": _now(),
                "method": "rule_based_precondition_constraint_scan",
            }
            if issues:
                gene["validation"] = _uniq(gene.get("validation", []) + ["simulation_blocked:" + ";".join(issues)], limit=40)
        return genes

    @staticmethod
    def _compatibility_issues(gene: Mapping[str, Any]) -> list[str]:
        text_pre = "\n".join(_as_list(gene.get("preconditions"))).lower()
        constraints = gene.get("constraints") or {}
        raw = json.dumps(constraints, ensure_ascii=False, sort_keys=True, default=str).lower()
        issues: list[str] = []
        for token in ("network", "write", "delete", "promote", "external", "llm"):
            if (f"no_{token}" in raw or f"禁止{token}" in raw) and token in text_pre:
                issues.append(f"precondition_requires_forbidden_{token}")
        if "must_be_verified" in raw and "candidate" in text_pre:
            issues.append("candidate_precondition_conflicts_with_must_be_verified")
        if len(_as_list(gene.get("preconditions"))) > 40:
            issues.append("preconditions_too_complex")
        return issues

    # ── Stage 4: TRANSCEND ──────────────────────────────────────────────

    def _transcend(self, genes: list[dict[str, Any]]) -> list[str]:
        if not genes:
            return []
        con = self._connect()
        written: list[str] = []
        try:
            cols = self._columns(con)
            for gene in genes:
                if self._insert_candidate(con, cols, gene):
                    written.append(str(gene["id"]))
            con.commit()
            return written
        finally:
            con.close()

    def _insert_candidate(self, con: sqlite3.Connection, cols: set[str], gene: Mapping[str, Any]) -> bool:
        # Schema described in the task (id/category/signals/preconditions/...) and
        # the deployed GeneDB schema (gene_id/cycle_id/absorbed_knowledge/...) are
        # both supported.
        if "id" in cols:
            values: dict[str, Any] = {
                "id": gene["id"],
                "type": gene.get("type", "pgg_gene"),
                "category": gene.get("category"),
                "signals_match": json.dumps(gene.get("signals_match", []), ensure_ascii=False),
                "preconditions": json.dumps(gene.get("preconditions", []), ensure_ascii=False),
                "strategy": json.dumps(gene.get("strategy", []), ensure_ascii=False),
                "constraints": json.dumps(gene.get("constraints", {}), ensure_ascii=False),
                "validation": json.dumps(gene.get("validation", []), ensure_ascii=False),
                "status": "candidate",
                "fitness": float(gene.get("fitness") or 0),
                "last_executed": None,
                "created": gene.get("created") or _now(),
                "origin": "auto_fusion",
            }
            insert_cols = [c for c in values if c in cols]
            placeholders = ",".join("?" for _ in insert_cols)
            sql = f"INSERT OR IGNORE INTO evolution_genes({','.join(insert_cols)}) VALUES({placeholders})"
            cur = con.execute(sql, tuple(values[c] for c in insert_cols))
            return cur.rowcount > 0

        values = {
            "gene_id": gene["id"],
            "cycle_id": "PGG-DREAM-MODE-" + time.strftime("%Y%m%d"),
            "created_at": gene.get("created") or _now(),
            "defect_no": 48,
            "defect_name": "Dream Mode adversarial gene synthesis",
            "gene_name": gene["id"],
            "absorbed_knowledge": json.dumps(gene, ensure_ascii=False, sort_keys=True),
            "source_refs_json": json.dumps([{"origin": "auto_fusion", "parent_ids": gene.get("parent_ids", [])}], ensure_ascii=False),
            "repair_mechanism": "\n".join(_as_list(gene.get("strategy"))),
            "severity_rank": 1,
            "apex_variables": "Ω_self,Φ_dream_mode,EVM_simulation",
            "gate_type": "pgg_dream_mode_auto_fusion",
            "reusable_rule": "Dream Mode rule-based fusion; candidate only until independent verification",
            "status": "candidate",
            "evidence_grade": "B",
            "verification_status": "pending_review_dream_mode_simulated",
            "boundary": BOUNDARY,
            "gene_hash": gene.get("gene_hash") or _hash(gene),
            "fitness": int(round(float(gene.get("fitness") or 0))),
            "execution_count": 0,
            "last_executed": None,
        }
        insert_cols = [c for c in values if c in cols]
        placeholders = ",".join("?" for _ in insert_cols)
        sql = f"INSERT OR IGNORE INTO evolution_genes({','.join(insert_cols)}) VALUES({placeholders})"
        cur = con.execute(sql, tuple(values[c] for c in insert_cols))
        return cur.rowcount > 0

    def _write_log(self, result: Mapping[str, Any]) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        latest = self.log_dir / "latest.json"
        stamp = time.strftime("%Y%m%dT%H%M%S")
        run_log = self.log_dir / f"dream_mode_{stamp}.json"
        payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        latest.write_text(payload + "\n", encoding="utf-8")
        run_log.write_text(payload + "\n", encoding="utf-8")


__all__ = ["DreamEngine"]


if __name__ == "__main__":
    print(json.dumps(DreamEngine().run_full_cycle(), ensure_ascii=False, indent=2, sort_keys=True))
