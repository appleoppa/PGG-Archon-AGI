from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from agent.pgg_archon_gene_lifecycle_transaction import main, write_lifecycle_transaction_result


def _db(tmp_path: Path, *, state: str = "candidate", retired_at: str | None = None) -> Path:
    path = tmp_path / "pgg_archon.db"
    con = sqlite3.connect(path)
    con.execute(
        "create table gene_lifecycle(gene_id integer primary key, state text not null, activated_at text, promoted_at text, archived_at text, retired_at text, quality_score real, parent_gene_id integer, candidate_at text)"
    )
    con.execute(
        "create table promotion_chain(id integer primary key autoincrement, gene_id integer not null, from_state text not null, to_state text not null, transitioned_at text not null, trigger_phase text, decision text)"
    )
    con.execute(
        "create table evolution_genes(id integer primary key autoincrement, gene_id integer not null, parent_gene_id integer, state text not null, generation integer default 0, mutation_vector text, fitness_before real, fitness_after real, promoted_at text, retired_at text, evidence_ref text, created_at text not null)"
    )
    con.execute(
        "insert into gene_lifecycle(gene_id,state,activated_at,promoted_at,archived_at,retired_at,quality_score,parent_gene_id,candidate_at) values (99,?,null,null,null,?,0.70,null,'2026-06-04T00:00:00Z')",
        (state, retired_at),
    )
    if state == "retired":
        con.execute(
            "insert into promotion_chain(gene_id,from_state,to_state,transitioned_at,trigger_phase,decision) values (99,'candidate','retired',?,'seed',?)",
            (retired_at or "2026-06-04T00:01:00Z", json.dumps({"seed": True})),
        )
    con.commit(); con.close()
    return path


def _life(db: Path):
    con = sqlite3.connect(db)
    row = con.execute("select gene_id,state,archived_at,retired_at from gene_lifecycle where gene_id=99").fetchone()
    chain_count = con.execute("select count(*) from promotion_chain where gene_id=99").fetchone()[0]
    evo_count = con.execute("select count(*) from evolution_genes where gene_id=99").fetchone()[0]
    con.close()
    return row, chain_count, evo_count


def test_lifecycle_transaction_retires_candidate_and_writes_chain_and_evolution_gene(tmp_path: Path) -> None:
    db = _db(tmp_path)
    result = write_lifecycle_transaction_result(
        db_path=db,
        gene_id=99,
        to_state="retired",
        reason="duplicate candidate",
        evidence_path=None,
        output_dir=tmp_path / "out",
    )
    assert result["status"] == "RETIRED_VERIFIED"
    row, chain_count, evo_count = _life(db)
    assert row[1] == "retired"
    assert row[3]
    assert chain_count == 1
    assert evo_count == 1
    payload = json.loads(Path(result["result"]).read_text(encoding="utf-8"))
    assert payload["chain"][2:4] == ["candidate", "retired"]
    assert "no deletion" in payload["boundary"].lower()


def test_lifecycle_transaction_archives_candidate(tmp_path: Path) -> None:
    db = _db(tmp_path)
    result = write_lifecycle_transaction_result(
        db_path=db,
        gene_id=99,
        to_state="archived",
        reason="needs historical archive",
        evidence_path=None,
        output_dir=tmp_path / "out",
    )
    assert result["status"] == "ARCHIVED_VERIFIED"
    row, chain_count, evo_count = _life(db)
    assert row[1] == "archived"
    assert row[2]
    assert chain_count == 1
    assert evo_count == 1


def test_lifecycle_transaction_dry_run_does_not_mutate(tmp_path: Path) -> None:
    db = _db(tmp_path)
    result = write_lifecycle_transaction_result(
        db_path=db,
        gene_id=99,
        to_state="retired",
        reason="duplicate candidate",
        evidence_path=None,
        output_dir=tmp_path / "out",
        dry_run=True,
    )
    assert result["status"] == "DRY_RUN_READY"
    row, chain_count, evo_count = _life(db)
    assert row[1] == "candidate"
    assert chain_count == 0
    assert evo_count == 0


def test_lifecycle_transaction_rejects_missing_reason(tmp_path: Path) -> None:
    db = _db(tmp_path)
    with pytest.raises(ValueError):
        write_lifecycle_transaction_result(
            db_path=db,
            gene_id=99,
            to_state="retired",
            reason=" ",
            evidence_path=None,
            output_dir=tmp_path / "out",
        )


def test_lifecycle_transaction_idempotent_for_already_retired(tmp_path: Path) -> None:
    db = _db(tmp_path, state="retired", retired_at="2026-06-04T00:01:00Z")
    result = write_lifecycle_transaction_result(
        db_path=db,
        gene_id=99,
        to_state="retired",
        reason="duplicate candidate",
        evidence_path=None,
        output_dir=tmp_path / "out",
    )
    assert result["status"] == "ALREADY_IN_TARGET_STATE_VERIFIED"
    row, chain_count, evo_count = _life(db)
    assert row[1] == "retired"
    assert chain_count == 1
    assert evo_count == 0


def test_main_writes_lifecycle_result(tmp_path: Path, capsys) -> None:
    db = _db(tmp_path)
    assert main([
        "--db", str(db),
        "--gene-id", "99",
        "--to-state", "retired",
        "--reason", "duplicate candidate",
        "--output-dir", str(tmp_path / "out"),
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "RETIRED_VERIFIED"
    assert Path(printed["result"]).is_file()
