import json
import sqlite3

from agent.pgg_archon_ultimate_evolution_ars_cycle import (
    build_phase3_ars_cycle,
    build_phase4_ars_trend_replay,
    build_phase5_promotion_gate,
    build_phase6_tool_status_surface,
    build_phase7_evidence_chain_status,
    build_phase8_chain_integrity_gate,
    build_phase9_cron_ci_drift_gate,
    call_pgg_ultimate_evolution_tool,
    collect_phase3_native_evidence,
    persist_phase3_to_pgg_db,
    persist_phase3_to_pgg_db_idempotent,
    persist_phase4_to_pgg_db,
    persist_phase5_to_pgg_db,
    persist_phase6_to_pgg_db,
    persist_phase7_to_pgg_db,
    persist_phase8_to_pgg_db,
    persist_phase9_to_pgg_db,
    write_phase3_report,
    write_phase4_report,
    write_phase5_report,
    write_phase6_report,
    write_phase7_report,
    write_phase8_report,
    write_phase9_report,
)


def test_collect_phase3_native_evidence_reads_phase_reports(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "phase1_report.json").write_text('{"schema":"phase1"}', encoding="utf-8")
    (workspace / "phase2_tool_integration_report.json").write_text(
        json.dumps({"tool_registered": True, "toolset_contains_tool": True, "test_result": "9 passed"}),
        encoding="utf-8",
    )
    session_db = tmp_path / "state.db"
    con = sqlite3.connect(session_db)
    con.execute("create table messages(id integer primary key, timestamp real)")
    con.execute("create table sessions(id text primary key)")
    con.execute("insert into sessions(id) values ('s1')")
    con.execute("insert into messages(timestamp) values (9999999999)")
    con.commit(); con.close()
    cron = tmp_path / "jobs.json"
    cron.write_text(json.dumps({"jobs": [{"name": "PGG Archon", "enabled": True, "last_run": {"status": "ok"}}]}), encoding="utf-8")

    evidence = collect_phase3_native_evidence(workspace_dir=workspace, session_db_path=session_db, cron_jobs_path=cron)

    assert evidence["phase1_report_exists"] is True
    assert evidence["phase2_report_exists"] is True
    assert evidence["tool_registered"] is True
    assert evidence["phase2_tests_seen"] is True
    assert evidence["sessiondb"]["messages_total"] == 1
    assert evidence["cron"]["active_jobs"] == 1


def test_call_pgg_ultimate_evolution_tool_returns_ars_plan():
    payload = call_pgg_ultimate_evolution_tool({
        "phase1_report_exists": True,
        "phase2_report_exists": True,
        "tool_registered": True,
        "phase2_tests_seen": True,
        "sessiondb": {"available": True, "messages_total": 5},
        "cron": {"available": True, "recent_errors": 0},
    })

    assert payload["report"]["schema"] == "PGGArchonUltimateEvolutionFormulaReport/v1"
    assert payload["ars_plan"]["decision"] == "allow_low_risk_sidecar_iteration"


def test_build_phase3_ars_cycle_preserves_sidecar_boundary():
    cycle = build_phase3_ars_cycle({
        "phase1_report_exists": True,
        "phase2_report_exists": True,
        "tool_registered": True,
        "phase2_tests_seen": True,
        "sessiondb": {"available": True, "messages_total": 5},
        "cron": {"available": True, "recent_errors": 0},
    })

    assert cycle["schema"] == "PGGArchonUltimateEvolutionPhase3ARSCycle/v1"
    assert cycle["status"] == "verified"
    assert cycle["score"] >= 75
    assert "no run_agent.py mutation" in cycle["boundary"]


def test_write_phase3_report_and_persist_readback(tmp_path):
    payload = build_phase3_ars_cycle({
        "phase1_report_exists": True,
        "phase2_report_exists": True,
        "tool_registered": True,
        "phase2_tests_seen": True,
        "sessiondb": {"available": True, "messages_total": 5},
        "cron": {"available": True, "recent_errors": 0},
    })
    paths = write_phase3_report(tmp_path / "workspace", payload=payload)
    assert paths["json"].endswith("phase3_ars_cycle_report.json")
    assert paths["markdown"].endswith("phase3_ars_cycle_report.md")

    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)

    result = persist_phase3_to_pgg_db(payload, paths, db_path=db)
    assert result["experiment_id"] == 1
    assert result["gene_id"] == 1
    assert result["readback"][1] == "ultimate_evolution_formula_phase3_ars_cycle_gate"


def _create_pgg_tables(db):
    con = sqlite3.connect(db)
    con.execute("create table experiments(id integer primary key, name text, hypothesis text, result text, score real, created_at text, tags text)")
    con.execute("create table genes(id integer primary key, name text, pattern_type text, source_repo text, code_snippet text, quality_score real, extracted_at text)")
    con.commit(); con.close()


def test_phase4_replays_phase3_trend_and_detects_duplicate_genes(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    payload = build_phase3_ars_cycle({
        "phase1_report_exists": True,
        "phase2_report_exists": True,
        "tool_registered": True,
        "phase2_tests_seen": True,
        "sessiondb": {"available": True, "messages_total": 5},
        "cron": {"available": True, "recent_errors": 0},
    })
    paths = write_phase3_report(workspace, payload=payload)
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)
    persist_phase3_to_pgg_db(payload, paths, db_path=db)
    persist_phase3_to_pgg_db(payload, paths, db_path=db)

    replay = build_phase4_ars_trend_replay(workspace_dir=workspace, db_path=db)

    assert replay["schema"] == "PGGArchonUltimateEvolutionPhase4ARSTrendReplay/v1"
    assert replay["status"] == "verified"
    assert replay["duplicate_gene_count"] == 1
    assert replay["risk"] == "cron_duplicate_gene_pollution"
    assert replay["payload_fingerprint"]


def test_phase3_idempotent_persistence_skips_repeated_fingerprint(tmp_path):
    workspace = tmp_path / "workspace"
    payload = build_phase3_ars_cycle({
        "phase1_report_exists": True,
        "phase2_report_exists": True,
        "tool_registered": True,
        "phase2_tests_seen": True,
        "sessiondb": {"available": True, "messages_total": 5},
        "cron": {"available": True, "recent_errors": 0},
    })
    paths = write_phase3_report(workspace, payload=payload)
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)

    first = persist_phase3_to_pgg_db_idempotent(payload, paths, db_path=db)
    second = persist_phase3_to_pgg_db_idempotent(payload, paths, db_path=db)

    assert first["inserted"] is True
    assert second["deduped"] is True
    assert second["gene_id"] == first["gene_id"]


def test_write_phase4_report_and_persist_readback(tmp_path):
    replay = {
        "schema": "PGGArchonUltimateEvolutionPhase4ARSTrendReplay/v1",
        "status": "verified",
        "score": 87.417,
        "trend": "stable",
        "duplicate_gene_count": 2,
        "payload_fingerprint": "abc123",
    }
    paths = write_phase4_report(tmp_path / "workspace", replay=replay)
    assert paths["json"].endswith("phase4_ars_trend_replay_dedup_report.json")
    assert paths["markdown"].endswith(".md")
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)

    result = persist_phase4_to_pgg_db(replay, paths, db_path=db)
    again = persist_phase4_to_pgg_db(replay, paths, db_path=db)

    assert result["inserted"] is True
    assert result["readback"][1] == "ultimate_evolution_formula_phase4_ars_trend_dedup_gate"
    assert again["deduped"] is True


def test_phase5_promotion_gate_fuses_phase3_phase4_and_model_review(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    phase3 = {
        "schema": "PGGArchonUltimateEvolutionPhase3ARSCycle/v1",
        "status": "verified",
        "score": 87.417,
        "decision": "allow_low_risk_sidecar_iteration",
    }
    phase4 = {
        "schema": "PGGArchonUltimateEvolutionPhase4DedupReport/v1",
        "status": "verified",
        "score": 87.417,
        "trend": "stable",
        "duplicate_gene_count": 2,
        "dedup_gate": {"status": "active"},
    }
    (workspace / "phase3_ars_cycle_report.json").write_text(json.dumps(phase3), encoding="utf-8")
    (workspace / "phase4_ars_trend_replay_dedup_report.json").write_text(json.dumps(phase4), encoding="utf-8")
    review_dir = workspace / "model_review_phase5"
    review_dir.mkdir()
    (review_dir / "phase5_dual_model_review.json").write_text(json.dumps({"ok_count": 2, "called_at": "now"}), encoding="utf-8")

    gate = build_phase5_promotion_gate(workspace_dir=workspace)

    assert gate["schema"] == "PGGArchonUltimateEvolutionPhase5PromotionGate/v1"
    assert gate["status"] == "promotion_ready"
    assert gate["decision"] == "allow_candidate_promotion"
    assert all(gate["gates"].values())


def test_phase5_report_and_persistence_are_idempotent(tmp_path):
    gate = {
        "schema": "PGGArchonUltimateEvolutionPhase5PromotionGate/v1",
        "status": "promotion_ready",
        "score": 87.417,
        "decision": "allow_candidate_promotion",
        "blockers": [],
        "gates": {"phase3_verified": True, "phase4_verified": True},
    }
    paths = write_phase5_report(tmp_path / "workspace", gate=gate)
    assert paths["json"].endswith("phase5_promotion_gate_report.json")
    assert paths["markdown"].endswith(".md")
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)

    result = persist_phase5_to_pgg_db(gate, paths, db_path=db)
    again = persist_phase5_to_pgg_db(gate, paths, db_path=db)

    assert result["inserted"] is True
    assert result["readback"][1] == "ultimate_evolution_formula_phase5_promotion_gate"
    assert again["deduped"] is True


def test_phase6_tool_status_surface_and_persistence_are_idempotent(tmp_path):
    surface = {
        "schema": "PGGArchonUltimateEvolutionPhase6ToolStatusSurface/v1",
        "status": "verified",
        "tool_action": "promotion_status",
        "score": 87.417,
        "decision": "allow_candidate_promotion",
        "blockers": [],
    }
    paths = write_phase6_report(tmp_path / "workspace", surface=surface)
    assert paths["json"].endswith("phase6_tool_status_surface_report.json")
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)

    result = persist_phase6_to_pgg_db(surface, paths, db_path=db)
    again = persist_phase6_to_pgg_db(surface, paths, db_path=db)

    assert result["inserted"] is True
    assert result["readback"][1] == "ultimate_evolution_formula_phase6_native_tool_status_surface"
    assert again["deduped"] is True

def test_phase6_build_uses_native_tool_action():
    surface = build_phase6_tool_status_surface()

    assert surface["schema"] == "PGGArchonUltimateEvolutionPhase6ToolStatusSurface/v1"
    assert surface["tool_action"] == "promotion_status"
    assert surface["native_tool_report_schema"] == "PGGArchonUltimateEvolutionPromotionStatus/v1"


def test_phase7_evidence_chain_status_verifies_reports_db_cron_and_review(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    reports = {
        "phase3_ars_cycle_report.json": {"status": "verified", "score": 87.417},
        "phase4_ars_trend_replay_dedup_report.json": {"status": "verified", "score": 87.417},
        "phase5_promotion_gate_report.json": {"status": "promotion_ready", "score": 87.417},
        "phase6_tool_status_surface_report.json": {"status": "verified", "score": 87.417},
    }
    for name, data in reports.items():
        (workspace / name).write_text(json.dumps(data), encoding="utf-8")
    review_dir = workspace / "model_review_phase7"
    review_dir.mkdir()
    (review_dir / "phase7_gpt_review.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    cron_script = tmp_path / "cron.sh"
    cron_script.write_text("run --phase4 --phase5 --phase6", encoding="utf-8")
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)
    con = sqlite3.connect(db)
    for name in [
        "ultimate_evolution_formula_phase3_ars_cycle_gate",
        "ultimate_evolution_formula_phase4_ars_trend_dedup_gate",
        "ultimate_evolution_formula_phase5_promotion_gate",
        "ultimate_evolution_formula_phase6_native_tool_status_surface",
    ]:
        con.execute("insert into genes(name,pattern_type,source_repo,code_snippet,quality_score,extracted_at) values (?,?,?,?,?,?)", (name, "p", "s", "{}", 0.8742, "now"))
    con.commit(); con.close()

    chain = build_phase7_evidence_chain_status(workspace_dir=workspace, db_path=db, cron_script=cron_script)

    assert chain["schema"] == "PGGArchonUltimateEvolutionPhase7EvidenceChainStatus/v1"
    assert chain["status"] == "evidence_chain_verified"
    assert chain["blockers"] == []
    assert all(chain["gates"].values())


def test_phase7_report_and_persistence_are_idempotent(tmp_path):
    chain = {
        "schema": "PGGArchonUltimateEvolutionPhase7EvidenceChainStatus/v1",
        "status": "evidence_chain_verified",
        "score": 87.417,
        "decision": "allow_chain_as_verified_sidecar_evidence",
        "blockers": [],
        "gates": {"phase3_report_ok": True},
    }
    paths = write_phase7_report(tmp_path / "workspace", chain=chain)
    assert paths["json"].endswith("phase7_evidence_chain_status_report.json")
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)

    result = persist_phase7_to_pgg_db(chain, paths, db_path=db)
    again = persist_phase7_to_pgg_db(chain, paths, db_path=db)

    assert result["inserted"] is True
    assert result["readback"][1] == "ultimate_evolution_formula_phase7_evidence_chain_status"
    assert again["deduped"] is True


def _seed_phase8_workspace(workspace):
    workspace.mkdir(exist_ok=True)
    reports = {
        "phase3_ars_cycle_report.json": {"status": "verified", "score": 87.417},
        "phase4_ars_trend_replay_dedup_report.json": {"status": "verified", "score": 87.417},
        "phase5_promotion_gate_report.json": {"status": "promotion_ready", "score": 87.417},
        "phase6_tool_status_surface_report.json": {"status": "verified", "score": 87.417},
        "phase7_evidence_chain_status_report.json": {"status": "evidence_chain_verified", "score": 87.417},
    }
    for name, data in reports.items():
        (workspace / name).write_text(json.dumps(data), encoding="utf-8")
    review_dir = workspace / "model_review_phase8"
    review_dir.mkdir(exist_ok=True)
    (review_dir / "phase8_gpt_review.json").write_text(json.dumps({"ok": True}), encoding="utf-8")


def test_phase8_chain_integrity_gate_hashes_phase3_7_reports_db_cron_and_review(tmp_path):
    workspace = tmp_path / "workspace"
    _seed_phase8_workspace(workspace)
    cron_script = tmp_path / "cron.sh"
    cron_script.write_text("run --phase4 --phase5 --phase6 --phase7", encoding="utf-8")
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)
    con = sqlite3.connect(db)
    for name in [
        "ultimate_evolution_formula_phase3_ars_cycle_gate",
        "ultimate_evolution_formula_phase4_ars_trend_dedup_gate",
        "ultimate_evolution_formula_phase5_promotion_gate",
        "ultimate_evolution_formula_phase6_native_tool_status_surface",
        "ultimate_evolution_formula_phase7_evidence_chain_status",
    ]:
        con.execute("insert into genes(name,pattern_type,source_repo,code_snippet,quality_score,extracted_at) values (?,?,?,?,?,?)", (name, "p", "s", "{}", 0.8742, "now"))
    con.commit(); con.close()

    gate = build_phase8_chain_integrity_gate(workspace_dir=workspace, db_path=db, cron_script=cron_script)

    assert gate["schema"] == "PGGArchonUltimateEvolutionPhase8ChainIntegrityGate/v1"
    assert gate["status"] == "integrity_verified"
    assert gate["blockers"] == []
    assert gate["manifest_hash"]
    assert gate["artifacts"]["phase7_report"]["sha256"]
    assert all(gate["gates"].values())


def test_phase8_report_and_persistence_are_idempotent(tmp_path):
    gate = {
        "schema": "PGGArchonUltimateEvolutionPhase8ChainIntegrityGate/v1",
        "status": "integrity_verified",
        "score": 87.417,
        "decision": "allow_integrity_manifest_as_cron_ci_gate",
        "manifest_hash": "abc123",
        "blockers": [],
        "gates": {"phase7_chain_verified": True},
    }
    paths = write_phase8_report(tmp_path / "workspace", gate=gate)
    assert paths["json"].endswith("phase8_chain_integrity_gate_report.json")
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)

    result = persist_phase8_to_pgg_db(gate, paths, db_path=db)
    again = persist_phase8_to_pgg_db(gate, paths, db_path=db)

    assert result["inserted"] is True
    assert result["readback"][1] == "ultimate_evolution_formula_phase8_chain_integrity_gate"
    assert again["deduped"] is True


def test_phase9_cron_ci_drift_gate_compares_phase8_manifest_native_tool_cron_and_review(tmp_path):
    workspace = tmp_path / "workspace"
    _seed_phase8_workspace(workspace)
    cron_script = tmp_path / "cron.sh"
    cron_script.write_text("run --phase4 --phase5 --phase6 --phase7 --phase8 --phase9", encoding="utf-8")
    review_dir = workspace / "model_review_phase9"
    review_dir.mkdir(exist_ok=True)
    (review_dir / "phase9_gpt_review.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)
    con = sqlite3.connect(db)
    for name in [
        "ultimate_evolution_formula_phase3_ars_cycle_gate",
        "ultimate_evolution_formula_phase4_ars_trend_dedup_gate",
        "ultimate_evolution_formula_phase5_promotion_gate",
        "ultimate_evolution_formula_phase6_native_tool_status_surface",
        "ultimate_evolution_formula_phase7_evidence_chain_status",
        "ultimate_evolution_formula_phase8_chain_integrity_gate",
    ]:
        con.execute("insert into genes(name,pattern_type,source_repo,code_snippet,quality_score,extracted_at) values (?,?,?,?,?,?)", (name, "p", "s", "{}", 0.8742, "now"))
    con.commit(); con.close()

    phase8 = build_phase8_chain_integrity_gate(workspace_dir=workspace, db_path=db, cron_script=cron_script)
    write_phase8_report(workspace, gate=phase8)
    gate = build_phase9_cron_ci_drift_gate(workspace_dir=workspace, db_path=db, cron_script=cron_script)

    assert gate["schema"] == "PGGArchonUltimateEvolutionPhase9CronCIDriftGate/v1"
    assert gate["status"] == "ci_drift_gate_passed"
    assert gate["blockers"] == []
    assert gate["native_tool_report_schema"] == "PGGArchonUltimateEvolutionChainIntegrityStatus/v1"
    assert all(gate["gates"].values())


def test_phase9_report_and_persistence_are_idempotent(tmp_path):
    gate = {
        "schema": "PGGArchonUltimateEvolutionPhase9CronCIDriftGate/v1",
        "status": "ci_drift_gate_passed",
        "score": 87.417,
        "decision": "allow_cron_ci_drift_gate_enforcement",
        "gate_hash": "abc123",
        "blockers": [],
        "gates": {"phase8_manifest_matches_current": True},
    }
    paths = write_phase9_report(tmp_path / "workspace", gate=gate)
    assert paths["json"].endswith("phase9_cron_ci_drift_gate_report.json")
    db = tmp_path / "pgg.db"
    _create_pgg_tables(db)

    result = persist_phase9_to_pgg_db(gate, paths, db_path=db)
    again = persist_phase9_to_pgg_db(gate, paths, db_path=db)

    assert result["inserted"] is True
    assert result["readback"][1] == "ultimate_evolution_formula_phase9_cron_ci_drift_gate"
    assert again["deduped"] is True
