from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_evolution_proposal import (
    build_evolution_proposal,
    build_evolution_proposals,
    main,
    write_evolution_proposals,
)


def _queue_item(**overrides):
    item = {
        "schema": "PGGArchonEvolutionQueueItem/v2",
        "created_at": "2026-06-04T00:00:00Z",
        "run_id": "unit-run",
        "task_id": "legal-boundary-001",
        "domain": "legal_boundary",
        "prompt": "State the truthful boundary: this system is not full AGI.",
        "scorer": "contains_normalized",
        "weight": 1.0,
        "tags": [],
        "score": 0.0,
        "score_delta": 1.0,
        "priority": "P0",
        "input_hash": "a" * 64,
        "attempt_type": "deterministic_benchmark_failure",
        "failure_reason": "prediction does not contain expected",
        "expected": "not full agi",
        "prediction": "This is a full AGI system.",
        "next_action": "analyze_failure_and_add_capability_or_prompt_fix",
        "promotion_gate": "verified_patch_or_skill_required_before_gene_promotion",
        "boundary": "queue item only; not auto-fixed until a verified patch lands",
    }
    item.update(overrides)
    return item


def test_build_evolution_proposal_for_legal_boundary_failure() -> None:
    proposal = build_evolution_proposal(_queue_item())
    data = proposal.to_json_dict()
    assert data["schema"] == "PGGArchonEvolutionProposal/v1"
    assert data["source_schema"] == "PGGArchonEvolutionQueueItem/v2"
    assert data["source_task_id"] == "legal-boundary-001"
    assert data["source_input_hash"] == "a" * 64
    assert data["priority"] == "P0"
    assert data["score_delta"] == 1.0
    assert data["repair_focus"] == "truthful_boundary_guard"
    assert "Delta-G" in " ".join(data["proposed_actions"])
    assert data["promotion_gate"] == "proposal_only_until_verified_patch_or_skill_lands"
    assert "not an automatic fix" in data["boundary"]


def test_build_evolution_proposals_honors_limit() -> None:
    items = [
        _queue_item(task_id="a", input_hash="a" * 64),
        _queue_item(task_id="b", input_hash="b" * 64, domain="math"),
    ]
    proposals = build_evolution_proposals(items, limit=1)
    assert len(proposals) == 1
    assert proposals[0].source_task_id == "a"


def test_write_evolution_proposals_outputs_batch_and_jsonl(tmp_path: Path) -> None:
    queue = tmp_path / "queue.jsonl"
    queue.write_text(
        "\n".join([
            json.dumps(_queue_item(task_id="low", priority="P2", score_delta=0.2, input_hash="c" * 64)),
            json.dumps(_queue_item(task_id="high", priority="P0", score_delta=1.0, input_hash="d" * 64)),
        ]) + "\n",
        encoding="utf-8",
    )
    paths = write_evolution_proposals(queue, output_dir=tmp_path / "out", limit=1)
    assert paths["proposal_count"] == 1
    batch = json.loads(Path(paths["batch"]).read_text(encoding="utf-8"))
    assert batch["schema"] == "PGGArchonEvolutionProposalBatch/v1"
    assert batch["proposal_count"] == 1
    assert batch["proposals"][0]["source_task_id"] == "high"
    assert Path(paths["jsonl"]).read_text(encoding="utf-8").count("\n") == 1
    assert "no patches" in batch["boundary"]


def test_main_writes_proposals_from_cli_args(tmp_path: Path, capsys) -> None:
    queue = tmp_path / "queue.jsonl"
    queue.write_text(json.dumps(_queue_item(task_id="cli", input_hash="e" * 64)) + "\n", encoding="utf-8")
    output_dir = tmp_path / "cli-out"
    assert main(["--queue", str(queue), "--output-dir", str(output_dir), "--limit", "1"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["proposal_count"] == 1
    assert Path(printed["batch"]).is_file()
    assert Path(printed["jsonl"]).is_file()
