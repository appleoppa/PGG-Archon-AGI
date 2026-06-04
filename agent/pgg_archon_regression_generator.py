"""PGG Archon targeted regression generator.

Boundary: converts verified failed-example queue items and read-only evolution
proposals into deterministic BenchmarkTask JSONL fixtures. It does not patch code,
call providers, write GeneDB, or mutate scheduler/security/provider boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent.agi_task_benchmark import BenchmarkTask, load_evolution_queue


@dataclass(frozen=True)
class RegressionFixture:
    schema: str
    generated_at: str
    fixture_id: str
    source_proposal_id: str
    source_input_hash: str
    benchmark_task: dict[str, Any]
    expected_failure_prediction: str
    verification_note: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _proposal_items(path: str | Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    proposals = data.get("proposals", [])
    if not isinstance(proposals, list):
        raise ValueError("proposal batch must contain a list field: proposals")
    return [item for item in proposals if isinstance(item, dict)]


def _queue_index(queue_paths: Sequence[str | Path]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for queue_path in queue_paths:
        for item in load_evolution_queue(queue_path):
            input_hash = str(item.get("input_hash") or "")
            if input_hash:
                indexed[input_hash] = item
    return indexed


def _fixture_id(proposal: Mapping[str, Any], queue_item: Mapping[str, Any]) -> str:
    payload = {
        "proposal_id": proposal.get("proposal_id"),
        "input_hash": queue_item.get("input_hash"),
        "task_id": queue_item.get("task_id"),
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return f"regression-{digest[:16]}"


def build_regression_fixture(proposal: Mapping[str, Any], queue_item: Mapping[str, Any]) -> RegressionFixture:
    """Build one deterministic regression fixture from a proposal and source queue item."""
    source_hash = str(queue_item.get("input_hash") or proposal.get("source_input_hash") or "")
    task = BenchmarkTask(
        task_id=f"regression-{queue_item.get('task_id', 'unknown')}-{source_hash[:8]}",
        domain=str(queue_item.get("domain") or "general"),
        prompt=str(queue_item.get("prompt") or ""),
        expected=str(queue_item.get("expected") or ""),
        scorer=str(queue_item.get("scorer") or "exact_normalized"),
        weight=float(queue_item.get("weight", 1.0) or 1.0),
        tags=tuple(["regression", "autonomous_evolution", str(proposal.get("repair_focus") or "unknown_focus")]),
    )
    return RegressionFixture(
        schema="PGGArchonTargetedRegressionFixture/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        fixture_id=_fixture_id(proposal, queue_item),
        source_proposal_id=str(proposal.get("proposal_id") or ""),
        source_input_hash=source_hash,
        benchmark_task=asdict(task),
        expected_failure_prediction=str(queue_item.get("prediction") or ""),
        verification_note="Run this BenchmarkTask through deterministic scoring; the previous failing prediction should fail and the repaired path should pass.",
        boundary="Regression fixture only; not a patch, not provider output, not GeneDB promotion.",
    )


def build_regression_fixtures(
    proposal_batch_path: str | Path,
    queue_paths: Sequence[str | Path],
    *,
    limit: int | None = None,
) -> list[RegressionFixture]:
    proposals = _proposal_items(proposal_batch_path)
    queues = _queue_index(queue_paths)
    fixtures: list[RegressionFixture] = []
    for proposal in proposals:
        source_hash = str(proposal.get("source_input_hash") or "")
        queue_item = queues.get(source_hash)
        if not queue_item:
            continue
        fixtures.append(build_regression_fixture(proposal, queue_item))
        if limit is not None and len(fixtures) >= limit:
            break
    return fixtures


def write_regression_fixtures(
    proposal_batch_path: str | Path,
    queue_paths: Sequence[str | Path],
    *,
    output_dir: str | Path,
    limit: int | None = None,
) -> dict[str, Any]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    fixtures = build_regression_fixtures(proposal_batch_path, queue_paths, limit=limit)
    tasks_path = out / "targeted_regression_tasks.jsonl"
    fixtures_path = out / "targeted_regression_fixtures.json"
    with tasks_path.open("w", encoding="utf-8") as f:
        for fixture in fixtures:
            f.write(json.dumps(fixture.benchmark_task, ensure_ascii=False) + "\n")
    payload = {
        "schema": "PGGArchonTargetedRegressionBatch/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "proposal_batch_path": str(Path(proposal_batch_path).expanduser()),
        "queue_paths": [str(Path(x).expanduser()) for x in queue_paths],
        "fixture_count": len(fixtures),
        "fixtures": [fixture.to_json_dict() for fixture in fixtures],
        "tasks_jsonl": str(tasks_path),
        "boundary": "Deterministic regression fixtures only; no code patch, provider call, scheduler mutation, or GeneDB write.",
    }
    fixtures_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"fixtures": str(fixtures_path), "tasks_jsonl": str(tasks_path), "fixture_count": len(fixtures)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build targeted regression fixtures from PGG evolution proposals.")
    parser.add_argument("--proposal-batch", required=True, help="Path to evolution_proposals.json")
    parser.add_argument("--queue", action="append", required=True, help="Source evolution queue JSONL; repeatable")
    parser.add_argument("--output-dir", required=True, help="Output directory for regression fixtures")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_regression_fixtures(args.proposal_batch, args.queue, output_dir=args.output_dir, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
