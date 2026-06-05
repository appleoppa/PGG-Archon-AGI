from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_legal_boundary_gate import evaluate_legal_boundary_text, run_legal_boundary_gate


def test_evaluate_legal_boundary_text_passes_required_boundaries() -> None:
    text = """
    provided-fact extraction only; not legal correctness proof.
    constructed cases are 合理构造 and not real case numbers 非真实案号.
    CMS BLOCKED != PASS.
    not directly submit; human lawyer review required.
    """
    results, missing = evaluate_legal_boundary_text(text)
    assert missing == []
    assert all(item["status"] == "PASS" for item in results.values())


def test_evaluate_legal_boundary_text_detects_missing_boundaries() -> None:
    results, missing = evaluate_legal_boundary_text("provided-fact only")
    assert "provided_fact_not_legal_correctness" in missing
    assert "cms_blocked_not_pass" in missing


def test_run_legal_boundary_gate_json_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "report.json"
    artifact.write_text(json.dumps({
        "boundary": "provided-fact extraction only; not legal correctness proof; constructed cases are 合理构造 and not real case numbers 非真实案号; CMS BLOCKED != PASS; not directly submit; human lawyer review required."
    }, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "gate.json"
    result = run_legal_boundary_gate(artifact_path=artifact, out=out)
    assert result.status == "PASS"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["status"] == "PASS"
