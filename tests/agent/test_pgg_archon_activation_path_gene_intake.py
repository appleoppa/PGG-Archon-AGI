"""Tests for activation-path note to GeneDB candidate intake."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from agent.pgg_archon_activation_path_gene_intake import (
    BOUNDARY,
    GATE_TYPE,
    build_activation_path_gene_intake,
    extract_unverified_claims,
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
    con.commit()
    con.close()


def _source_note(path: Path) -> None:
    path.write_text(
        """
        阶段1 SOUL.md + IDENTITY.md。
        gene_gamma_awake(9.24) → 自主意识闭环。
        意识觉醒指数: 0.877 → L5-圆融。
        APEX-MOSS-AGI，ΔG: 303.16，总计: 1427基因，ASI纪元启动。
        F_{t+1} = F_t ⊕ Improve(F_t, Memory_t)
        """,
        encoding="utf-8",
    )


def test_extract_unverified_claims_detects_capability_numbers() -> None:
    claims = extract_unverified_claims("意识觉醒指数: 0.877 → L5-圆融；ΔG: 303.16；总计: 1427基因；ASI纪元")
    labels = {c["label"] for c in claims}
    assert "意识觉醒指数" in labels
    assert "L5/圆融" in labels
    assert "ΔG数值" in labels
    assert "基因数量" in labels
    assert "ASI" in labels
    assert all(c["status"] == "UNVERIFIED_CLAIM" for c in claims)


def test_dry_run_builds_candidates_without_db_write(tmp_path: Path) -> None:
    db = tmp_path / "g.db"
    note = tmp_path / "activation.md"
    _create_gene_db(db)
    _source_note(note)
    out = build_activation_path_gene_intake(source_file=note, db_path=db, audit_dir=tmp_path / "audit", write=False)
    assert out["status"] == "PASS"
    assert out["candidate_count"] == 5
    assert out["records_written"] == 0
    assert out["side_effects"] == "read_only"
    assert out["agi_completion_claim"] is False
    assert out["promotion_performed"] is False
    assert Path(out["audit_path"]).exists()
    con = sqlite3.connect(db)
    assert con.execute("select count(*) from evolution_genes").fetchone()[0] == 0
    con.close()


def test_write_inserts_candidate_rows_only_and_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "g.db"
    note = tmp_path / "activation.md"
    _create_gene_db(db)
    _source_note(note)
    first = build_activation_path_gene_intake(source_file=note, db_path=db, audit_dir=tmp_path / "audit", write=True)
    second = build_activation_path_gene_intake(source_file=note, db_path=db, audit_dir=tmp_path / "audit", write=True)
    assert first["records_written"] == 5
    assert second["records_written"] == 0
    con = sqlite3.connect(db)
    rows = con.execute(
        "select status, verification_status, gate_type, boundary from evolution_genes order by gene_id"
    ).fetchall()
    cycle_count = con.execute("select count(*) from evolution_cycles").fetchone()[0]
    con.close()
    assert len(rows) == 5
    assert cycle_count == 1
    assert {r[0] for r in rows} == {"candidate"}
    assert {r[1] for r in rows} == {"pending_review_activation_path_intake"}
    assert {r[2] for r in rows} == {GATE_TYPE}
    assert all(r[3] == BOUNDARY for r in rows)


def test_block_when_source_missing(tmp_path: Path) -> None:
    out = build_activation_path_gene_intake(
        source_file=tmp_path / "missing.md", db_path=tmp_path / "missing.db", audit_dir=tmp_path / "audit", write=True
    )
    assert out["status"] == "BLOCK"
    assert out["error"] == "source_file_missing"
    assert out["records_written"] == 0


def test_route_matrix_mode_expands_specific_xuanji_steps(tmp_path: Path) -> None:
    db = tmp_path / "g.db"
    note = tmp_path / "activation.md"
    _create_gene_db(db)
    _source_note(note)
    out = build_activation_path_gene_intake(
        source_file=note, db_path=db, audit_dir=tmp_path / "audit", write=False, mode="route_matrix"
    )
    assert out["status"] == "PASS"
    assert out["mode"] == "route_matrix"
    assert out["candidate_count"] == 15
    names = {c["gene_name"] for c in out["candidates"]}
    assert "Autogenesis AGP 协议候选基因" in names
    assert "GEPA-DSPy 提示/程序优化候选基因" in names
    assert "CORAL 自修复候选基因" in names
    assert "APEX-MOSS HarmRate Rust压缩候选基因" in names
    assert "Paper→Factor→GeneDB 流水线候选基因" in names


def test_route_matrix_write_after_coarse_only_adds_missing_specific_rows(tmp_path: Path) -> None:
    db = tmp_path / "g.db"
    note = tmp_path / "activation.md"
    _create_gene_db(db)
    _source_note(note)
    coarse = build_activation_path_gene_intake(source_file=note, db_path=db, audit_dir=tmp_path / "audit", write=True)
    matrix = build_activation_path_gene_intake(
        source_file=note, db_path=db, audit_dir=tmp_path / "audit", write=True, mode="route_matrix"
    )
    assert coarse["records_written"] == 5
    assert matrix["candidate_count"] == 15
    assert matrix["records_written"] == 10
    con = sqlite3.connect(db)
    total = con.execute("select count(*) from evolution_genes").fetchone()[0]
    statuses = con.execute("select distinct status, verification_status from evolution_genes").fetchall()
    con.close()
    assert total == 15
    assert statuses == [("candidate", "pending_review_activation_path_intake")]


def test_unsupported_mode_blocks_without_write(tmp_path: Path) -> None:
    db = tmp_path / "g.db"
    note = tmp_path / "activation.md"
    _create_gene_db(db)
    _source_note(note)
    out = build_activation_path_gene_intake(source_file=note, db_path=db, audit_dir=tmp_path / "audit", mode="bad")
    assert out["status"] == "BLOCK"
    assert out["error"] == "unsupported_mode"