from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_external_evidence_triad import run_triad


def test_run_triad_writes_all_outputs(tmp_path: Path) -> None:
    result = run_triad(tmp_path)
    assert result.status == "TRIAD_SMOKE_READY"
    assert result.benchmark["item_count"] == 5
    assert result.safety["item_count"] == 5
    assert result.research["success"] is True
    for name in [
        "external_benchmark_smoke.json",
        "safety_alignment_smoke.json",
        "research_artifact_smoke.json",
        "triad_run_result.json",
    ]:
        assert (tmp_path / name).exists()
    data = json.loads((tmp_path / "triad_run_result.json").read_text(encoding="utf-8"))
    assert "not official external benchmark" in data["boundary"]
