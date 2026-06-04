"""PGG Archon LLM quorum gate.

Boundary: evaluates saved model-call evidence for a configurable quorum. It does
not call providers, promote genes, apply patches, or claim AGI.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class LLMQuorumGateResult:
    schema: str
    status: str
    required_pass_count: int
    visible_pass_count: int
    visible_count: int
    evidence_files: list[str]
    model_results: list[dict[str, Any]]
    blockers: list[str]
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {p}")
    return data


def _classify_from_text(text: str) -> str:
    low = text.lower()
    if re.search(r'"?model_verdict"?\s*[:=]\s*"?pass"?', low) or re.search(r'"?feasibility_ok"?\s*[:=]\s*true', low):
        if re.search(r'"?model_verdict"?\s*[:=]\s*"?(blocked|fail)', low):
            return "BLOCKED"
        return "PASS"
    if any(token in low for token in ["blocked", "not feasible", "do not proceed", "must not proceed"]):
        return "BLOCKED"
    return "UNKNOWN"


def _normalize_evidence(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser()
    data = _load_json(p)
    label = data.get("label") or data.get("provider") or p.stem
    status = str(data.get("status") or "")
    visible_chars = int(data.get("visible_output_chars") or 0)
    verdict = data.get("classified_verdict")
    if not verdict:
        verdict = _classify_from_text(str(data.get("text_preview") or data.get("output") or ""))
    return {
        "label": label,
        "provider": data.get("provider"),
        "model": data.get("model"),
        "status": status,
        "http_status": data.get("http_status"),
        "visible_output_chars": visible_chars,
        "classified_verdict": verdict,
        "evidence": str(p),
        "counts_as_pass": status == "ok_visible" and visible_chars > 0 and verdict == "PASS",
    }


def evaluate_llm_quorum_gate(evidence_files: Sequence[str | Path], *, required_pass_count: int = 2) -> LLMQuorumGateResult:
    model_results = [_normalize_evidence(path) for path in evidence_files]
    visible_count = sum(1 for item in model_results if item["status"] == "ok_visible" and item["visible_output_chars"] > 0)
    visible_pass_count = sum(1 for item in model_results if item["counts_as_pass"])
    blockers: list[str] = []
    if visible_pass_count < required_pass_count:
        blockers.append("visible_pass_count_below_threshold")
    if not evidence_files:
        blockers.append("missing_evidence_files")
    status = "PASS_QUORUM" if not blockers else "BLOCKED_QUORUM"
    return LLMQuorumGateResult(
        schema="PGGArchonLLMQuorumGateResult/v1",
        status=status,
        required_pass_count=required_pass_count,
        visible_pass_count=visible_pass_count,
        visible_count=visible_count,
        evidence_files=[str(Path(path).expanduser()) for path in evidence_files],
        model_results=model_results,
        blockers=blockers,
        boundary="Read-only LLM quorum gate over saved evidence; no provider calls, no mutation, no full AGI proof.",
    )


def write_llm_quorum_gate_result(*, evidence_files: Sequence[str | Path], output_dir: str | Path, required_pass_count: int = 2) -> dict[str, Any]:
    result = evaluate_llm_quorum_gate(evidence_files, required_pass_count=required_pass_count)
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "llm_quorum_gate_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "visible_pass_count": result.visible_pass_count, "blockers": result.blockers}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate read-only LLM quorum gate from saved evidence JSON files.")
    parser.add_argument("--evidence", action="append", required=True)
    parser.add_argument("--required-pass-count", type=int, default=2)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_llm_quorum_gate_result(evidence_files=args.evidence, output_dir=args.output_dir, required_pass_count=args.required_pass_count)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
