import sqlite3

from agent import pgg_bridge_processor as bridge


def test_proof_review_gene_does_not_mutate_db(tmp_path, monkeypatch):
    db = tmp_path / "genes.sqlite3"
    con = sqlite3.connect(db)
    con.execute(
        """CREATE TABLE evolution_genes (
            gene_id TEXT PRIMARY KEY,
            gene_name TEXT,
            fitness INTEGER,
            evidence_grade TEXT,
            gate_type TEXT,
            severity_rank INTEGER,
            boundary TEXT,
            absorbed_knowledge TEXT,
            source_refs_json TEXT,
            status TEXT,
            verification_status TEXT
        )"""
    )
    con.execute(
        """INSERT INTO evolution_genes VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "g1",
            "test_gene",
            620,
            "B",
            "unit",
            1,
            "bounded",
            "signals_match: unit",
            "{\"src\":\"unit\"}",
            "candidate",
            "pending_intake_loop_review",
        ),
    )
    con.commit()
    con.close()
    monkeypatch.setattr(bridge, "DB_PATH", db)

    def fake_dual(gene, stats):
        stats["both_rejected"] += 1
        return {
            "decision": "reject",
            "confidence": 88,
            "reason": "unit proof",
            "channel": "dual_agreed",
            "gpt_verdict": {"decision": "reject", "confidence": 88},
            "claude_verdict": {"decision": "reject", "confidence": 80},
        }

    monkeypatch.setattr(bridge, "_dual_channel_review", fake_dual)
    result = bridge.proof_review_gene("g1", task_id="unit_task")
    assert result["verdict"] == "PASS_DUAL_REVIEW_NO_MUTATION"
    assert result["mutation_detected"] is False
    assert result["decision"]["channel"] == "dual_agreed"

    con = sqlite3.connect(db)
    row = con.execute("SELECT status, verification_status FROM evolution_genes WHERE gene_id='g1'").fetchone()
    con.close()
    assert row == ("candidate", "pending_intake_loop_review")


def test_dual_channel_review_no_circular_json_when_agreed(monkeypatch):
    def fake_gpt(gene):
        return {"decision": "reject", "confidence": 90, "reason": "gpt"}

    def fake_claude(gene):
        return {"decision": "reject", "confidence": 80, "reason": "claude"}

    monkeypatch.setattr(bridge, "_llm_review_gene", fake_gpt)
    monkeypatch.setattr(bridge, "_claude_review_gene", fake_claude)
    stats = {"both_approved": 0, "both_rejected": 0, "arbitrated": 0,
             "gpt_only": 0, "claude_only": 0, "deepseek_errors": 0}
    result = bridge._dual_channel_review({"gene_id": "g1"}, stats)
    assert result["channel"] == "dual_agreed"
    assert stats["both_rejected"] == 1
    import json
    json.dumps(result)
