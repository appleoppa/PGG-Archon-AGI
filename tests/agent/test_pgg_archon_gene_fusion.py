"""Tests for PGG Archon gene fusion surface."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agent.pgg_archon_gene_fusion import (
    FUSION_GATE_TYPE,
    FUSION_STATUS,
    FUSION_VERIFICATION,
    SUPERSEDED_STATUS,
    build_pgg_archon_gene_fusion_surface,
)


def _create_gene_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE evolution_cycles(cycle_id TEXT PRIMARY KEY,created_at TEXT NOT NULL,theme TEXT NOT NULL,sequence_logic TEXT NOT NULL,status TEXT NOT NULL,evidence_grade TEXT NOT NULL,boundary TEXT NOT NULL);
        CREATE TABLE evolution_genes(gene_id TEXT PRIMARY KEY,cycle_id TEXT NOT NULL,created_at TEXT NOT NULL,defect_no INTEGER NOT NULL,defect_name TEXT NOT NULL,gene_name TEXT NOT NULL,absorbed_knowledge TEXT NOT NULL,source_refs_json TEXT NOT NULL,repair_mechanism TEXT NOT NULL,severity_rank INTEGER NOT NULL,apex_variables TEXT NOT NULL,gate_type TEXT NOT NULL,reusable_rule TEXT NOT NULL,status TEXT NOT NULL,evidence_grade TEXT NOT NULL,verification_status TEXT NOT NULL,boundary TEXT NOT NULL,gene_hash TEXT NOT NULL,FOREIGN KEY(cycle_id) REFERENCES evolution_cycles(cycle_id));
        CREATE TABLE gene_source_map(gene_id TEXT NOT NULL,source_id TEXT NOT NULL,PRIMARY KEY(gene_id, source_id));
        """
    )
    con.execute(
        "INSERT INTO evolution_cycles VALUES(?, ?, ?, ?, ?, ?, ?)",
        ("c1", "2026-05-29T00:00:00+0800", "test", "12534", "active", "A-: test", "test boundary"),
    )
    con.commit()
    con.close()


def _insert_gene(
    db: Path,
    *,
    gene_id: str,
    defect_no: int,
    defect_name: str,
    absorbed: str = "knowledge",
    repair: str = "repair",
    rule: str = "rule",
    refs: str = "[]",
    status: str = "active",
    evidence: str = "A-: deterministic",
    verification: str = "verified_by_test",
    gate_type: str = "test_gate",
    severity: int = 2,
) -> None:
    con = sqlite3.connect(db)
    con.execute(
        """
        INSERT INTO evolution_genes
        (gene_id, cycle_id, created_at, defect_no, defect_name, gene_name,
         absorbed_knowledge, source_refs_json, repair_mechanism, severity_rank,
         apex_variables, gate_type, reusable_rule, status, evidence_grade,
         verification_status, boundary, gene_hash)
        VALUES (?, 'c1', '2026-05-29T00:00:00+0800', ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, 'test', ?)
        """,
        (
            gene_id,
            defect_no,
            defect_name,
            f"name-{gene_id}",
            absorbed,
            refs,
            repair,
            severity,
            gate_type,
            rule,
            status,
            evidence,
            verification,
            f"hash-{gene_id}",
        ),
    )
    con.commit()
    con.close()


def test_disabled_returns_short_circuit(tmp_path: Path) -> None:
    db = tmp_path / "g.db"
    _create_gene_db(db)
    out = build_pgg_archon_gene_fusion_surface(
        db_path=db, write=True, enabled=False, audit_dir=tmp_path / "audit"
    )
    assert out["status"] == "DISABLED"
    assert out["fusion_candidates"] == []
    assert out["fusion_records_written"] == 0
    assert out["agi_completion_claim"] is False


def test_block_when_db_missing(tmp_path: Path) -> None:
    out = build_pgg_archon_gene_fusion_surface(
        db_path=tmp_path / "missing.db", write=False, audit_dir=tmp_path / "audit"
    )
    assert out["status"] == "BLOCK"
    assert out["error"] == "gene_db_missing"


def test_dry_run_finds_groups_without_writing(tmp_path: Path) -> None:
    db = tmp_path / "g.db"
    _create_gene_db(db)
    _insert_gene(db, gene_id="A1", defect_no=10, defect_name="topic-x", absorbed="alpha", repair="r1", rule="rule-1")
    _insert_gene(db, gene_id="A2", defect_no=10, defect_name="topic-x", absorbed="beta", repair="r2", rule="rule-2")
    _insert_gene(db, gene_id="B1", defect_no=11, defect_name="topic-y")
    out = build_pgg_archon_gene_fusion_surface(
        db_path=db, write=False, audit_dir=tmp_path / "audit", min_member_count=2
    )
    assert out["status"] == "PASS"
    assert out["fusion_records_written"] == 0
    cands = out["fusion_candidates"]
    assert len(cands) == 1
    cand = cands[0]
    assert cand["defect_no"] == 10
    assert cand["member_count"] == 2
    assert cand["written"] is False
    con = sqlite3.connect(db)
    rows = con.execute("SELECT gene_id, status FROM evolution_genes ORDER BY gene_id").fetchall()
    con.close()
    statuses = {gid: status for gid, status in rows}
    assert statuses["A1"] == "active"
    assert statuses["A2"] == "active"


def test_write_inserts_fusion_and_supersedes_members(tmp_path: Path) -> None:
    db = tmp_path / "g.db"
    _create_gene_db(db)
    _insert_gene(db, gene_id="A1", defect_no=10, defect_name="topic-x", absorbed="alpha\nfact-1", evidence="A: high")
    _insert_gene(db, gene_id="A2", defect_no=10, defect_name="topic-x", absorbed="beta", evidence="A-: lower")
    out = build_pgg_archon_gene_fusion_surface(
        db_path=db, write=True, audit_dir=tmp_path / "audit", min_member_count=2
    )
    assert out["status"] == "PASS"
    assert out["fusion_records_written"] == 1
    cand = out["fusion_candidates"][0]
    fusion_id = cand["fusion_gene_id"]
    con = sqlite3.connect(db)
    fusion_row = con.execute(
        "SELECT gene_id, status, verification_status, gate_type, evidence_grade, severity_rank FROM evolution_genes WHERE gene_id = ?",
        (fusion_id,),
    ).fetchone()
    member_statuses = {
        gid: status
        for gid, status in con.execute(
            "SELECT gene_id, status FROM evolution_genes WHERE gene_id IN ('A1', 'A2')"
        ).fetchall()
    }
    map_rows = con.execute(
        "SELECT gene_id, source_id FROM gene_source_map ORDER BY source_id"
    ).fetchall()
    con.close()
    assert fusion_row is not None
    assert fusion_row[1] == FUSION_STATUS
    assert fusion_row[2] == FUSION_VERIFICATION
    assert fusion_row[3] == FUSION_GATE_TYPE
    assert fusion_row[4].startswith("A:")
    assert member_statuses["A1"] == SUPERSEDED_STATUS
    assert member_statuses["A2"] == SUPERSEDED_STATUS
    assert {row[1] for row in map_rows} == {"A1", "A2"}


def test_write_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "g.db"
    _create_gene_db(db)
    _insert_gene(db, gene_id="A1", defect_no=10, defect_name="topic-x")
    _insert_gene(db, gene_id="A2", defect_no=10, defect_name="topic-x")
    first = build_pgg_archon_gene_fusion_surface(
        db_path=db, write=True, audit_dir=tmp_path / "audit", min_member_count=2
    )
    second = build_pgg_archon_gene_fusion_surface(
        db_path=db, write=True, audit_dir=tmp_path / "audit", min_member_count=2
    )
    assert first["fusion_records_written"] == 1
    assert second["fusion_records_written"] == 0
    # the candidate count drops because members got marked superseded
    assert second["status"] == "WATCH"


def test_does_not_refuse_existing_fusion_outputs(tmp_path: Path) -> None:
    db = tmp_path / "g.db"
    _create_gene_db(db)
    _insert_gene(db, gene_id="F1", defect_no=20, defect_name="topic-z", gate_type=FUSION_GATE_TYPE)
    _insert_gene(db, gene_id="F2", defect_no=20, defect_name="topic-z", gate_type=FUSION_GATE_TYPE)
    out = build_pgg_archon_gene_fusion_surface(
        db_path=db, write=True, audit_dir=tmp_path / "audit", min_member_count=2
    )
    assert out["status"] == "WATCH"
    assert out["fusion_records_written"] == 0
