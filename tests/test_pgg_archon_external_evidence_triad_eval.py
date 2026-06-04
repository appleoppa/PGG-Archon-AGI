from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_external_evidence_triad_eval import evaluate_triad, main


def test_evaluate_triad_scores_frozen_specs(tmp_path: Path) -> None:
    r = evaluate_triad(tmp_path)
    assert r.status == "PASS"
    assert r.benchmark_count == 100
    assert r.safety_count == 50
    assert r.benchmark_score == 1.0
    assert r.safety_score == 1.0
    assert r.research_score == 1.0
    assert "not a real provider benchmark" in r.boundary
    out = tmp_path / "triad_eval_result.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "PGGArchonExternalEvidenceTriadEval/v1"


def test_main_writes_eval_result(tmp_path: Path, capsys) -> None:
    assert main(["--output-dir", str(tmp_path)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "PASS"
    assert printed["benchmark_count"] == 100
    assert (tmp_path / "triad_eval_result.json").exists()
