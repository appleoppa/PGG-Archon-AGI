"""PGG Archon failed-example evolution proposal worker.

Boundary: read-only proposal generation from benchmark evolution queue items.
No provider calls, no filesystem mutation except explicit proposal output writes, no
patch application, no GeneDB promotion, and no policy/routing changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent.agi_task_benchmark import load_evolution_queue


@dataclass(frozen=True)
class EvolutionProposal:
    schema: str
    proposal_id: str
    created_at: str
    source_schema: str
    source_run_id: str
    source_task_id: str
    source_input_hash: str
    priority: str
    score_delta: float
    repair_focus: str
    proposed_actions: list[str]
    verification_plan: list[str]
    promotion_gate: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _repair_focus(item: Mapping[str, Any]) -> str:
    domain = str(item.get("domain") or "general")
    reason = str(item.get("failure_reason") or "")
    scorer = str(item.get("scorer") or "")
    if domain == "legal_boundary":
        return "truthful_boundary_guard"
    if "json" in scorer or "json" in reason.lower():
        return "structured_output_contract"
    if domain in {"math", "calculation"}:
        return "deterministic_calculation_guard"
    if "empty" in reason.lower() or not str(item.get("prediction") or "").strip():
        return "provider_empty_output_recovery"
    return "task_specific_prompt_or_capability_fix"


def _actions_for_focus(focus: str) -> list[str]:
    action_map = {
        "truthful_boundary_guard": [
            "Add or strengthen boundary-language regression fixture for this task/domain.",
            "Check whether the failing prompt path bypasses existing anti-overclaim / Delta-G gates.",
            "Require future patch to prove the model output contains the truthful boundary before promotion.",
        ],
        "structured_output_contract": [
            "Add a stricter structured-output fixture covering the failing scorer.",
            "Verify JSON extraction/normalization before changing provider prompts.",
            "Promote only after malformed and fenced JSON variants pass deterministic scoring.",
        ],
        "deterministic_calculation_guard": [
            "Route arithmetic-like tasks through deterministic tool/scorer fixtures where possible.",
            "Add regression case with expected answer and exact-normalized scorer.",
            "Verify no free-form explanation is accepted when exact output is required.",
        ],
        "provider_empty_output_recovery": [
            "Inspect provider raw response and extraction path before changing prompts.",
            "Add retry/extraction regression around empty visible output.",
            "Keep provider ranked WATCH until visible output and scoring both pass.",
        ],
    }
    return action_map.get(focus, [
        "Create a minimal regression fixture reproducing this failed queue item.",
        "Identify whether the fix belongs in prompt, scorer, routing, tool use, or capability code.",
        "Promote only after targeted test, integration smoke, and manifest readback pass.",
    ])


def _proposal_id(item: Mapping[str, Any], focus: str) -> str:
    payload = {
        "input_hash": item.get("input_hash"),
        "run_id": item.get("run_id"),
        "task_id": item.get("task_id"),
        "focus": focus,
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return f"proposal-{digest[:16]}"


def build_evolution_proposal(item: Mapping[str, Any]) -> EvolutionProposal:
    """Convert one failed-example queue item into an auditable repair proposal."""
    focus = _repair_focus(item)
    score_delta = float(item.get("score_delta", 0.0) or 0.0)
    return EvolutionProposal(
        schema="PGGArchonEvolutionProposal/v1",
        proposal_id=_proposal_id(item, focus),
        created_at=datetime.now(timezone.utc).isoformat(),
        source_schema=str(item.get("schema") or "unknown"),
        source_run_id=str(item.get("run_id") or ""),
        source_task_id=str(item.get("task_id") or ""),
        source_input_hash=str(item.get("input_hash") or ""),
        priority=str(item.get("priority") or "P2"),
        score_delta=score_delta,
        repair_focus=focus,
        proposed_actions=_actions_for_focus(focus),
        verification_plan=[
            "Reproduce the failed queue item with deterministic scoring.",
            "Apply the smallest targeted patch or skill update; do not mutate scheduler/security/provider boundaries by default.",
            "Run targeted unit tests and integrated benchmark smoke.",
            "Read back proposal, queue item, test output, and EVOLUTION_MANIFEST before promotion.",
        ],
        promotion_gate="proposal_only_until_verified_patch_or_skill_lands",
        boundary="Read-only proposal; not an automatic fix, not GeneDB promotion, not full AGI proof.",
    )


def build_evolution_proposals(queue_items: Sequence[Mapping[str, Any]], *, limit: int | None = None) -> list[EvolutionProposal]:
    """Build proposals from prioritized queue items."""
    selected = list(queue_items[:limit] if limit is not None else queue_items)
    return [build_evolution_proposal(item) for item in selected]


def write_evolution_proposals(
    queue_path: str | Path,
    *,
    output_dir: str | Path,
    limit: int | None = None,
) -> dict[str, Any]:
    """Load a queue, build proposals, and write JSON/JSONL evidence files."""
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    queue_items = load_evolution_queue(queue_path, limit=limit)
    proposals = build_evolution_proposals(queue_items)
    generated_at = datetime.now(timezone.utc).isoformat()
    result = {
        "schema": "PGGArchonEvolutionProposalBatch/v1",
        "generated_at": generated_at,
        "queue_path": str(Path(queue_path).expanduser()),
        "proposal_count": len(proposals),
        "proposals": [proposal.to_json_dict() for proposal in proposals],
        "boundary": "Read-only proposal batch; no patches, provider calls, policy changes, or GeneDB writes.",
    }
    batch_path = out / "evolution_proposals.json"
    jsonl_path = out / "evolution_proposals.jsonl"
    batch_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as f:
        for proposal in proposals:
            f.write(json.dumps(proposal.to_json_dict(), ensure_ascii=False) + "\n")
    return {
        "batch": str(batch_path),
        "jsonl": str(jsonl_path),
        "proposal_count": len(proposals),
        "generated_at": generated_at,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build read-only PGG Archon evolution proposals from a failed-example queue.")
    parser.add_argument("--queue", required=True, help="Path to PGGArchonEvolutionQueueItem JSONL file")
    parser.add_argument("--output-dir", required=True, help="Directory for proposal JSON/JSONL outputs")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of prioritized queue items to convert")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_evolution_proposals(args.queue, output_dir=args.output_dir, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by CLI smoke test
    raise SystemExit(main())
