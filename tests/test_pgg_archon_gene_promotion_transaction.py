from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from agent.pgg_archon_gene_promotion_transaction import main, write_promotion_transaction_result


def _db(tmp_path: Path, *, state: str = "candidate", promoted_at: str | None = None) -> Path:
    path = tmp_path / "pgg_archon.db"
    con = sqlite3.connect(path)
    con.execute(
        "create table gene_lifecycle(gene_id integer primary key, state text not null, activated_at text, promoted_at text, archived_at text, retired_at text, quality_score real, parent_gene_id integer, candidate_at text)"
    )
    con.execute(
        "create table promotion_chain(id integer primary key autoincrement, gene_id integer not null, from_state text not null, to_state text not null, transitioned_at text not null, trigger_phase text, decision text)"
    )
    con.execute(
        "insert into gene_lifecycle(gene_id,state,activated_at,promoted_at,archived_at,retired_at,quality_score,parent_gene_id,candidate_at) values (347,?,?,?,null,null,0.86,null,'2026-06-04T00:00:00Z')",
        (state, None, promoted_at),
    )
    if state == "promoted":
        con.execute(
            "insert into promotion_chain(gene_id,from_state,to_state,transitioned_at,trigger_phase,decision) values (347,'candidate','promoted',?,'seed',?)",
            (promoted_at or "2026-06-04T00:01:00Z", json.dumps({"seed": True})),
        )
    con.commit(); con.close()
    return path


def _summary(tmp_path: Path, *, passes: int = 2, decision: str = "PROCEED_PROMOTION_TRANSACTION") -> Path:
    path = tmp_path / "summary.json"
    results = [
        {"label": "gpt", "provider": "gpt55_5yuantoken", "status": "ok_visible", "classified_verdict": "PASS", "http_status": 200, "visible_output_chars": 100},
        {"label": "deepseek", "provider": "deepseek_v4_flash", "status": "ok_visible", "classified_verdict": "PASS" if passes >= 2 else "BLOCKED", "http_status": 200, "visible_output_chars": 100},
    ]
    path.write_text(json.dumps({"decision": decision, "visible_pass_count": passes, "visible_count": 2, "authorization": "unit-test", "results": results}), encoding="utf-8")
    return path


def _life(db: Path):
    con = sqlite3.connect(db)
    row = con.execute("select gene_id,state,promoted_at from gene_lifecycle where gene_id=347").fetchone()
    chain_count = con.execute("select count(*) from promotion_chain where gene_id=347").fetchone()[0]
    con.close()
    return row, chain_count


def test_promotion_transaction_promotes_candidate_and_writes_chain(tmp_path: Path) -> None:
    db = _db(tmp_path)
    result = write_promotion_transaction_result(
        db_path=db,
        gene_id=347,
        llm_summary_path=_summary(tmp_path),
        output_dir=tmp_path / "out",
    )
    assert result["status"] == "PROMOTED_VERIFIED"
    row, chain_count = _life(db)
    assert row[1] == "promoted"
    assert row[2]
    assert chain_count == 1
    payload = json.loads(Path(result["result"]).read_text(encoding="utf-8"))
    assert payload["promotion_chain"][2:4] == ["candidate", "promoted"]


def test_promotion_transaction_rejects_low_llm_pass_count(tmp_path: Path) -> None:
    db = _db(tmp_path)
    with pytest.raises(ValueError):
        write_promotion_transaction_result(
            db_path=db,
            gene_id=347,
            llm_summary_path=_summary(tmp_path, passes=1, decision="DO_NOT_PROMOTE"),
            output_dir=tmp_path / "out",
        )
    row, chain_count = _life(db)
    assert row[1] == "candidate"
    assert chain_count == 0


def test_promotion_transaction_is_idempotent_for_already_promoted(tmp_path: Path) -> None:
    db = _db(tmp_path, state="promoted", promoted_at="2026-06-04T00:01:00Z")
    result = write_promotion_transaction_result(
        db_path=db,
        gene_id=347,
        llm_summary_path=_summary(tmp_path),
        output_dir=tmp_path / "out",
    )
    assert result["status"] == "ALREADY_PROMOTED_VERIFIED"
    row, chain_count = _life(db)
    assert row[1] == "promoted"
    assert chain_count == 1


def test_main_dry_run_does_not_mutate_db(tmp_path: Path, capsys) -> None:
    db = _db(tmp_path)
    assert main([
        "--db", str(db),
        "--gene-id", "347",
        "--llm-summary", str(_summary(tmp_path)),
        "--output-dir", str(tmp_path / "out"),
        "--dry-run",
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "DRY_RUN_READY"
    row, chain_count = _life(db)
    assert row[1] == "candidate"
    assert chain_count == 0
