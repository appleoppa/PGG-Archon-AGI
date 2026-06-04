"""PGG Archon bounded GeneDB promotion transaction.

Boundary: promotes exactly one GeneDB lifecycle row from candidate to promoted
under explicit multi-LLM evidence and transactional readback checks. It does not
claim AGI, modify code, or promote unrelated genes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class PromotionTransactionResult:
    schema: str
    status: str
    gene_id: int
    promoted_at: str | None
    backup: str
    db: str
    before: list[Any] | None
    after: list[Any] | None
    promotion_chain: list[Any] | None
    promotion_chain_decision_sha256: str | None
    llm_summary: str
    db_sha256: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _validate_llm_summary(summary: dict[str, Any], min_visible_pass_count: int) -> None:
    if summary.get("decision") != "PROCEED_PROMOTION_TRANSACTION":
        raise ValueError(f"LLM decision does not allow promotion: {summary.get('decision')}")
    if int(summary.get("visible_pass_count") or 0) < min_visible_pass_count:
        raise ValueError(
            f"visible_pass_count below threshold: {summary.get('visible_pass_count')} < {min_visible_pass_count}"
        )


def _backup_db(db_path: Path, output_dir: Path, gene_id: int, timestamp: str) -> Path:
    safe_ts = timestamp.replace(":", "-")
    backup = output_dir / f"pgg_archon.db.bak-promote-{gene_id}-{safe_ts}"
    shutil.copy2(db_path, backup)
    return backup


def promote_gene_transaction(
    *,
    db_path: str | Path,
    gene_id: int,
    llm_summary_path: str | Path,
    output_dir: str | Path,
    min_visible_pass_count: int = 2,
    trigger_phase: str = "available_llm_promotion_feasibility_b",
    patch_commit: str = "13986d7fe",
    promotion_gate_commit: str = "9e75f8a13",
    dry_run: bool = False,
) -> PromotionTransactionResult:
    db = Path(db_path).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    llm_path = Path(llm_summary_path).expanduser().resolve()
    llm_summary = _read_json(llm_path)
    _validate_llm_summary(llm_summary, min_visible_pass_count)
    now = datetime.now(timezone.utc).isoformat()
    backup = _backup_db(db, out, gene_id, now)
    before = after = chain = None
    chain_hash = None

    con = sqlite3.connect(db)
    con.isolation_level = None
    cur = con.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        before_row = cur.execute(
            "select gene_id,state,activated_at,promoted_at,archived_at,retired_at,quality_score,parent_gene_id,candidate_at "
            "from gene_lifecycle where gene_id=?",
            (gene_id,),
        ).fetchone()
        if before_row is None:
            raise RuntimeError("gene_lifecycle row missing")
        before = list(before_row)
        if before_row[1] == "promoted" and before_row[3]:
            # Idempotent verified readback path: do not add duplicate chain rows.
            after = list(before_row)
            latest_chain = cur.execute(
                "select id,gene_id,from_state,to_state,transitioned_at,trigger_phase,decision "
                "from promotion_chain where gene_id=? order by id desc limit 1",
                (gene_id,),
            ).fetchone()
            chain = list(latest_chain[:6]) if latest_chain else None
            chain_hash = hashlib.sha256(str(latest_chain[6] if latest_chain else "").encode()).hexdigest() if latest_chain else None
            con.rollback()
            return PromotionTransactionResult(
                schema="PGGArchonPromotionTransactionResult/v1",
                status="ALREADY_PROMOTED_VERIFIED",
                gene_id=gene_id,
                promoted_at=before_row[3],
                backup=str(backup),
                db=str(db),
                before=before,
                after=after,
                promotion_chain=chain,
                promotion_chain_decision_sha256=chain_hash,
                llm_summary=str(llm_path),
                db_sha256=hashlib.sha256(db.read_bytes()).hexdigest(),
                boundary="Idempotent readback only; no duplicate promotion mutation, no full AGI claim.",
            )
        if before_row[1] != "candidate":
            raise RuntimeError(f"gene not candidate before promotion: {before_row[1]}")
        if before_row[3] is not None:
            raise RuntimeError("gene already has promoted_at")
        decision = json.dumps(
            {
                "schema": "PGGArchonPromotionDecision/v1",
                "visible_pass_count": llm_summary.get("visible_pass_count"),
                "visible_count": llm_summary.get("visible_count"),
                "authorization": llm_summary.get("authorization"),
                "models": [
                    {
                        "label": r.get("label"),
                        "provider": r.get("provider"),
                        "status": r.get("status"),
                        "verdict": r.get("classified_verdict"),
                        "http_status": r.get("http_status"),
                        "visible_output_chars": r.get("visible_output_chars"),
                    }
                    for r in llm_summary.get("results", [])
                ],
                "commits": {"main_patch": patch_commit, "promotion_gate": promotion_gate_commit},
                "boundary": "bounded GeneDB lifecycle promotion only; no full AGI claim",
            },
            ensure_ascii=False,
        )
        if dry_run:
            con.rollback()
            return PromotionTransactionResult(
                schema="PGGArchonPromotionTransactionResult/v1",
                status="DRY_RUN_READY",
                gene_id=gene_id,
                promoted_at=None,
                backup=str(backup),
                db=str(db),
                before=before,
                after=None,
                promotion_chain=None,
                promotion_chain_decision_sha256=hashlib.sha256(decision.encode()).hexdigest(),
                llm_summary=str(llm_path),
                db_sha256=hashlib.sha256(db.read_bytes()).hexdigest(),
                boundary="Dry-run only; no GeneDB mutation, no full AGI claim.",
            )
        cur.execute(
            "update gene_lifecycle set state='promoted', promoted_at=?, quality_score=coalesce(quality_score, ?) "
            "where gene_id=? and state='candidate' and promoted_at is null",
            (now, 0.86, gene_id),
        )
        if cur.rowcount != 1:
            raise RuntimeError(f"conditional lifecycle update rowcount={cur.rowcount}")
        cur.execute(
            "insert into promotion_chain(gene_id,from_state,to_state,transitioned_at,trigger_phase,decision) "
            "values (?,?,?,?,?,?)",
            (gene_id, "candidate", "promoted", now, trigger_phase, decision),
        )
        chain_id = cur.lastrowid
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS evolution_genes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gene_id INTEGER NOT NULL,
                parent_gene_id INTEGER,
                state TEXT NOT NULL,
                generation INTEGER DEFAULT 0,
                mutation_vector TEXT,
                fitness_before REAL,
                fitness_after REAL,
                promoted_at TEXT,
                retired_at TEXT,
                evidence_ref TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (gene_id) REFERENCES genes(id)
            )
            """
        )
        cur.execute(
            """
            insert into evolution_genes(
                gene_id,parent_gene_id,state,generation,mutation_vector,fitness_before,fitness_after,
                promoted_at,retired_at,evidence_ref,created_at
            ) values (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                gene_id,
                before_row[7],
                "promoted",
                0,
                "promotion_transaction",
                before_row[6],
                before_row[6] if before_row[6] is not None else 0.86,
                now,
                None,
                decision,
                now,
            ),
        )
        after_row = cur.execute(
            "select gene_id,state,activated_at,promoted_at,archived_at,retired_at,quality_score,parent_gene_id,candidate_at "
            "from gene_lifecycle where gene_id=?",
            (gene_id,),
        ).fetchone()
        chain_row = cur.execute(
            "select id,gene_id,from_state,to_state,transitioned_at,trigger_phase,decision from promotion_chain where id=?",
            (chain_id,),
        ).fetchone()
        if after_row[1] != "promoted" or after_row[3] != now:
            raise RuntimeError(f"readback mismatch: {after_row}")
        if chain_row[1] != gene_id or chain_row[2] != "candidate" or chain_row[3] != "promoted":
            raise RuntimeError(f"promotion_chain mismatch: {chain_row}")
        con.commit()
        after = list(after_row)
        chain = list(chain_row[:6])
        chain_hash = hashlib.sha256(str(chain_row[6]).encode()).hexdigest()
        status = "PROMOTED_VERIFIED"
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    return PromotionTransactionResult(
        schema="PGGArchonPromotionTransactionResult/v1",
        status=status,
        gene_id=gene_id,
        promoted_at=after[3] if after else None,
        backup=str(backup),
        db=str(db),
        before=before,
        after=after,
        promotion_chain=chain,
        promotion_chain_decision_sha256=chain_hash,
        llm_summary=str(llm_path),
        db_sha256=hashlib.sha256(db.read_bytes()).hexdigest(),
        boundary="GeneDB lifecycle promotion only; no code change, no full AGI claim.",
    )


def write_promotion_transaction_result(**kwargs: Any) -> dict[str, Any]:
    result = promote_gene_transaction(**kwargs)
    out = Path(kwargs["output_dir"]).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "promotion_transaction_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "gene_id": result.gene_id, "promoted_at": result.promoted_at}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded audited GeneDB promotion transaction.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--gene-id", type=int, required=True)
    parser.add_argument("--llm-summary", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--min-visible-pass-count", type=int, default=2)
    parser.add_argument("--trigger-phase", default="available_llm_promotion_feasibility_b")
    parser.add_argument("--patch-commit", default="13986d7fe")
    parser.add_argument("--promotion-gate-commit", default="9e75f8a13")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_promotion_transaction_result(
        db_path=args.db,
        gene_id=args.gene_id,
        llm_summary_path=args.llm_summary,
        output_dir=args.output_dir,
        min_visible_pass_count=args.min_visible_pass_count,
        trigger_phase=args.trigger_phase,
        patch_commit=args.patch_commit,
        promotion_gate_commit=args.promotion_gate_commit,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
