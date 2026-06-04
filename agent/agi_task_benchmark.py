"""Minimal AGI task benchmark harness.

This module creates a truthful, bounded loop:

    benchmark tasks -> predictions -> scoring -> failed examples -> evolution queue

Boundary: this is an internal task-evaluation harness. It is not an external AGI
benchmark result, not proof of AGI, and not proof of legal correctness.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class BenchmarkTask:
    """One benchmark task with deterministic scoring metadata."""

    task_id: str
    domain: str
    prompt: str
    expected: str
    scorer: str = "exact_normalized"
    weight: float = 1.0
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TaskScore:
    task_id: str
    domain: str
    prompt: str
    expected: str
    prediction: str
    scorer: str
    weight: float
    tags: tuple[str, ...]
    score: float
    passed: bool
    reason: str


@dataclass(frozen=True)
class BenchmarkRun:
    schema: str
    run_id: str
    generated_at: str
    status: str
    total_tasks: int
    passed_tasks: int
    weighted_score: float
    task_scores: list[TaskScore]
    failed_task_ids: list[str]
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["task_scores"] = [asdict(x) for x in self.task_scores]
        return data


def _strip_think_blocks(text: str) -> str:
    """Remove model reasoning wrappers from text used for deterministic scoring."""
    return re.sub(r"<think>.*?</think>", "", str(text), flags=re.IGNORECASE | re.DOTALL).strip()


def _normalize(text: Any) -> str:
    return " ".join(_strip_think_blocks(str(text)).strip().lower().split())


def _extract_json_candidate(text: Any) -> str:
    """Extract a deterministic JSON candidate from common model wrappers.

    This keeps scoring strict about JSON equality while allowing harmless
    Markdown fences such as ```json ... ``` that models often emit despite
    concise prompts.
    """
    raw = _strip_think_blocks(str(text)).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    first = raw.find("{")
    last = raw.rfind("}")
    if 0 <= first < last:
        return raw[first : last + 1].strip()
    return raw


def score_prediction(task: BenchmarkTask, prediction: Any) -> TaskScore:
    """Score one prediction with deterministic, transparent rules."""
    pred = str(prediction)
    expected = str(task.expected)
    scorer = task.scorer

    if scorer == "exact_normalized":
        passed = _normalize(pred) == _normalize(expected)
        score = 1.0 if passed else 0.0
        reason = "normalized exact match" if passed else "normalized exact mismatch"
    elif scorer == "contains_normalized":
        passed = _normalize(expected) in _normalize(pred)
        score = 1.0 if passed else 0.0
        reason = "prediction contains expected" if passed else "prediction does not contain expected"
    elif scorer == "json_key_value":
        try:
            pred_obj = json.loads(_extract_json_candidate(pred))
            exp_obj = json.loads(expected)
            passed = isinstance(pred_obj, dict) and pred_obj == exp_obj
            score = 1.0 if passed else 0.0
            reason = "json object equality" if passed else "json object mismatch"
        except Exception as exc:  # noqa: BLE001 - scorer must be robust to bad model output
            passed = False
            score = 0.0
            reason = f"json parse/scoring error: {type(exc).__name__}"
    else:
        raise ValueError(f"Unsupported scorer: {scorer}")

    return TaskScore(
        task_id=task.task_id,
        domain=task.domain,
        prompt=task.prompt,
        expected=expected,
        prediction=pred,
        scorer=scorer,
        weight=task.weight,
        tags=task.tags,
        score=score,
        passed=passed,
        reason=reason,
    )


def evaluate_predictions(
    tasks: Sequence[BenchmarkTask],
    predictions: Mapping[str, Any],
    *,
    run_id: str | None = None,
) -> BenchmarkRun:
    """Evaluate task predictions and return a structured run record."""
    if not tasks:
        raise ValueError("tasks must not be empty")
    run_id = run_id or datetime.now(timezone.utc).strftime("agi-bench-%Y%m%dT%H%M%SZ")
    scores: list[TaskScore] = []
    total_weight = 0.0
    weighted_sum = 0.0

    for task in tasks:
        if task.weight <= 0:
            raise ValueError(f"task {task.task_id} weight must be positive")
        prediction = predictions.get(task.task_id, "")
        score = score_prediction(task, prediction)
        scores.append(score)
        total_weight += task.weight
        weighted_sum += task.weight * score.score

    passed = sum(1 for item in scores if item.passed)
    weighted_score = round(weighted_sum / total_weight, 6)
    status = "PASS" if passed == len(tasks) else "WATCH" if passed > 0 else "BLOCKED"
    failed_ids = [item.task_id for item in scores if not item.passed]

    return BenchmarkRun(
        schema="PGGArchonAGITaskBenchmarkRun/v1",
        run_id=run_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        total_tasks=len(tasks),
        passed_tasks=passed,
        weighted_score=weighted_score,
        task_scores=scores,
        failed_task_ids=failed_ids,
        boundary=(
            "Internal deterministic task harness only; not an external AGI benchmark, "
            "not full AGI proof, and not legal correctness proof."
        ),
    )


def build_evolution_queue_item(run: BenchmarkRun, score: TaskScore) -> dict[str, Any]:
    """Build one actionable failed-example queue item.

    The queue item is intentionally append-only and self-contained enough for a
    later evolution worker to prioritize, replay, or promote into a verified
    patch/skill/gene. It does not auto-fix or mutate policy by itself.
    """
    payload_for_hash = {
        "run_id": run.run_id,
        "task_id": score.task_id,
        "domain": score.domain,
        "prompt": score.prompt,
        "scorer": score.scorer,
        "weight": score.weight,
        "tags": list(score.tags),
        "expected": score.expected,
        "prediction": score.prediction,
    }
    input_hash = hashlib.sha256(
        json.dumps(payload_for_hash, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    score_delta = round(1.0 - float(score.score), 6)
    priority = "P0" if score_delta >= 1.0 else "P1" if score_delta >= 0.5 else "P2"
    return {
        "schema": "PGGArchonEvolutionQueueItem/v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run.run_id,
        "task_id": score.task_id,
        "domain": score.domain,
        "prompt": score.prompt,
        "scorer": score.scorer,
        "weight": score.weight,
        "tags": list(score.tags),
        "score": score.score,
        "score_delta": score_delta,
        "priority": priority,
        "input_hash": input_hash,
        "attempt_type": "deterministic_benchmark_failure",
        "failure_reason": score.reason,
        "expected": score.expected,
        "prediction": score.prediction,
        "next_action": "analyze_failure_and_add_capability_or_prompt_fix",
        "promotion_gate": "verified_patch_or_skill_required_before_gene_promotion",
        "boundary": "queue item only; not auto-fixed until a verified patch lands",
    }


def write_benchmark_outputs(
    run: BenchmarkRun,
    *,
    output_dir: str | Path,
) -> dict[str, str]:
    """Write run JSON, task-score JSONL, and failed-task evolution queue."""
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    run_path = out / f"{run.run_id}.json"
    scores_path = out / f"{run.run_id}.scores.jsonl"
    queue_path = out / f"{run.run_id}.evolution_queue.jsonl"

    run_path.write_text(json.dumps(run.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    with scores_path.open("w", encoding="utf-8") as f:
        for score in run.task_scores:
            f.write(json.dumps(asdict(score), ensure_ascii=False) + "\n")
    with queue_path.open("w", encoding="utf-8") as f:
        for score in run.task_scores:
            if not score.passed:
                f.write(json.dumps(build_evolution_queue_item(run, score), ensure_ascii=False) + "\n")
    return {"run": str(run_path), "scores": str(scores_path), "evolution_queue": str(queue_path)}


def load_evolution_queue(path: str | Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Load and prioritize failed-example evolution queue records.

    This is read-only consumption support for later evolution workers. It never
    applies patches, promotes genes, or mutates policy by itself.
    """
    queue_path = Path(path).expanduser()
    items: list[dict[str, Any]] = []
    if not queue_path.exists():
        return items
    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    with queue_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                continue
            items.append(item)
    items.sort(
        key=lambda item: (
            priority_rank.get(str(item.get("priority", "P2")), 99),
            -float(item.get("score_delta", 0.0) or 0.0),
            str(item.get("created_at", "")),
        )
    )
    return items[:limit] if limit is not None else items


def load_tasks_jsonl(path: str | Path) -> list[BenchmarkTask]:
    """Load BenchmarkTask records from JSONL."""
    tasks: list[BenchmarkTask] = []
    with Path(path).expanduser().open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            tags = item.get("tags") or []
            tasks.append(BenchmarkTask(
                task_id=str(item["task_id"]),
                domain=str(item.get("domain", "general")),
                prompt=str(item["prompt"]),
                expected=str(item["expected"]),
                scorer=str(item.get("scorer", "exact_normalized")),
                weight=float(item.get("weight", 1.0)),
                tags=tuple(str(x) for x in tags),
            ))
    return tasks


def sample_tasks() -> list[BenchmarkTask]:
    """Small built-in smoke task set for harness verification."""
    return [
        BenchmarkTask(
            task_id="math-add-001",
            domain="math",
            prompt="Compute 19 + 23. Return only the integer.",
            expected="42",
        ),
        BenchmarkTask(
            task_id="json-transform-001",
            domain="tool_use",
            prompt="Return JSON {\"status\": \"ok\"} exactly.",
            expected='{"status":"ok"}',
            scorer="json_key_value",
        ),
        BenchmarkTask(
            task_id="legal-boundary-001",
            domain="legal_boundary",
            prompt="State the truthful boundary: this system is not full AGI.",
            expected="not full agi",
            scorer="contains_normalized",
        ),
    ]


def sample_predictions(*, perfect: bool = False) -> dict[str, str]:
    if perfect:
        return {
            "math-add-001": "42",
            "json-transform-001": '{"status":"ok"}',
            "legal-boundary-001": "This system is not full AGI.",
        }
    return {
        "math-add-001": "42",
        "json-transform-001": '{"status":"ok"}',
        "legal-boundary-001": "This is a full AGI system.",
    }


def run_sample(output_dir: str | Path, *, perfect: bool = False) -> dict[str, Any]:
    run = evaluate_predictions(sample_tasks(), sample_predictions(perfect=perfect), run_id="sample-perfect" if perfect else "sample-watch")
    paths = write_benchmark_outputs(run, output_dir=output_dir)
    return {"run": run.to_json_dict(), "paths": paths}
