import json
from pathlib import Path

from agent.pgg_promotion_packet_completion import complete_packet_queue


def test_complete_packet_queue_blocks_missing_source_and_keeps_no_db_mutation(tmp_path):
    packet = {
        "schema": "PGGPromotionProofPacket/v0.1",
        "task_id": "pam-test-missing",
        "capability_id": "pgg_gene_missing",
        "risk_lane": "low_engineering",
        "proposal": "PROMOTION_REVIEW_REQUIRED",
        "source_refs_json": json.dumps({"source_file": str(tmp_path / "missing.py"), "source_hash": "abc"}),
        "required_evidence": ["source_readback", "test_output", "runtime_output", "ledger_or_manifest", "replay"],
        "missing_evidence": ["test_output", "ledger_or_manifest", "replay"],
    }
    queue = tmp_path / "queue.json"
    queue.write_text(json.dumps([packet]), encoding="utf-8")

    result = complete_packet_queue(queue, tmp_path / "out", limit=1)

    assert result["schema"] == "PGGProofPacketCompletion/v0.1"
    assert result["completed_count"] == 1
    assert result["verdict_counts"] == {"BLOCKED_SOURCE_MISSING": 1}
    evidence = json.loads((tmp_path / "out" / "completion_results.json").read_text(encoding="utf-8"))
    assert evidence[0]["task_id"] == "pam-test-missing"
    assert evidence[0]["db_mutation"] is False
    assert evidence[0]["controlled_promotion_eligible"] is False


def test_complete_packet_queue_passes_existing_low_risk_packet_with_py_compile_and_replay(tmp_path):
    src = tmp_path / "agent" / "sample_capability.py"
    src.parent.mkdir()
    src.write_text("def answer():\n    return 42\n", encoding="utf-8")
    test_file = tmp_path / "tests" / "test_sample_capability.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "from agent.sample_capability import answer\n\n"
        "def test_answer():\n"
        "    assert answer() == 42\n",
        encoding="utf-8",
    )
    packet = {
        "schema": "PGGPromotionProofPacket/v0.1",
        "task_id": "pam-test-pass",
        "capability_id": "pgg_gene_pass",
        "risk_lane": "low_engineering",
        "proposal": "PROMOTION_REVIEW_REQUIRED",
        "source_refs_json": json.dumps({"source_file": str(src), "source_hash": "unused"}),
        "required_evidence": ["source_readback", "claim_extract", "test_output", "runtime_output", "ledger_or_manifest", "replay"],
        "present_evidence": ["claim_extract", "source_readback", "runtime_output"],
    }
    queue = tmp_path / "queue.json"
    queue.write_text(json.dumps([packet]), encoding="utf-8")

    result = complete_packet_queue(queue, tmp_path / "out", limit=1, pytest_root=tmp_path, pythonpath=tmp_path)

    assert result["verdict_counts"] == {"PASS_CONTROLLED_PROMOTION_PROPOSAL": 1}
    evidence = json.loads((tmp_path / "out" / "completion_results.json").read_text(encoding="utf-8"))
    assert evidence[0]["controlled_promotion_eligible"] is True
    assert "test_output" in evidence[0]["completed_evidence"]
    assert "replay" in evidence[0]["completed_evidence"]
    assert evidence[0]["db_mutation"] is False
