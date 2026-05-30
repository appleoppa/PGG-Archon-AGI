import json
import sqlite3

from agent.pgg_archon_auto_core_takeover import (
    apply_auto_core_takeover_context,
    build_auto_core_takeover_status,
    write_auto_core_takeover_policy,
)


def _create_gene_db(path):
    con = sqlite3.connect(path)
    con.execute("create table genes(id integer primary key, name text, pattern_type text, source_repo text, code_snippet text, quality_score real, extracted_at text)")
    con.execute(
        "insert into genes(name,pattern_type,source_repo,code_snippet,quality_score,extracted_at) values (?,?,?,?,?,?)",
        ("ultimate_evolution_formula_phase9_cron_ci_drift_gate", "p9", "test", "{}", 0.8742, "now"),
    )
    con.commit(); con.close()


def test_auto_core_takeover_policy_activates_only_with_phase9_and_db_readback(tmp_path):
    policy = tmp_path / "policy.json"
    phase9 = tmp_path / "phase9.json"
    db = tmp_path / "pgg.db"
    phase9.write_text(json.dumps({"status": "ci_drift_gate_passed", "blockers": []}), encoding="utf-8")
    _create_gene_db(db)
    write_auto_core_takeover_policy(policy_path=policy)

    status = build_auto_core_takeover_status(policy_path=policy, phase9_report_path=phase9, db_path=db)

    assert status["schema"] == "PGGArchonAutoCoreTakeoverStatus/v1"
    assert status["status"] == "auto_core_takeover_active"
    assert status["blockers"] == []
    assert status["authorized_actions"]["auto_modify_run_agent_py"] is True


def test_apply_auto_core_takeover_context_is_bounded_and_idempotent(tmp_path, monkeypatch):
    policy = tmp_path / "policy.json"
    phase9 = tmp_path / "phase9.json"
    db = tmp_path / "pgg.db"
    phase9.write_text(json.dumps({"status": "ci_drift_gate_passed", "blockers": []}), encoding="utf-8")
    _create_gene_db(db)
    write_auto_core_takeover_policy(policy_path=policy)

    import agent.pgg_archon_auto_core_takeover as mod

    monkeypatch.setattr(mod, "_DEFAULT_POLICY", policy)
    monkeypatch.setattr(mod, "_DEFAULT_PHASE9", phase9)
    monkeypatch.setattr(mod, "_DEFAULT_DB", db)

    context = apply_auto_core_takeover_context("base")
    again = apply_auto_core_takeover_context(context)

    assert "[PGG_ARCHON_AUTO_CORE_TAKEOVER_ACTIVE]" in context
    assert "never read or expose secrets" in context
    assert again.count("[PGG_ARCHON_AUTO_CORE_TAKEOVER_ACTIVE]") == 1
