"""Bounded PGG Archon GeneDB lifecycle transition transaction.

Supports non-promotion lifecycle cleanup such as retiring duplicate/low-score
candidates. It updates exactly one gene_lifecycle row, inserts one
promotion_chain audit row, backs up the DB, and reads back the mutation.

Boundary: GeneDB lifecycle metadata only; no code execution, no deletion, no
full AGI/external benchmark/legal correctness claim.
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

_ALLOWED_TO_STATES = {"retired", "archived"}


@dataclass(frozen=True)
class LifecycleTransactionResult:
    schema: str
    status: str
    gene_id: int
    to_state: str
    transitioned_at: str | None
    backup: str
    db: str
    before: list[Any] | None
    after: list[Any] | None
    chain: list[Any] | None
    chain_decision_sha256: str | None
    db_sha256: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _backup_db(db_path: Path, output_dir: Path, gene_id: int, to_state: str, timestamp: str) -> Path:
    safe_ts = timestamp.replace(":", "-")
    backup = output_dir / f"pgg_archon.db.bak-{to_state}-{gene_id}-{safe_ts}"
    shutil.copy2(db_path, backup)
    return backup


def transition_gene_lifecycle(
    *,
    db_path: str | Path,
    gene_id: int,
    to_state: str,
    reason: str,
    evidence_path: str | Path | None,
    output_dir: str | Path,
    trigger_phase: str = "bounded_lifecycle_cleanup",
    dry_run: bool = False,
) -> LifecycleTransactionResult:
    if to_state not in _ALLOWED_TO_STATES:
        raise ValueError(f"unsupported to_state: {to_state}")
    if not reason.strip():
        raise ValueError("reason is required")
    db = Path(db_path).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    backup = _backup_db(db, out, gene_id, to_state, now)
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
        from_state = str(before_row[1])
        if from_state == to_state:
            latest_chain = cur.execute(
                "select id,gene_id,from_state,to_state,transitioned_at,trigger_phase,decision "
                "from promotion_chain where gene_id=? and to_state=? order by id desc limit 1",
                (gene_id, to_state),
            ).fetchone()
            chain = list(latest_chain[:6]) if latest_chain else None
            chain_hash = hashlib.sha256(str(latest_chain[6] if latest_chain else "").encode()).hexdigest() if latest_chain else None
            con.rollback()
            return LifecycleTransactionResult(
                schema="PGGArchonLifecycleTransactionResult/v1",
                status="ALREADY_IN_TARGET_STATE_VERIFIED",
                gene_id=gene_id,
                to_state=to_state,
                transitioned_at=before_row[5] if to_state == "retired" else before_row[4],
                backup=str(backup),
                db=str(db),
                before=before,
                after=before,
                chain=chain,
                chain_decision_sha256=chain_hash,
                db_sha256=hashlib.sha256(db.read_bytes()).hexdigest(),
                boundary="Idempotent readback only; no duplicate lifecycle mutation, no deletion.",
            )
        if from_state not in {"candidate", "promoted", "active"}:
            raise RuntimeError(f"unsupported from_state for cleanup: {from_state}")
        decision = json.dumps(
            {
                "schema": "PGGArchonLifecycleDecision/v1",
                "gene_id": gene_id,
                "from_state": from_state,
                "to_state": to_state,
                "reason": reason,
                "evidence_path": str(Path(evidence_path).expanduser()) if evidence_path else None,
                "boundary": "lifecycle metadata cleanup only; no deletion; no capability claim",
            },
            ensure_ascii=False,
        )
        if dry_run:
            con.rollback()
            return LifecycleTransactionResult(
                schema="PGGArchonLifecycleTransactionResult/v1",
                status="DRY_RUN_READY",
                gene_id=gene_id,
                to_state=to_state,
                transitioned_at=None,
                backup=str(backup),
                db=str(db),
                before=before,
                after=None,
                chain=None,
                chain_decision_sha256=hashlib.sha256(decision.encode()).hexdigest(),
                db_sha256=hashlib.sha256(db.read_bytes()).hexdigest(),
                boundary="Dry-run only; no GeneDB mutation, no deletion.",
            )
        timestamp_col = "retired_at" if to_state == "retired" else "archived_at"
        cur.execute(
            f"update gene_lifecycle set state=?, {timestamp_col}=? where gene_id=? and state=?",
            (to_state, now, gene_id, from_state),
        )
        if cur.rowcount != 1:
            raise RuntimeError(f"conditional lifecycle update rowcount={cur.rowcount}")
        cur.execute(
            "insert into promotion_chain(gene_id,from_state,to_state,transitioned_at,trigger_phase,decision) values (?,?,?,?,?,?)",
            (gene_id, from_state, to_state, now, trigger_phase, decision),
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
                to_state,
                0,
                f"lifecycle_{from_state}_to_{to_state}",
                before_row[6],
                before_row[6],
                before_row[3] if to_state != "promoted" else now,
                now if to_state == "retired" else before_row[5],
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
        expected_ts = after_row[5] if to_state == "retired" else after_row[4]
        if after_row[1] != to_state or expected_ts != now:
            raise RuntimeError(f"readback mismatch: {after_row}")
        if chain_row[1] != gene_id or chain_row[2] != from_state or chain_row[3] != to_state:
            raise RuntimeError(f"chain mismatch: {chain_row}")
        con.commit()
        after = list(after_row)
        chain = list(chain_row[:6])
        chain_hash = hashlib.sha256(str(chain_row[6]).encode()).hexdigest()
        status = f"{to_state.upper()}_VERIFIED"
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return LifecycleTransactionResult(
        schema="PGGArchonLifecycleTransactionResult/v1",
        status=status,
        gene_id=gene_id,
        to_state=to_state,
        transitioned_at=after[5] if to_state == "retired" else after[4],
        backup=str(backup),
        db=str(db),
        before=before,
        after=after,
        chain=chain,
        chain_decision_sha256=chain_hash,
        db_sha256=hashlib.sha256(db.read_bytes()).hexdigest(),
        boundary="GeneDB lifecycle metadata transition only; no deletion, no full AGI claim.",
    )


def write_lifecycle_transaction_result(**kwargs: Any) -> dict[str, Any]:
    result = transition_gene_lifecycle(**kwargs)
    out = Path(kwargs["output_dir"]).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "lifecycle_transaction_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "gene_id": result.gene_id, "to_state": result.to_state}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded audited GeneDB lifecycle transition transaction.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--gene-id", type=int, required=True)
    parser.add_argument("--to-state", choices=sorted(_ALLOWED_TO_STATES), required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--evidence")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--trigger-phase", default="bounded_lifecycle_cleanup")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_lifecycle_transaction_result(
        db_path=args.db,
        gene_id=args.gene_id,
        to_state=args.to_state,
        reason=args.reason,
        evidence_path=args.evidence,
        output_dir=args.output_dir,
        trigger_phase=args.trigger_phase,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
