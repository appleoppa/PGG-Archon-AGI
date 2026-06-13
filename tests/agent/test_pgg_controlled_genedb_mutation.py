import json
import sqlite3
from pathlib import Path

from agent.pgg_controlled_genedb_mutation import apply_controlled_mutation


def _make_db(path: Path):
    con = sqlite3.connect(path)
    con.execute(
        """CREATE TABLE evolution_genes(
        gene_id TEXT PRIMARY KEY,
        status TEXT,
        evidence_grade TEXT,
        verification_status TEXT,
        boundary TEXT,
        fitness INTEGER,
        source_refs_json TEXT
        )"""
    )
    con.execute(
        "INSERT INTO evolution_genes VALUES(?,?,?,?,?,?,?)",
        ("pass_gene", "candidate", "B", "pending", "old_boundary", 770, "{}"),
    )
    con.execute(
        "INSERT INTO evolution_genes VALUES(?,?,?,?,?,?,?)",
        ("missing_gene", "candidate", "B", "pending", "old_boundary", 770, "{}"),
    )
    con.commit()
    con.close()


def test_apply_controlled_mutation_promotes_pass_and_blocks_missing_with_backup(tmp_path):
    db = tmp_path / "genes.sqlite3"
    _make_db(db)
    proposal = tmp_path / "controlled_promotion_proposal.json"
    proposal.write_text(json.dumps([
        {"capability_id": "pass_gene", "task_id": "task-pass", "verdict": "PASS_CONTROLLED_PROMOTION_PROPOSAL"}
    ]), encoding="utf-8")
    results = tmp_path / "completion_results.json"
    results.write_text(json.dumps([
        {"capability_id": "pass_gene", "task_id": "task-pass", "verdict": "PASS_CONTROLLED_PROMOTION_PROPOSAL"},
        {"capability_id": "missing_gene", "task_id": "task-missing", "verdict": "BLOCKED_SOURCE_MISSING"},
    ]), encoding="utf-8")

    summary = apply_controlled_mutation(db, proposal, results, tmp_path / "out", execute=True)

    assert summary["db_mutation"] is True
    assert summary["promoted_count"] == 1
    assert summary["source_missing_marked_count"] == 1
    assert Path(summary["backup_path"]).exists()
    con = sqlite3.connect(db)
    pass_row = con.execute("SELECT status,evidence_grade,verification_status FROM evolution_genes WHERE gene_id='pass_gene'").fetchone()
    missing_row = con.execute("SELECT status,evidence_grade,verification_status FROM evolution_genes WHERE gene_id='missing_gene'").fetchone()
    con.close()
    assert pass_row[0] == "verified"
    assert pass_row[1] == "A (proof packet)"
    assert "controlled_promotion_phase4" in pass_row[2]
    assert missing_row[0] == "blocked"
    assert missing_row[1] == "D (source missing)"
    assert "blocked_source_missing_phase4" in missing_row[2]


def test_apply_controlled_mutation_dry_run_does_not_change_db(tmp_path):
    db = tmp_path / "genes.sqlite3"
    _make_db(db)
    proposal = tmp_path / "controlled_promotion_proposal.json"
    proposal.write_text(json.dumps([
        {"capability_id": "pass_gene", "task_id": "task-pass", "verdict": "PASS_CONTROLLED_PROMOTION_PROPOSAL"}
    ]), encoding="utf-8")
    results = tmp_path / "completion_results.json"
    results.write_text(json.dumps([
        {"capability_id": "missing_gene", "task_id": "task-missing", "verdict": "BLOCKED_SOURCE_MISSING"}
    ]), encoding="utf-8")

    summary = apply_controlled_mutation(db, proposal, results, tmp_path / "out", execute=False)

    assert summary["db_mutation"] is False
    con = sqlite3.connect(db)
    rows = con.execute("SELECT gene_id,status,evidence_grade,verification_status FROM evolution_genes ORDER BY gene_id").fetchall()
    con.close()
    assert rows == [
        ("missing_gene", "candidate", "B", "pending"),
        ("pass_gene", "candidate", "B", "pending"),
    ]
