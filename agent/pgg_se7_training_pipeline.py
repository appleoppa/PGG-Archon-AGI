#!/usr/bin/env python3
"""
SE7 ClawG Training Sandbox Pipeline
===================================

Internal PGG Archon training workflow for SE7 / ClawG sandbox experiments.
This module is intentionally local-only: it does not call external models or
claim AGI/T5 capability. It materializes the SE7 formulas as auditable Python
components:

    Task_APEX      = PersonaIntent × SkillGrounding × MockWorkspace
    Agent_APEX     = SFT_Trajectory + RL_Rollout × SandboxParallel
    Score_APEX     = AutoVerify(60%) + LLM_HumanVerify(40%)
    Iteration_APEX = Data → Train → Bench → Feedback
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", HOME / ".hermes")).expanduser()
REPO_ROOT = HERMES_HOME / "hermes-agent"
DATA_ROOT = HERMES_HOME / "data" / "pgg-se7-training"
TASK_ROOT = DATA_ROOT / "tasks"
ROLL_OUT_ROOT = DATA_ROOT / "rollouts"
BENCH_ROOT = DATA_ROOT / "bench"
STATE_FILE = DATA_ROOT / "pipeline_state.json"

AUTO_VERIFY_WEIGHT = 0.60
LLM_HUMAN_VERIFY_WEIGHT = 0.40


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    for path in (DATA_ROOT, TASK_ROOT, ROLL_OUT_ROOT, BENCH_ROOT):
        path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{int(time.time())}_{digest}"


def _state() -> dict[str, Any]:
    _ensure_dirs()
    state = _read_json(STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("created_at", _utc_now())
    state.setdefault("updated_at", _utc_now())
    state.setdefault("tasks_generated", 0)
    state.setdefault("tasks_scored", 0)
    state.setdefault("sft_trajectories", 0)
    state.setdefault("rl_rollouts", 0)
    state.setdefault("sandbox_parallel_runs", 0)
    state.setdefault("iteration_loops", 0)
    state.setdefault("last_task_dir", None)
    state.setdefault("last_score", None)
    state.setdefault("last_feedback", None)
    return state


def _save_state(update: dict[str, Any]) -> dict[str, Any]:
    state = _state()
    state.update(update)
    state["updated_at"] = _utc_now()
    _write_json(STATE_FILE, state)
    return state


def _list_task_dirs() -> list[Path]:
    _ensure_dirs()
    return sorted([p for p in TASK_ROOT.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)


def _safe_read_text(path: Path, limit: int = 8000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[:limit]
    except Exception:
        return ""


@dataclass
class ComponentStatus:
    """Small serializable status envelope used by every SE7 component."""

    component: str
    status: str
    updated_at: str = field(default_factory=_utc_now)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TaskGenerator:
    """Task_APEX = PersonaIntent × SkillGrounding × MockWorkspace.

    Responsibilities:
      - PersonaIntent management: keeps a local roster of training personas.
      - SkillGrounding binding: attaches task objectives to concrete Hermes skills.
      - MockWorkspace management: creates isolated task directories and fixtures.
    """

    DEFAULT_PERSONA_INTENTS = [
        {"persona": "archon_operator", "intent": "diagnose_and_patch_local_pipeline", "risk": "low"},
        {"persona": "skill_curator", "intent": "ground_skill_usage_into_replayable_steps", "risk": "low"},
        {"persona": "sandbox_reviewer", "intent": "verify_artifacts_without_external_calls", "risk": "low"},
    ]
    DEFAULT_SKILL_GROUNDING = [
        {"skill": "filesystem", "capabilities": ["read", "write", "verify"]},
        {"skill": "terminal", "capabilities": ["import_check", "unit_smoke", "status"]},
        {"skill": "pgg_governance", "capabilities": ["manifest", "rubric", "feedback"]},
    ]

    def __init__(
        self,
        persona_intents: list[dict[str, Any]] | None = None,
        skill_grounding: list[dict[str, Any]] | None = None,
        task_root: Path | str = TASK_ROOT,
    ) -> None:
        _ensure_dirs()
        self.persona_intents = persona_intents or list(self.DEFAULT_PERSONA_INTENTS)
        self.skill_grounding = skill_grounding or list(self.DEFAULT_SKILL_GROUNDING)
        self.task_root = Path(task_root)
        self.last_status = ComponentStatus("TaskGenerator", "initialized")

    def bind_skill_grounding(self, persona_intent: dict[str, Any]) -> dict[str, Any]:
        seed = persona_intent.get("intent", "") + persona_intent.get("persona", "")
        idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(self.skill_grounding)
        return self.skill_grounding[idx]

    def create_mock_workspace(self, task_dir: Path, task_spec: dict[str, Any]) -> Path:
        workspace = task_dir / "mock_workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "README.md").write_text(
            "# SE7 ClawG Mock Workspace\n\n"
            f"Task: {task_spec['task_id']}\n"
            "Boundary: local sandbox only; no external model calls.\n",
            encoding="utf-8",
        )
        (workspace / "input.md").write_text(
            "## Operator Request\n"
            f"Persona `{task_spec['persona_intent']['persona']}` must complete intent "
            f"`{task_spec['persona_intent']['intent']}` using grounded skill "
            f"`{task_spec['skill_grounding']['skill']}`.\n",
            encoding="utf-8",
        )
        (workspace / "expected.json").write_text(
            json.dumps(
                {
                    "required_files": ["README.md", "input.md"],
                    "success_criteria": [
                        "task_spec_present",
                        "workspace_isolated",
                        "skill_grounding_declared",
                        "no_external_model_call",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return workspace

    def generate_task(self, persona_index: int | None = None) -> dict[str, Any]:
        if persona_index is None:
            persona_index = int(time.time()) % len(self.persona_intents)
        persona_intent = self.persona_intents[persona_index % len(self.persona_intents)]
        skill = self.bind_skill_grounding(persona_intent)
        task_spec = {
            "schema": "pgg.se7.clawg.task.v1",
            "created_at": _utc_now(),
            "formula": "Task_APEX = PersonaIntent × SkillGrounding × MockWorkspace",
            "persona_intent": persona_intent,
            "skill_grounding": skill,
            "boundaries": ["internal_training_workflow", "no_external_model_calls", "no_agi_t5_claims"],
            "objective": "Produce a replayable sandbox trajectory that satisfies the local verification rubric.",
        }
        task_id = _stable_id("se7_task", task_spec)
        task_spec["task_id"] = task_id
        task_dir = self.task_root / task_id
        task_dir.mkdir(parents=True, exist_ok=False)
        workspace = self.create_mock_workspace(task_dir, task_spec)
        task_spec["mock_workspace"] = str(workspace)
        _write_json(task_dir / "task.json", task_spec)
        _write_json(task_dir / "status.json", {"status": "generated", "updated_at": _utc_now()})
        state = _state()
        _save_state({"tasks_generated": int(state.get("tasks_generated", 0)) + 1, "last_task_dir": str(task_dir)})
        self.last_status = ComponentStatus(
            "TaskGenerator",
            "task_generated",
            details={"task_id": task_id, "task_dir": str(task_dir), "persona": persona_intent["persona"], "skill": skill["skill"]},
        )
        return {"task_dir": str(task_dir), "task": task_spec, "status": self.last_status.to_dict()}

    def run(self) -> dict[str, Any]:
        return self.generate_task()

    def status_report(self) -> dict[str, Any]:
        return self.last_status.to_dict()


class TrainingPipeline:
    """Agent_APEX = SFT_Trajectory + RL_Rollout × SandboxParallel.

    This local training pipeline creates auditable trajectory and rollout records
    from generated sandbox tasks. It does not train a production model; it stages
    data for internal ClawG iteration and benchmark feedback.
    """

    def __init__(self, task_root: Path | str = TASK_ROOT, rollout_root: Path | str = ROLL_OUT_ROOT) -> None:
        _ensure_dirs()
        self.task_root = Path(task_root)
        self.rollout_root = Path(rollout_root)
        self.last_status = ComponentStatus("TrainingPipeline", "initialized")

    def collect_sft_trajectory(self, task_dir: Path) -> dict[str, Any]:
        task = _read_json(task_dir / "task.json", {})
        trajectory = {
            "schema": "pgg.se7.clawg.sft_trajectory.v1",
            "created_at": _utc_now(),
            "task_id": task.get("task_id", task_dir.name),
            "task_dir": str(task_dir),
            "messages": [
                {"role": "user", "content": _safe_read_text(task_dir / "mock_workspace" / "input.md")},
                {"role": "assistant", "content": "Inspect task.json, operate only inside mock_workspace, emit verification artifacts."},
            ],
            "labels": ["local_sandbox", "skill_grounded", "replayable"],
        }
        _write_json(task_dir / "sft_trajectory.json", trajectory)
        return trajectory

    def schedule_rl_rollout(self, task_dir: Path, trajectory: dict[str, Any]) -> dict[str, Any]:
        rollout = {
            "schema": "pgg.se7.clawg.rl_rollout.v1",
            "created_at": _utc_now(),
            "formula": "Agent_APEX = SFT_Trajectory + RL_Rollout × SandboxParallel",
            "task_id": trajectory.get("task_id", task_dir.name),
            "sandbox_parallel": {
                "lanes": ["plan", "act", "verify"],
                "max_workers": 3,
                "execution_mode": "local_deterministic",
            },
            "policy_steps": [
                "read_task_spec",
                "validate_workspace_boundary",
                "write_solution_trace",
                "run_auto_verify",
            ],
        }
        _write_json(task_dir / "rl_rollout.json", rollout)
        _write_json(self.rollout_root / f"{task_dir.name}.json", rollout)
        return rollout

    def execute_sandbox_parallel(self, task_dir: Path, rollout: dict[str, Any]) -> dict[str, Any]:
        workspace = task_dir / "mock_workspace"
        trace = {
            "schema": "pgg.se7.clawg.sandbox_parallel_result.v1",
            "created_at": _utc_now(),
            "task_id": rollout.get("task_id", task_dir.name),
            "lane_results": {
                "plan": {"ok": (task_dir / "task.json").exists(), "note": "task_spec_checked"},
                "act": {"ok": workspace.exists(), "note": "workspace_boundary_checked"},
                "verify": {"ok": (workspace / "expected.json").exists(), "note": "expected_rubric_checked"},
            },
        }
        trace["ok"] = all(item["ok"] for item in trace["lane_results"].values())
        _write_json(task_dir / "sandbox_parallel_result.json", trace)
        _write_json(task_dir / "status.json", {"status": "rolled_out", "updated_at": _utc_now(), "ok": trace["ok"]})
        return trace

    def run(self, task_dirs: Iterable[Path | str] | None = None, limit: int = 5) -> dict[str, Any]:
        if task_dirs is None:
            task_dirs = _list_task_dirs()[:limit]
        results = []
        for raw in task_dirs:
            task_dir = Path(raw)
            if not (task_dir / "task.json").exists():
                continue
            trajectory = self.collect_sft_trajectory(task_dir)
            rollout = self.schedule_rl_rollout(task_dir, trajectory)
            sandbox = self.execute_sandbox_parallel(task_dir, rollout)
            results.append({"task_dir": str(task_dir), "trajectory": trajectory, "rollout": rollout, "sandbox": sandbox})
        state = _state()
        _save_state(
            {
                "sft_trajectories": int(state.get("sft_trajectories", 0)) + len(results),
                "rl_rollouts": int(state.get("rl_rollouts", 0)) + len(results),
                "sandbox_parallel_runs": int(state.get("sandbox_parallel_runs", 0)) + len(results),
            }
        )
        self.last_status = ComponentStatus("TrainingPipeline", "completed", details={"processed": len(results)})
        return {"processed": len(results), "results": results, "status": self.last_status.to_dict()}

    def status_report(self) -> dict[str, Any]:
        return self.last_status.to_dict()


class ScoringEngine:
    """Score_APEX = AutoVerify(60%) + LLM_HumanVerify(40%).

    The LLM_HumanVerify portion is represented by a local human-review rubric
    proxy to keep this module offline and deterministic. A future internal review
    queue can replace the proxy without changing the weighted score contract.
    """

    def __init__(self) -> None:
        _ensure_dirs()
        self.last_status = ComponentStatus("ScoringEngine", "initialized")

    def auto_verify(self, task_dir: Path) -> dict[str, Any]:
        checks = {
            "task_json_exists": (task_dir / "task.json").exists(),
            "mock_workspace_exists": (task_dir / "mock_workspace").is_dir(),
            "expected_json_exists": (task_dir / "mock_workspace" / "expected.json").exists(),
            "sft_trajectory_exists": (task_dir / "sft_trajectory.json").exists(),
            "rl_rollout_exists": (task_dir / "rl_rollout.json").exists(),
            "sandbox_result_exists": (task_dir / "sandbox_parallel_result.json").exists(),
        }
        score = sum(1 for ok in checks.values() if ok) / max(len(checks), 1)
        return {"score": round(score, 4), "checks": checks, "weight": AUTO_VERIFY_WEIGHT}

    def llm_human_verify(self, task_dir: Path) -> dict[str, Any]:
        task = _read_json(task_dir / "task.json", {})
        rollout = _read_json(task_dir / "rl_rollout.json", {})
        sandbox = _read_json(task_dir / "sandbox_parallel_result.json", {})
        rubric = {
            "persona_intent_declared": bool(task.get("persona_intent")),
            "skill_grounding_declared": bool(task.get("skill_grounding")),
            "boundaries_declared": "no_external_model_calls" in task.get("boundaries", []),
            "sandbox_parallel_ok": bool(sandbox.get("ok")),
            "rollout_policy_steps_present": bool(rollout.get("policy_steps")),
        }
        score = sum(1 for ok in rubric.values() if ok) / max(len(rubric), 1)
        return {
            "score": round(score, 4),
            "rubric": rubric,
            "weight": LLM_HUMAN_VERIFY_WEIGHT,
            "mode": "local_rubric_proxy_no_external_llm",
        }

    def score(self, task_dir: Path | str) -> dict[str, Any]:
        task_dir = Path(task_dir).expanduser()
        if not task_dir.exists():
            raise FileNotFoundError(f"task_dir not found: {task_dir}")
        auto = self.auto_verify(task_dir)
        human = self.llm_human_verify(task_dir)
        final_score = (auto["score"] * AUTO_VERIFY_WEIGHT) + (human["score"] * LLM_HUMAN_VERIFY_WEIGHT)
        result = {
            "schema": "pgg.se7.clawg.score.v1",
            "created_at": _utc_now(),
            "formula": "Score_APEX = AutoVerify(60%) + LLM_HumanVerify(40%)",
            "task_dir": str(task_dir),
            "task_id": _read_json(task_dir / "task.json", {}).get("task_id", task_dir.name),
            "auto_verify": auto,
            "llm_human_verify": human,
            "final_score": round(final_score, 4),
            "pass": final_score >= 0.80,
        }
        _write_json(task_dir / "score.json", result)
        _write_json(task_dir / "status.json", {"status": "scored", "updated_at": _utc_now(), "score": result["final_score"]})
        state = _state()
        _save_state({"tasks_scored": int(state.get("tasks_scored", 0)) + 1, "last_score": result})
        self.last_status = ComponentStatus("ScoringEngine", "scored", details={"task_dir": str(task_dir), "score": result["final_score"]})
        return result

    def run(self, task_dir: Path | str | None = None) -> dict[str, Any]:
        if task_dir is None:
            tasks = _list_task_dirs()
            if not tasks:
                raise FileNotFoundError("no SE7 task directories found; run generate-task first")
            task_dir = tasks[0]
        return self.score(task_dir)

    def status_report(self) -> dict[str, Any]:
        return self.last_status.to_dict()


class IterationLoop:
    """Iteration_APEX = Data → Train → Bench → Feedback."""

    def __init__(self) -> None:
        _ensure_dirs()
        self.task_generator = TaskGenerator()
        self.training_pipeline = TrainingPipeline()
        self.scoring_engine = ScoringEngine()
        self.last_status = ComponentStatus("IterationLoop", "initialized")

    def feedback(self, task_dir: Path, score: dict[str, Any]) -> dict[str, Any]:
        feedback = {
            "schema": "pgg.se7.clawg.feedback.v1",
            "created_at": _utc_now(),
            "task_dir": str(task_dir),
            "score": score.get("final_score"),
            "pass": score.get("pass"),
            "recommendations": [],
        }
        if score.get("final_score", 0) < 0.80:
            feedback["recommendations"].append("increase_workspace_artifact_completeness")
            feedback["recommendations"].append("ensure_rollout_and_sandbox_results_are_generated_before_scoring")
        else:
            feedback["recommendations"].append("promote_to_internal_bench_seed")
        _write_json(task_dir / "feedback.json", feedback)
        _write_json(BENCH_ROOT / f"{task_dir.name}.feedback.json", feedback)
        _save_state({"last_feedback": feedback})
        return feedback

    def run(self) -> dict[str, Any]:
        data = self.task_generator.run()
        task_dir = Path(data["task_dir"])
        train = self.training_pipeline.run([task_dir])
        bench = self.scoring_engine.run(task_dir)
        feedback = self.feedback(task_dir, bench)
        state = _state()
        _save_state({"iteration_loops": int(state.get("iteration_loops", 0)) + 1})
        self.last_status = ComponentStatus(
            "IterationLoop",
            "completed",
            details={"task_dir": str(task_dir), "score": bench.get("final_score"), "pass": bench.get("pass")},
        )
        return {
            "formula": "Iteration_APEX = Data → Train → Bench → Feedback",
            "data": data,
            "train": train,
            "bench": bench,
            "feedback": feedback,
            "status": self.last_status.to_dict(),
        }

    def status_report(self) -> dict[str, Any]:
        return self.last_status.to_dict()


def pipeline_status() -> dict[str, Any]:
    _ensure_dirs()
    state = _state()
    tasks = _list_task_dirs()
    scored = [p for p in tasks if (p / "score.json").exists()]
    return {
        "schema": "pgg.se7.clawg.pipeline_status.v1",
        "updated_at": _utc_now(),
        "data_root": str(DATA_ROOT),
        "task_root": str(TASK_ROOT),
        "task_count_on_disk": len(tasks),
        "scored_task_count_on_disk": len(scored),
        "state": state,
        "components": {
            "TaskGenerator": "ready",
            "TrainingPipeline": "ready",
            "ScoringEngine": "ready",
            "IterationLoop": "ready",
        },
    }


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SE7 ClawG training sandbox pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="显示管线状态")
    sub.add_parser("generate-task", help="生成训练任务")
    score = sub.add_parser("score", help="评分指定 task_dir")
    score.add_argument("task_dir", help="Task directory created by generate-task")
    sub.add_parser("run-loop", help="运行 Data → Train → Bench → Feedback 闭环")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            _print_json(pipeline_status())
        elif args.command == "generate-task":
            _print_json(TaskGenerator().run())
        elif args.command == "score":
            task_dir = Path(args.task_dir).expanduser()
            if not (task_dir / "rl_rollout.json").exists():
                TrainingPipeline().run([task_dir])
            _print_json(ScoringEngine().run(task_dir))
        elif args.command == "run-loop":
            _print_json(IterationLoop().run())
        else:
            parser.error(f"unknown command: {args.command}")
    except Exception as exc:
        print(f"pgg-se7-training-pipeline: error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


__all__ = [
    "TaskGenerator",
    "TrainingPipeline",
    "ScoringEngine",
    "IterationLoop",
    "pipeline_status",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
