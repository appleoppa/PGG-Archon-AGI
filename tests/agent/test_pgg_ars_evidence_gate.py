from pathlib import Path

from agent import pgg_ars_evidence_gate as gate


def test_header_ast_check_uses_api_key_fstrings():
    result = gate.header_ast_check()
    assert result["pass"] is True
    assert result["binop_headers"] == []
    assert all("api_key" in item["vars"] for item in result["joinedstr_headers"])


def test_init_and_evaluate_structural_packet(tmp_path):
    task_id = "unit_ars_proof"
    gate.init_task(task_id, tmp_path, "unit proof")
    task_dir = tmp_path / task_id
    receipts = task_dir / "receipts"
    receipts.mkdir(exist_ok=True)
    for provider in gate.PROVIDERS:
        (receipts / f"{provider}_receipt.json").write_text('{"status":"success","result":"ok"}')
    rows = []
    for state in gate.STATE_REQUIRED:
        rows.append(f'{{"state":"{state}","task_id":"{task_id}"}}')
    (task_dir / "state_transition.jsonl").write_text("\n".join(rows) + "\n")
    packet = gate.evaluate_packet(task_id, tmp_path)
    assert packet["verdict"] == "PASS_MINIMAL_BOUNDED_ARS_PROOF"
    assert packet["missing_artifacts"] == []
    assert packet["header_ast_check"]["pass"] is True
