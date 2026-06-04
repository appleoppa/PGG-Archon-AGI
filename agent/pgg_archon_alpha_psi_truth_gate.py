"""PGG Archon Rust Alpha-Psi Truth Gate.

A deterministic truth-gate surface for the remaining Rust health pending dimension.
It checks whether the current AGI progress claims preserve the required boundaries:
- 33-card ACTIVE is engineering status, not full AGI
- Outline-1 score remains L1 evidence, not L2 proof
- MiniMax parse failures are preserved as non-PASS evidence
- Rust health is infrastructure evidence, not external AGI benchmark

Boundary: this is a truthfulness/completeness gate, not an AGI capability benchmark.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

HOME = Path.home()
MANIFEST = HOME / ".hermes/data/EVOLUTION_MANIFEST.json"
FINAL33 = HOME / ".hermes/workspace/audit/p3_final_33_active_20260604/p3_final_33_active_report.json"
OUTLINE1 = HOME / ".hermes/workspace/audit/p3_outline1_score_20260604/outline1_progress_comparison_report.json"
RUST_HEALTH = HOME / ".hermes/data/pgg-background-evolution/rust_health_snapshot.json"
MINIMAX_SCORE = HOME / ".hermes/workspace/audit/p3_outline1_score_20260604/deepseek_minimax_score.json"


@dataclass(frozen=True)
class TruthGateResult:
    schema: str
    status: str
    passed: int
    total: int
    checks: list[dict[str, Any]]
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def run_truth_gate() -> TruthGateResult:
    manifest = _json(MANIFEST)
    final33 = _json(FINAL33)
    outline1 = _json(OUTLINE1)
    rust = _json(RUST_HEALTH)
    minimax = _json(MINIMAX_SCORE).get("providers", {}).get("minimax", {})
    summary = manifest.get("summary", {})

    checks = [
        {
            "id": "final33_boundary",
            "passed": final33.get("status_distribution") == {"SKELETON": 0, "ABSENT": 0, "PARTIAL": 0, "ACTIVE": 33}
            and "not full AGI" in str(final33.get("boundary", "")),
            "evidence": str(final33.get("boundary", "")),
        },
        {
            "id": "outline1_l1_boundary",
            "passed": outline1.get("objective_summary", {}).get("structured_level") == "L1"
            and "not L2" in str(outline1.get("objective_summary", {}).get("interpretation", "")),
            "evidence": str(outline1.get("objective_summary", {}).get("interpretation", ""))[:300],
        },
        {
            "id": "minimax_parse_fail_preserved",
            "passed": minimax.get("ok") is False and minimax.get("error") == "json_parse_failed",
            "evidence": {"http_status": minimax.get("http_status"), "error": minimax.get("error")},
        },
        {
            "id": "rust_health_boundary",
            "passed": "not external AGI benchmark" in str(rust.get("boundary", ""))
            and rust.get("schema") in {"PGGArchonRustHealthSnapshot/v2", "PGGArchonRustHealthSnapshot/v3"},
            "evidence": {"schema": rust.get("schema"), "boundary": rust.get("boundary")},
        },
        {
            "id": "manifest_core_fusion_boundary",
            "passed": "not full AGI" in str(summary.get("latest_p3_final_33_active_20260604", {}).get("boundary", ""))
            and "not full AGI" in str(summary.get("latest_core_fusion_outline1_20260604", {}).get("boundary", "")),
            "evidence": {
                "final33": summary.get("latest_p3_final_33_active_20260604", {}).get("boundary"),
                "outline1": summary.get("latest_core_fusion_outline1_20260604", {}).get("boundary"),
            },
        },
    ]
    passed = sum(1 for c in checks if c["passed"])
    return TruthGateResult(
        schema="PGGArchonAlphaPsiTruthGate/v1",
        status="PASS" if passed == len(checks) else "WATCH",
        passed=passed,
        total=len(checks),
        checks=checks,
        boundary="Truth gate only; validates anti-overclaim evidence, not AGI capability.",
    )


def write_truth_gate(path: str | Path | None = None) -> dict[str, Any]:
    out = Path(path).expanduser() if path else HOME / ".hermes/data/pgg-background-evolution/alpha_psi_truth_gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    result = run_truth_gate()
    out.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(out), "status": result.status, "passed": result.passed, "total": result.total}


if __name__ == "__main__":
    print(json.dumps(write_truth_gate(), ensure_ascii=False, indent=2))
