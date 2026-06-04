from __future__ import annotations

from agent.pgg_archon_alpha_psi_truth_gate import run_truth_gate, write_truth_gate


def test_truth_gate_passes_current_boundaries(tmp_path) -> None:
    r = run_truth_gate()
    assert r.status == "PASS"
    assert r.passed == r.total
    assert r.total == 5
    assert "not AGI capability" in r.boundary


def test_write_truth_gate(tmp_path) -> None:
    out = tmp_path / "alpha.json"
    summary = write_truth_gate(out)
    assert summary["status"] == "PASS"
    assert out.exists()
