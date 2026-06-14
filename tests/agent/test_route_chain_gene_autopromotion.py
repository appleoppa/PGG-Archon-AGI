import json
from pathlib import Path

from agent.route_chain_gene_autopromotion import (
    record_controlled_autonomous_promotion,
    validate_route_chain_gene_candidate,
    write_route_chain_candidate_to_gene_db,
)


def _hash_obj(obj):
    import hashlib
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _candidate_fixture(tmp_path: Path):
    stages = []
    providers = [
        "gpt55_5yuantoken",
        "claude_opus47_5yuantoken",
        "gpt55_5yuantoken",
        "deepseek_v4_flash",
        "gpt55_5yuantoken",
    ]
    prev = "seed"
    for idx, provider in enumerate(providers):
        stage = {
            "stage": ["GPT主脑统筹", "Claude反证审错", "修复落地", "旁证压缩", "GPT主脑收束"][idx],
            "provider": provider,
            "response_id": f"resp-{idx}",
            "output_hash": f"hash-{idx}",
            "record_hash": f"rh-{idx}",
            "content_excerpt": "这是足够长的判断增量、反证增量、修复增量和收束结论，用于通过候选基因验证门禁。",
        }
        stages.append(stage)
        prev = stage["record_hash"]
    evidence = {
        "schema": "route_chain_evidence_gate/v3",
        "task_id": "rceg_test",
        "task_class": "evolution_agi",
        "risk_level": "medium",
        "execute_stages": True,
        "selected_chain": "dual_strong_review",
        "stage_outputs": stages,
        "final_decision": "model_execution_completed",
        "fallback_used": False,
        "errors_or_model_failures": [],
    }
    evidence["record_hash"] = _hash_obj(evidence)
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
    candidate = {
        "schema": "route_chain_gene_candidate/v1",
        "status": "candidate_ready",
        "gene_id": "gene_candidate_rceg_test",
        "source_task_id": "rceg_test",
        "source_evidence_path": str(evidence_path),
        "source_record_hash": evidence["record_hash"],
        "task_class": "evolution_agi",
        "risk_level": "medium",
        "selected_chain": "dual_strong_review",
        "candidate_rule": "AGI/进化任务必须以 GPT(A)+Claude(C) 真实双通道为门禁。",
        "stage_response_ids": [s["response_id"] for s in stages],
        "stage_output_hashes": [s["output_hash"] for s in stages],
        "fallback_used": False,
        "fallback_notes": [],
        "verification": {"record_hash_ok": True, "stage_count": 5, "real_response_count": 5, "gates": []},
        "not_written_to_gene_db": True,
        "requires_human_or_next_gate": True,
    }
    candidate["gene_hash"] = _hash_obj(candidate)
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
    return candidate_path


def _create_gene_db(path: Path):
    import sqlite3
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE evolution_cycles(cycle_id TEXT PRIMARY KEY,created_at TEXT NOT NULL,theme TEXT NOT NULL,sequence_logic TEXT NOT NULL,status TEXT NOT NULL,evidence_grade TEXT NOT NULL,boundary TEXT NOT NULL)")
    con.execute("CREATE TABLE evolution_genes(gene_id TEXT PRIMARY KEY,cycle_id TEXT NOT NULL,created_at TEXT NOT NULL,defect_no INTEGER NOT NULL,defect_name TEXT NOT NULL,gene_name TEXT NOT NULL,absorbed_knowledge TEXT NOT NULL,source_refs_json TEXT NOT NULL,repair_mechanism TEXT NOT NULL,severity_rank INTEGER NOT NULL,apex_variables TEXT NOT NULL,gate_type TEXT NOT NULL,reusable_rule TEXT NOT NULL,status TEXT NOT NULL,evidence_grade TEXT NOT NULL,verification_status TEXT NOT NULL,boundary TEXT NOT NULL,gene_hash TEXT NOT NULL)")
    con.execute("CREATE TABLE verification_log(log_id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,check_name TEXT NOT NULL,result TEXT NOT NULL,details TEXT NOT NULL)")
    con.commit(); con.close()


def test_validate_route_chain_gene_candidate_passes_for_real_gpt_claude_stages(tmp_path):
    candidate_path = _candidate_fixture(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    report = validate_route_chain_gene_candidate(candidate)
    assert report["status"] == "PASS"
    assert report["providers"] == ["claude_opus47_5yuantoken", "deepseek_v4_flash", "gpt55_5yuantoken"]


def test_write_candidate_to_gene_db_and_record_controlled_promotion(tmp_path):
    candidate_path = _candidate_fixture(tmp_path)
    db = tmp_path / "genes.sqlite3"
    _create_gene_db(db)
    report = write_route_chain_candidate_to_gene_db(candidate_path, db_path=db)
    assert report["status"] == "PASS"
    assert report["readback_count"] == 1
    promotion = record_controlled_autonomous_promotion(report, audit_dir=tmp_path / "audit")
    assert promotion["status"] == "PROMOTED_CONTROLLED"
    assert promotion["success"] is True
    assert promotion["agi_completion_claim"] is False
    assert Path(promotion["audit_path"]).exists()


def test_controlled_promotion_core_patch_callback_blocks_without_request(tmp_path):
    candidate_path = _candidate_fixture(tmp_path)
    db = tmp_path / "genes.sqlite3"
    _create_gene_db(db)
    report = write_route_chain_candidate_to_gene_db(candidate_path, db_path=db)
    promotion = record_controlled_autonomous_promotion(report, audit_dir=tmp_path / "audit", enable_core_patch=True)
    assert promotion["status"] == "PROMOTED_CONTROLLED"
    assert promotion["core_patch"]["status"] == "BLOCK"
    assert "core_patch_request_missing" in promotion["core_patch"]["issues"]


def test_controlled_promotion_core_patch_callback_applies_allowlisted_patch(tmp_path, monkeypatch):
    monkeypatch.setenv("PGG_AUTO_CORE_PATCH_ALLOW_EXTERNAL_TEST_TARGETS", "1")
    candidate_path = _candidate_fixture(tmp_path)
    db = tmp_path / "genes.sqlite3"
    _create_gene_db(db)
    report = write_route_chain_candidate_to_gene_db(candidate_path, db_path=db)
    target = tmp_path / "target.py"
    target.write_text("VALUE = 'old'\n", encoding="utf-8")
    promotion = record_controlled_autonomous_promotion(
        report,
        audit_dir=tmp_path / "audit",
        enable_core_patch=True,
        core_patch_request={
            "target_path": str(target),
            "old_text": "VALUE = 'old'",
            "new_text": "VALUE = 'new'",
            "reason": "unit test promotion callback",
            "verify_commands": [f"python -m py_compile {target}"],
            "allowlist": [str(target)],
            "audit_dir": tmp_path / "core-audit",
            "backup_dir": tmp_path / "backup",
        },
    )
    assert promotion["status"] == "PROMOTED_CONTROLLED"
    assert promotion["core_patch"]["status"] == "PASS"
    assert "VALUE = 'new'" in target.read_text(encoding="utf-8")


def test_write_candidate_blocks_when_claude_missing(tmp_path):
    candidate_path = _candidate_fixture(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    evidence_path = Path(candidate["source_evidence_path"])
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    for stage in evidence["stage_outputs"]:
        if stage["provider"] == "claude_opus47_5yuantoken":
            stage["provider"] = "deepseek_v4_flash"
    evidence.pop("record_hash", None)
    evidence["record_hash"] = _hash_obj(evidence)
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
    candidate["source_record_hash"] = evidence["record_hash"]
    candidate.pop("gene_hash", None)
    candidate["gene_hash"] = _hash_obj(candidate)
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
    db = tmp_path / "genes.sqlite3"
    _create_gene_db(db)
    report = write_route_chain_candidate_to_gene_db(candidate_path, db_path=db)
    assert report["status"] == "BLOCK"
    assert "missing_claude_stage" in report["validation"]["issues"]
