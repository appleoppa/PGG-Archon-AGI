from __future__ import annotations

import sqlite3
from pathlib import Path

from agent.pgg_archon_gene_fusion_engine import (
    fuse_genedb_records,
    fuse_standard_genes,
    insert_fused_gene,
    validate_standard_gene,
)


def standard_gene(gid: str, fitness: int = 850):
    return {
        "type": "pgg_gene",
        "id": gid,
        "category": "test",
        "signals_match": ["signal"],
        "preconditions": ["pre"],
        "strategy": ["step1", "step2"],
        "constraints": {"boundary": "test"},
        "validation": ["pytest"],
        "fitness": fitness,
    }


def make_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE evolution_cycles(cycle_id TEXT PRIMARY KEY,created_at TEXT NOT NULL,theme TEXT NOT NULL,sequence_logic TEXT NOT NULL,status TEXT NOT NULL,evidence_grade TEXT NOT NULL,boundary TEXT NOT NULL);
        CREATE TABLE evolution_genes(gene_id TEXT PRIMARY KEY,cycle_id TEXT NOT NULL,created_at TEXT NOT NULL,defect_no INTEGER NOT NULL,defect_name TEXT NOT NULL,gene_name TEXT NOT NULL,absorbed_knowledge TEXT NOT NULL,source_refs_json TEXT NOT NULL,repair_mechanism TEXT NOT NULL,severity_rank INTEGER NOT NULL,apex_variables TEXT NOT NULL,gate_type TEXT NOT NULL,reusable_rule TEXT NOT NULL,status TEXT NOT NULL,evidence_grade TEXT NOT NULL,verification_status TEXT NOT NULL,boundary TEXT NOT NULL,gene_hash TEXT NOT NULL);
        """
    )
    con.execute("INSERT INTO evolution_cycles VALUES(?,?,?,?,?,?,?)", ("c", "now", "theme", "12534", "verified", "A", "boundary"))
    rows = [
        ("g1", "c", "now", 1, "defect", "gene1", "knowledge", "[]", "repair1", 1, "apex", "gate", "rule1", "verified", "A", "verified", "boundary", "h1"),
        ("g2", "c", "now", 1, "defect", "gene2", "knowledge", "[]", "repair2", 1, "apex", "gate", "rule2", "verified", "A", "verified", "boundary", "h2"),
    ]
    con.executemany("INSERT INTO evolution_genes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit(); con.close()


def test_standard_gene_template_validation_blocks_bad_shape():
    assert validate_standard_gene(standard_gene("g"))["status"] == "PASS"
    bad = {"id": "x"}
    out = validate_standard_gene(bad)
    assert out["status"] == "BLOCK"
    assert "invalid_type" in out["errors"]


def test_fuse_standard_genes_positive_synergy():
    out = fuse_standard_genes([standard_gene("a", 800), standard_gene("b", 805)])
    assert out["status"] == "PASS"
    assert out["offspring_gene"]["type"] == "pgg_gene"
    assert out["offspring_gene"]["synergy"] > 0
    assert out["offspring_gene"]["parent_ids"] == ["a", "b"]


def test_insert_fused_gene_dry_run_and_write(tmp_path: Path):
    db = tmp_path / "genes.sqlite3"
    make_db(db)
    gene = fuse_standard_genes([standard_gene("a", 800), standard_gene("b", 805)])["offspring_gene"]
    assert insert_fused_gene(gene, db_path=db)["status"] == "DRY_RUN"
    out = insert_fused_gene(gene, db_path=db, write=True, promote=True)
    assert out["status"] == "PASS"
    assert out["db_status"] == "verified"
    con = sqlite3.connect(db)
    assert con.execute("select count(*) from evolution_genes where gene_id=?", (gene["id"],)).fetchone()[0] == 1
    con.close()


def test_fuse_genedb_records_reads_and_inserts(tmp_path: Path):
    db = tmp_path / "genes.sqlite3"
    make_db(db)
    dry = fuse_genedb_records(["g1", "g2"], db_path=db)
    assert dry["records_found"] == 2
    assert dry["fusion"]["status"] == "PASS"
    written = fuse_genedb_records(["g1", "g2"], db_path=db, write=True, promote=False)
    assert written["insert"]["written"] is True
