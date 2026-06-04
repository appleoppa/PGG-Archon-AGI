"""PGG Archon read-only patch candidate sandbox.

Boundary: turns targeted regression fixtures into auditable patch-candidate plans.
It does not edit files, apply patches, call providers, write GeneDB, or mutate
scheduler/security/provider boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PatchCandidate:
    schema: str
    candidate_id: str
    created_at: str
    source_fixture_id: str
    source_input_hash: str
    repair_focus: str
    candidate_type: str
    target_surfaces: list[str]
    proposed_patch_steps: list[str]
    verification_commands: list[str]
    risk_level: str
    promotion_gate: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_fixture_batch(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected regression fixture batch object: {path}")
    return data


def _focus_from_fixture(fixture: Mapping[str, Any]) -> str:
    raw_task = fixture.get("benchmark_task")
    task: Mapping[str, Any] = raw_task if isinstance(raw_task, Mapping) else {}
    tags = task.get("tags", [])
    joined = " ".join(str(x) for x in tags)
    if "truthful_boundary_guard" in joined or task.get("domain") == "legal_boundary":
        return "truthful_boundary_guard"
    if "structured_output_contract" in joined or "json" in str(task.get("scorer", "")):
        return "structured_output_contract"
    if task.get("domain") in {"math", "calculation"}:
        return "deterministic_calculation_guard"
    return "task_specific_prompt_or_capability_fix"


def _candidate_id(fixture: Mapping[str, Any], focus: str) -> str:
    payload = {
        "fixture_id": fixture.get("fixture_id"),
        "source_input_hash": fixture.get("source_input_hash"),
        "focus": focus,
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return f"patch-candidate-{digest[:16]}"


def _surfaces_for_focus(focus: str) -> list[str]:
    if focus == "truthful_boundary_guard":
        return [
            "agent/agi_task_benchmark.py",
            "agent/pgg_archon_delta_gate.py",
            "tests/test_agi_task_benchmark.py",
            "tests/test_pgg_archon_regression_generator.py",
        ]
    if focus == "structured_output_contract":
        return ["agent/agi_task_benchmark.py", "tests/test_agi_task_benchmark.py"]
    if focus == "deterministic_calculation_guard":
        return ["agent/agi_task_benchmark.py", "tools/", "tests/test_agi_task_benchmark.py"]
    return ["agent/", "tests/"]


def _steps_for_focus(focus: str) -> list[str]:
    if focus == "truthful_boundary_guard":
        return [
            "Add the generated regression task to a bounded regression fixture set or test helper.",
            "Verify the previous overclaiming prediction fails deterministic scoring.",
            "Verify a truthful boundary response passes deterministic scoring.",
            "If failures originate upstream, inspect Delta-G/anti-overclaim gate before changing provider prompts.",
        ]
    if focus == "structured_output_contract":
        return [
            "Add generated JSON regression fixture to deterministic scorer coverage.",
            "Verify malformed/fenced/explanatory JSON behavior before changing model prompts.",
            "Patch extraction/scoring only if the generated fixture proves a deterministic gap.",
        ]
    return [
        "Add generated regression fixture as the minimal reproducer.",
        "Patch only the smallest prompt/scorer/tool/capability surface proven by the fixture.",
        "Run targeted tests and integrated benchmark smoke before promotion.",
    ]


def build_patch_candidate(fixture: Mapping[str, Any]) -> PatchCandidate:
    focus = _focus_from_fixture(fixture)
    risk = "LOW" if focus in {"truthful_boundary_guard", "structured_output_contract"} else "MEDIUM"
    return PatchCandidate(
        schema="PGGArchonPatchCandidate/v1",
        candidate_id=_candidate_id(fixture, focus),
        created_at=datetime.now(timezone.utc).isoformat(),
        source_fixture_id=str(fixture.get("fixture_id") or ""),
        source_input_hash=str(fixture.get("source_input_hash") or ""),
        repair_focus=focus,
        candidate_type="read_only_patch_plan",
        target_surfaces=_surfaces_for_focus(focus),
        proposed_patch_steps=_steps_for_focus(focus),
        verification_commands=[
            "python -m pytest tests/test_agi_task_benchmark.py tests/test_pgg_archon_regression_generator.py -q",
            "python -m pytest tests/test_pgg_archon_benchmark_loop.py tests/test_pgg_archon_provider_health_gate.py -q",
            "python -m py_compile agent/agi_task_benchmark.py agent/pgg_archon_regression_generator.py",
            "git diff --check",
        ],
        risk_level=risk,
        promotion_gate="candidate_plan_only_until_patch_is_applied_and_tests_manifest_readback_pass",
        boundary="Read-only patch candidate plan; no file edits or GeneDB promotion performed.",
    )


def build_patch_candidates(fixture_batch_path: str | Path, *, limit: int | None = None) -> list[PatchCandidate]:
    batch = _load_fixture_batch(fixture_batch_path)
    fixtures = batch.get("fixtures", [])
    if not isinstance(fixtures, list):
        raise ValueError("fixture batch must contain list field: fixtures")
    selected = [item for item in fixtures if isinstance(item, dict)]
    if limit is not None:
        selected = selected[:limit]
    return [build_patch_candidate(item) for item in selected]


def write_patch_candidates(fixture_batch_path: str | Path, *, output_dir: str | Path, limit: int | None = None) -> dict[str, Any]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    candidates = build_patch_candidates(fixture_batch_path, limit=limit)
    payload = {
        "schema": "PGGArchonPatchCandidateBatch/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixture_batch_path": str(Path(fixture_batch_path).expanduser()),
        "candidate_count": len(candidates),
        "candidates": [candidate.to_json_dict() for candidate in candidates],
        "boundary": "Read-only patch candidates only; no patches applied, no provider calls, no GeneDB writes.",
    }
    batch_path = out / "patch_candidates.json"
    jsonl_path = out / "patch_candidates.jsonl"
    batch_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as f:
        for candidate in candidates:
            f.write(json.dumps(candidate.to_json_dict(), ensure_ascii=False) + "\n")
    return {"batch": str(batch_path), "jsonl": str(jsonl_path), "candidate_count": len(candidates)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build read-only patch candidates from targeted regression fixtures.")
    parser.add_argument("--fixtures", required=True, help="Path to targeted_regression_fixtures.json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_patch_candidates(args.fixtures, output_dir=args.output_dir, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
