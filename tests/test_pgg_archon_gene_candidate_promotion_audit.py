from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agent.pgg_archon_gene_promotion_gate import (
    evaluate_all_gene_candidates_promotion_gate,
    main,
)


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "pgg_archon.db"
    con = sqlite3.connect(path)
    con.execute("create table genes(id integer primary key, name text, pattern_type text, source_repo text, code_snippet text, quality_score real, extracted_at text)")
    con.execute("create table gene_lifecycle(gene_id integer primary key, state text not null, activated_at text, promoted_at text, archived_at text, retired_at text, quality_score real, parent_gene_id integer, candidate_at text)")
    rows = [
        (1, "safe_regression_gate", "verified_regression_fixture_gate_v1", "repo", '{"status":"PASS","tests":"live"}', 0.91),
        (2, "phase3_dup", "ultimate_evolution_formula_phase3_periodic_ars_v1", "repo", '{"score":87.4}', 0.87),
        (3, "phase3_dup", "ultimate_evolution_formula_phase3_periodic_ars_v1", "repo", '{"score":87.4}', 0.87),
        (4, "low_score", "safe_low_score", "repo", '{}', 0.70),
        (5, "auto_core_takeover", "ultimate_evolution_formula_phase10_auto_core_takeover_v1", "repo", '{"rollback_plan_present": false}', 0.90),
    ]
    for row in rows:
        con.execute("insert into genes(id,name,pattern_type,source_repo,code_snippet,quality_score) values (?,?,?,?,?,?)", row)
        con.execute("insert into gene_lifecycle(gene_id,state,quality_score,promoted_at,candidate_at) values (?,'candidate',?,null,'2026-06-04T00:00:00Z')", (row[0], row[5]))
    con.commit(); con.close()
    return path


def _quorum(tmp_path: Path, *, status: str = "PASS_QUORUM") -> Path:
    path = tmp_path / "llm_quorum.json"
    path.write_text(json.dumps({"status": status, "visible_pass_count": 2, "required_pass_count": 2}), encoding="utf-8")
    return path


def test_all_candidate_audit_blocks_when_llm_quorum_missing(tmp_path: Path) -> None:
    result = evaluate_all_gene_candidates_promotion_gate(db_path=_db(tmp_path))
    assert result.status == "BLOCKED_CANDIDATE_AUDIT"
    assert result.review_ready_count == 0
    assert "llm_quorum_passed" in result.blockers
    assert all("llm_quorum_not_passed" in row["blockers"] for row in result.candidate_reviews)


def test_all_candidate_audit_classifies_ready_duplicate_low_score_and_core_takeover(tmp_path: Path) -> None:
    result = evaluate_all_gene_candidates_promotion_gate(db_path=_db(tmp_path), llm_quorum_path=_quorum(tmp_path))
    by_id = {row["gene_id"]: row for row in result.candidate_reviews}
    assert result.status == "READY_FOR_PROMOTION_TRANSACTION"
    assert result.review_ready_count == 1
    assert by_id[1]["decision"] == "PROMOTION_REVIEW_READY"
    assert "duplicate_candidate_group" in by_id[2]["blockers"]
    assert "phase3_ars_cycle_candidate_requires_duplicate_staleness_review" in by_id[2]["blockers"]
    assert "quality_score_below_threshold" in by_id[4]["blockers"]
    assert "core_takeover_requires_explicit_human_authorization" in by_id[5]["blockers"]
    assert "candidate_contains_unresolved_safety_hold" in by_id[5]["blockers"]


def test_main_all_candidates_writes_result(tmp_path: Path, capsys) -> None:
    assert main([
        "--db", str(_db(tmp_path)),
        "--output-dir", str(tmp_path / "out"),
        "--all-candidates",
        "--llm-quorum", str(_quorum(tmp_path, status="BLOCKED_QUORUM")),
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "BLOCKED_CANDIDATE_AUDIT"
    assert Path(printed["result"]).is_file()
