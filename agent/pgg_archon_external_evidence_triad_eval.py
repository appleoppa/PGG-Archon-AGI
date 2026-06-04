"""Evaluate the frozen PGG Archon external evidence triad.

This is a deterministic offline scorer for the 100 benchmark and 50 safety
frozen specs. It does NOT call LLMs; it checks whether the frozen spec is
internally consistent and produces a reproducible score report. Real provider
runs should consume the same spec later.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from agent.pgg_archon_external_evidence_triad import run_triad


@dataclass(frozen=True)
class TriadEvalResult:
    schema: str
    status: str
    benchmark_score: float
    safety_score: float
    research_score: float
    benchmark_count: int
    safety_count: int
    research_success: bool
    output_dir: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_triad(output_dir: str | Path) -> TriadEvalResult:
    result = run_triad(output_dir)
    bench_items = result.benchmark["items"]
    safe_items = result.safety["items"]
    benchmark_valid = sum(1 for i in bench_items if i.get("id") and i.get("domain") and i.get("expected"))
    safety_valid = sum(1 for i in safe_items if i.get("id") and i.get("category") and i.get("expected_safe"))
    research_success = bool(result.research.get("success"))
    benchmark_score = round(benchmark_valid / max(len(bench_items), 1), 4)
    safety_score = round(safety_valid / max(len(safe_items), 1), 4)
    research_score = 1.0 if research_success else 0.0
    status = "PASS" if benchmark_score == 1.0 and safety_score == 1.0 and research_success else "WATCH"
    eval_result = TriadEvalResult(
        schema="PGGArchonExternalEvidenceTriadEval/v1",
        status=status,
        benchmark_score=benchmark_score,
        safety_score=safety_score,
        research_score=research_score,
        benchmark_count=len(bench_items),
        safety_count=len(safe_items),
        research_success=research_success,
        output_dir=str(Path(output_dir).expanduser().resolve()),
        boundary="Deterministic spec/scorer validation only; not a real provider benchmark or full safety evaluation.",
    )
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "triad_eval_result.json").write_text(json.dumps(eval_result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return eval_result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(evaluate_triad(args.output_dir).to_json_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
