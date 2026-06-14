import sqlite3

from agent import pgg_ars_batch_promotion as batch


def test_is_promotable_review_requires_pass_approve_dual():
    review = {
        "verdict": "PASS_DUAL_REVIEW_NO_MUTATION",
        "mutation_detected": False,
        "external_concurrent_mutation": False,
        "decision": {"decision": "approve", "channel": "dual_agreed", "confidence": 90},
    }
    ok, reason = batch.is_promotable_review(review)
    assert ok is True
    assert reason == "promotable"


def test_is_promotable_review_rejects_gpt_only_in_strict_mode():
    review = {
        "verdict": "PASS_DUAL_REVIEW_NO_MUTATION",
        "mutation_detected": False,
        "external_concurrent_mutation": False,
        "decision": {"decision": "approve", "channel": "gpt_only", "confidence": 90},
    }
    ok, reason = batch.is_promotable_review(review, strict_dual=True)
    assert ok is False
    assert "channel_not_promotable:gpt_only" == reason


def test_candidate_rows_query_can_be_monkeypatched(tmp_path, monkeypatch):
    db = tmp_path / "genes.sqlite3"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE evolution_genes (gene_id TEXT, gene_name TEXT, fitness INTEGER, evidence_grade TEXT, verification_status TEXT, created_at TEXT, status TEXT)")
    con.execute("INSERT INTO evolution_genes VALUES ('g1','g1',701,'B','pending','2026','candidate')")
    con.execute("INSERT INTO evolution_genes VALUES ('g2','g2',699,'B','pending','2026','candidate')")
    con.commit(); con.close()
    monkeypatch.setattr(batch, "DB_PATH", db)
    rows = batch.candidate_rows(limit=10, min_fitness=700)
    assert [r["gene_id"] for r in rows] == ["g1"]


def test_run_batch_skips_gene_already_mutated_inside_lock(tmp_path, monkeypatch):
    db = tmp_path / "genes.sqlite3"
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE evolution_genes (
        gene_id TEXT, gene_name TEXT, fitness INTEGER, evidence_grade TEXT,
        verification_status TEXT, created_at TEXT, status TEXT, last_executed TEXT
    )""")
    con.execute("INSERT INTO evolution_genes VALUES ('g1','g1',701,'B','pending','2026','verified',NULL)")
    con.commit(); con.close()
    monkeypatch.setattr(batch, "DB_PATH", db)
    monkeypatch.setattr(batch, "EVIDENCE_ROOT", tmp_path)
    monkeypatch.setattr(batch, "candidate_rows", lambda limit=3, min_fitness=700, gene_ids=None: [{"gene_id":"g1","gene_name":"g1","fitness":701,"evidence_grade":"B","verification_status":"pending","created_at":"2026"}] if limit != 10000 else [])
    monkeypatch.setattr(batch, "bridge_processor_summary", lambda: {"ok": True})
    monkeypatch.setattr(batch, "gene_db_write_lock", lambda owner: _DummyLock())
    res = batch.run_batch(limit=1, task_id="test_batch", dry_run=True)
    assert res["held"] == 1
    assert res["items"][0]["promotion_precheck"]["reason"] == "not_candidate_at_locked_start"


def test_self_evolution_promote_uses_shared_gene_db_lock(monkeypatch, tmp_path):
    from agent import pgg_self_evolution_loop as loop
    called = {"entered": False}

    class DummyLock:
        def __enter__(self):
            called["entered"] = True
            return {}
        def __exit__(self, exc_type, exc, tb):
            return False

    import agent.pgg_bridge_processor as bridge
    monkeypatch.setattr(bridge, "gene_db_write_lock", lambda owner: DummyLock())
    db = tmp_path / "empty.sqlite3"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE evolution_genes (gene_id TEXT, status TEXT, verification_status TEXT, fitness INTEGER, evidence_grade TEXT, source_refs_json TEXT, absorbed_knowledge TEXT, gene_name TEXT, gate_type TEXT, severity_rank TEXT, boundary TEXT)")
    con.commit(); con.close()
    res = loop.promote_candidates(db, dry_run=True)
    assert called["entered"] is True
    assert res["promoted"] == 0


def test_self_evolution_phase_25_uses_ars_batch_gate(monkeypatch, tmp_path):
    from agent import pgg_self_evolution_loop as loop
    import agent.pgg_ars_batch_promotion as ars_batch

    called = {"ars": False}
    monkeypatch.setattr(loop, "run_intake_scan", lambda write_candidates=True, db_path=None: {"status": "skip"})
    monkeypatch.setattr(loop, "promote_candidates", lambda db_path=None, dry_run=False: {"promoted": 0, "skipped_reasons": {}, "promoted_ids": [], "total_candidates_total": 0})
    monkeypatch.setattr(loop, "run_fusion_on_verified", lambda db_path=None, dry_run=False: {"fused": 0, "sample_results": []})
    monkeypatch.setattr(loop, "generate_db_summary", lambda db_path=None: {"total_genes": 0, "verified": 0, "active": 0, "candidate": 0, "by_status": {}, "by_evidence": {}})
    monkeypatch.setattr(ars_batch, "run_batch", lambda limit=3, min_fitness=700: called.update({"ars": True}) or {"verdict": "WATCH_ARS_BATCH_NO_PROMOTION", "promoted": 0, "held": 0})
    res = loop.run_evolution_cycle(
        promote=True, fusion=False, intake=False, dream_mode=False,
        aris_reflect=False, picoapex_check=False, health_check=False,
        self_scan=False, dry_run=False, db_path=tmp_path / "unused.sqlite3",
    )
    assert called["ars"] is True
    assert "ars_batch_gate" in res["phases"]
    assert "bridge_processor" not in res["phases"]


class _DummyLock:
    def __enter__(self):
        return {"lock_path": "dummy", "owner": "test"}
    def __exit__(self, exc_type, exc, tb):
        return False
