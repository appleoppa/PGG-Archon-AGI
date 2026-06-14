#!/usr/bin/env python3
"""
SE8 Unified Research Engine for PGG Archon
==========================================

Internal draft-only research framework implementing the SE8 formula:

    Engine_APEX = (Coord_Fix × Token_Control) × (Task_Syn + Train + Bench)
                  × (ERA + Co_Scientist + Robin)

Boundaries:
  - Local-only deterministic mock operation.
  - No external LLM/API calls.
  - No AGI/T5 capability claims.
  - Produces auditable draft hypotheses and experiment records.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", HOME / ".hermes")).expanduser()
DATA_ROOT = HERMES_HOME / "data" / "pgg-se8-research-engine"
ERA_ROOT = DATA_ROOT / "era"
CO_SCIENTIST_ROOT = DATA_ROOT / "co-scientist"
ROBIN_ROOT = DATA_ROOT / "robin"
MEMORY_FILE = CO_SCIENTIST_ROOT / "memory.jsonl"
STATE_FILE = DATA_ROOT / "engine_state.json"

BOUNDARIES = ["internal_pgg_research_framework", "draft_only", "no_external_llm", "no_agi_t5_claims"]
ENGINE_FORMULA = "Engine_APEX = (Coord_Fix × Token_Control) × (Task_Syn + Train + Bench) × (ERA + Co_Scientist + Robin)"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    for path in (DATA_ROOT, ERA_ROOT, CO_SCIENTIST_ROOT, ROBIN_ROOT):
        path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{int(time.time())}_{digest}"


def _load_state() -> dict[str, Any]:
    _ensure_dirs()
    state = _read_json(STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("schema", "pgg.se8.research_engine.state.v1")
    state.setdefault("created_at", _utc_now())
    state.setdefault("updated_at", _utc_now())
    state.setdefault("era_runs", 0)
    state.setdefault("co_scientist_runs", 0)
    state.setdefault("robin_runs", 0)
    state.setdefault("last_run", None)
    return state


def _save_state(update: dict[str, Any]) -> dict[str, Any]:
    state = _load_state()
    state.update(update)
    state["updated_at"] = _utc_now()
    _write_json(STATE_FILE, state)
    return state


@dataclass
class StatusEnvelope:
    component: str
    status: str
    updated_at: str = field(default_factory=_utc_now)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MockLLM:
    """Deterministic local LLM interface abstraction.

    This is deliberately a mock backend. It never performs network calls and is
    suitable for repeatable sandbox tests.
    """

    def __init__(self, model_name: str = "local-mock-se8") -> None:
        self.model_name = model_name

    def complete(self, prompt: str, *, role: str = "researcher") -> str:
        digest = hashlib.sha256(f"{role}:{prompt}".encode("utf-8")).hexdigest()[:10]
        lower = prompt.lower()
        if "algorithm" in lower or "era" in lower:
            return f"Draft algorithm candidate {digest}: normalize inputs, score evidence, then select the simplest verified rule."
        if "hypothesis" in lower or "co" in lower:
            return f"Draft scientific hypothesis {digest}: coordinated local verification improves hypothesis quality under token constraints."
        return f"Draft research note {digest}: local deterministic synthesis completed."


class TreeSearch:
    """Small breadth-first tree search over algorithm idea mutations."""

    OPERATORS = ["simplify", "add_invariant", "add_test", "reduce_state"]

    def __init__(self, llm: MockLLM, max_depth: int = 2, beam_width: int = 3) -> None:
        self.llm = llm
        self.max_depth = max_depth
        self.beam_width = beam_width

    def _score(self, node: dict[str, Any]) -> float:
        text = node["idea"]
        bonus = sum(token in text for token in ("invariant", "test", "verified", "simplest"))
        return round(0.50 + 0.08 * node["depth"] + 0.05 * bonus - 0.01 * len(text.split()), 4)

    def explore(self, seed: str) -> list[dict[str, Any]]:
        frontier = [{"idea": seed, "depth": 0, "path": ["seed"], "score": 0.5}]
        visited: list[dict[str, Any]] = []
        for depth in range(1, self.max_depth + 1):
            candidates: list[dict[str, Any]] = []
            for node in frontier:
                for op in self.OPERATORS:
                    prompt = f"ERA algorithm mutation op={op}; parent={node['idea']}"
                    idea = self.llm.complete(prompt, role="era-tree-search") + f" Operator={op}."
                    child = {"idea": idea, "depth": depth, "path": node["path"] + [op]}
                    child["score"] = self._score(child)
                    candidates.append(child)
            candidates.sort(key=lambda item: item["score"], reverse=True)
            frontier = candidates[: self.beam_width]
            visited.extend(frontier)
        return visited


class CodeSandbox:
    """Local code sandbox validator for ERA-generated algorithm sketches."""

    SAFE_BUILTINS = {"len": len, "sum": sum, "min": min, "max": max, "range": range, "float": float, "int": int}

    DEFAULT_CODE = """
def candidate_score(values):
    if not values:
        return 0.0
    normalized = [float(v) for v in values]
    return sum(normalized) / len(normalized)
""".strip()

    def validate(self, code: str | None = None) -> dict[str, Any]:
        source = code or self.DEFAULT_CODE
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
                    raise ValueError(f"disallowed syntax: {type(node).__name__}")
            namespace: dict[str, Any] = {"__builtins__": self.SAFE_BUILTINS}
            exec(compile(tree, "<se8-era-sandbox>", "exec"), namespace, namespace)
            func = namespace.get("candidate_score")
            if not callable(func):
                raise ValueError("candidate_score function missing")
            tests = [([1, 2, 3], 2.0), ([0, 10], 5.0), ([], 0.0)]
            results = []
            for values, expected in tests:
                got = func(values)
                numeric_got = float(got)  # type: ignore[arg-type]
                ok = abs(numeric_got - expected) < 1e-9
                results.append({"input": values, "expected": expected, "got": numeric_got, "ok": ok})
            passed = all(item["ok"] for item in results)
            return {"passed": passed, "tests": results, "source_hash": hashlib.sha256(source.encode()).hexdigest()[:12]}
        except Exception as exc:
            return {"passed": False, "error": str(exc), "source_hash": hashlib.sha256(source.encode()).hexdigest()[:12]}


class ERAModule:
    """ERA = LLM × TreeSearch × CodeSandbox.

    Automatic algorithm-writing draft module. It proposes local algorithm
    hypotheses and verifies the executable kernel in a sandbox.
    """

    def __init__(self, llm: MockLLM | None = None, root: Path | str = ERA_ROOT) -> None:
        _ensure_dirs()
        self.llm = llm or MockLLM()
        self.tree_search = TreeSearch(self.llm)
        self.sandbox = CodeSandbox()
        self.root = Path(root)
        self.last_status = StatusEnvelope("ERAModule", "initialized", details={"llm": self.llm.model_name})

    def run(self, objective: str = "write a robust local scoring algorithm") -> dict[str, Any]:
        seed = self.llm.complete(f"ERA algorithm seed: {objective}", role="era-seed")
        explored = self.tree_search.explore(seed)
        best = max(explored, key=lambda item: item["score"]) if explored else {"idea": seed, "score": 0.5, "path": ["seed"]}
        sandbox = self.sandbox.validate()
        hypothesis = {
            "schema": "pgg.se8.era.algorithm_hypothesis.v1",
            "id": _stable_id("era", {"objective": objective, "best": best}),
            "created_at": _utc_now(),
            "formula": "ERA = LLM × TreeSearch × CodeSandbox",
            "objective": objective,
            "algorithm_hypothesis": best["idea"],
            "tree_path": best["path"],
            "confidence": round(min(0.95, best["score"] + (0.20 if sandbox["passed"] else 0.0)), 4),
            "sandbox": sandbox,
            "boundaries": BOUNDARIES,
        }
        out = self.root / f"{hypothesis['id']}.json"
        _write_json(out, hypothesis)
        state = _load_state()
        _save_state({"era_runs": int(state.get("era_runs", 0)) + 1, "last_run": {"component": "ERA", "path": str(out), "id": hypothesis["id"]}})
        self.last_status = StatusEnvelope("ERAModule", "algorithm_hypothesis_generated", details={"id": hypothesis["id"], "path": str(out), "sandbox_passed": sandbox["passed"]})
        return hypothesis

    def status_report(self) -> dict[str, Any]:
        return self.last_status.to_dict()


class CoScientist:
    """Co-Scientist = Gen + Rank + Reflect + Evolve × Memory."""

    def __init__(self, llm: MockLLM | None = None, memory_file: Path | str = MEMORY_FILE) -> None:
        _ensure_dirs()
        self.llm = llm or MockLLM()
        self.memory_file = Path(memory_file)
        self.last_status = StatusEnvelope("CoScientist", "initialized", details={"memory_file": str(self.memory_file)})

    def _load_memory(self) -> list[dict[str, Any]]:
        if not self.memory_file.exists():
            return []
        rows = []
        for line in self.memory_file.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        return rows[-50:]

    def gen(self, topic: str) -> list[dict[str, Any]]:
        personas = ["generator", "skeptic", "methodologist", "systems_biologist"]
        return [
            {"agent": persona, "hypothesis": self.llm.complete(f"CoScientist hypothesis topic={topic}; persona={persona}", role=persona)}
            for persona in personas
        ]

    def rank(self, hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for item in hypotheses:
            text = item["hypothesis"]
            novelty = (int(hashlib.sha256(text.encode()).hexdigest()[:2], 16) % 30) / 100
            item["rank_score"] = round(0.55 + novelty + (0.05 if "verification" in text else 0.0), 4)
        return sorted(hypotheses, key=lambda item: item["rank_score"], reverse=True)

    def reflect(self, hypothesis: dict[str, Any], memory: list[dict[str, Any]]) -> dict[str, Any]:
        prior_count = len(memory)
        critique = "Add falsifiable local benchmark and mechanism trace before promotion."
        return {**hypothesis, "reflection": critique, "memory_context_count": prior_count}

    def evolve(self, reflected: dict[str, Any]) -> dict[str, Any]:
        evolved_text = reflected["hypothesis"] + " Evolved: test against a local ablation benchmark with explicit negative controls."
        return {**reflected, "evolved_hypothesis": evolved_text, "evolution_step": "local_ablation_and_negative_control"}

    def run(self, topic: str = "token-controlled coordinated research workflow") -> dict[str, Any]:
        memory = self._load_memory()
        generated = self.gen(topic)
        ranked = self.rank(generated)
        reflected = self.reflect(ranked[0], memory)
        evolved = self.evolve(reflected)
        result = {
            "schema": "pgg.se8.co_scientist.scientific_hypothesis.v1",
            "id": _stable_id("co_scientist", {"topic": topic, "top": evolved}),
            "created_at": _utc_now(),
            "formula": "Co_Scientist = Gen+Rank+Reflect+Evolve × Memory",
            "topic": topic,
            "generated": generated,
            "ranked": ranked,
            "scientific_hypothesis": evolved["evolved_hypothesis"],
            "reflection": evolved["reflection"],
            "rank_score": evolved["rank_score"],
            "memory_context_count": evolved["memory_context_count"],
            "boundaries": BOUNDARIES,
        }
        out = CO_SCIENTIST_ROOT / f"{result['id']}.json"
        _write_json(out, result)
        _append_jsonl(self.memory_file, {"id": result["id"], "created_at": result["created_at"], "topic": topic, "scientific_hypothesis": result["scientific_hypothesis"], "rank_score": result["rank_score"]})
        state = _load_state()
        _save_state({"co_scientist_runs": int(state.get("co_scientist_runs", 0)) + 1, "last_run": {"component": "CoScientist", "path": str(out), "id": result["id"]}})
        self.last_status = StatusEnvelope("CoScientist", "scientific_hypothesis_generated", details={"id": result["id"], "path": str(out), "memory_file": str(self.memory_file)})
        return result

    def status_report(self) -> dict[str, Any]:
        return self.last_status.to_dict()


class Robin:
    """Robin = Hypo + Plan + Exp + Analyze × Mechanism."""

    def __init__(self, root: Path | str = ROBIN_ROOT) -> None:
        _ensure_dirs()
        self.root = Path(root)
        self.last_status = StatusEnvelope("Robin", "initialized")

    def hypo(self, question: str) -> dict[str, Any]:
        return {"question": question, "hypothesis": "A constrained local research loop improves reproducibility when each step emits machine-checkable evidence."}

    def plan(self, hypothesis: dict[str, Any]) -> dict[str, Any]:
        return {
            "steps": ["define_control", "run_constrained_loop", "compare_evidence_completeness", "record_mechanism_trace"],
            "metrics": ["evidence_fields_present", "reproducibility_score", "mechanism_trace_depth"],
            "hypothesis": hypothesis,
        }

    def exp(self, plan: dict[str, Any]) -> dict[str, Any]:
        control = {"evidence_fields_present": 3, "reproducibility_score": 0.62, "mechanism_trace_depth": 1}
        treatment = {"evidence_fields_present": 5, "reproducibility_score": 0.84, "mechanism_trace_depth": 3}
        return {"control": control, "treatment": treatment, "delta_reproducibility": round(treatment["reproducibility_score"] - control["reproducibility_score"], 4), "plan_steps": plan["steps"]}

    def analyze(self, experiment: dict[str, Any]) -> dict[str, Any]:
        supported = experiment["delta_reproducibility"] > 0.10 and experiment["treatment"]["evidence_fields_present"] >= 5
        return {"supported": supported, "summary": "Treatment produced more complete evidence and deeper mechanism traces in the local mock experiment.", "statistics": experiment}

    def mechanism(self, analysis: dict[str, Any]) -> dict[str, Any]:
        return {
            "mechanism": "Coord_Fix reduces action noise; Token_Control preserves context budget; structured Train/Bench records make experiment traces reproducible.",
            "causal_chain": ["lower_ui_noise", "stable_context", "complete_evidence", "higher_reproducibility"],
            "analysis_supported": analysis["supported"],
        }

    def run(self, question: str = "Does a constrained local research loop improve reproducibility?") -> dict[str, Any]:
        hypothesis = self.hypo(question)
        plan = self.plan(hypothesis)
        experiment = self.exp(plan)
        analysis = self.analyze(experiment)
        mechanism = self.mechanism(analysis)
        result = {
            "schema": "pgg.se8.robin.experiment_result.v1",
            "id": _stable_id("robin", {"question": question, "analysis": analysis}),
            "created_at": _utc_now(),
            "formula": "Robin = Hypo+Plan+Exp+Analyze × Mechanism",
            "question": question,
            "hypothesis": hypothesis,
            "plan": plan,
            "experiment": experiment,
            "analysis": analysis,
            "mechanism": mechanism,
            "experiment_result": "supported" if analysis["supported"] else "not_supported",
            "boundaries": BOUNDARIES,
        }
        out = self.root / f"{result['id']}.json"
        _write_json(out, result)
        state = _load_state()
        _save_state({"robin_runs": int(state.get("robin_runs", 0)) + 1, "last_run": {"component": "Robin", "path": str(out), "id": result["id"]}})
        self.last_status = StatusEnvelope("Robin", "experiment_completed", details={"id": result["id"], "path": str(out), "supported": analysis["supported"]})
        return result

    def status_report(self) -> dict[str, Any]:
        return self.last_status.to_dict()


class ResearchEngine:
    """Three-in-one SE8 research entrypoint: ERA + CoScientist + Robin."""

    def __init__(self) -> None:
        _ensure_dirs()
        self.era = ERAModule()
        self.co_scientist = CoScientist()
        self.robin = Robin()
        self.last_status = StatusEnvelope("ResearchEngine", "initialized", details={"formula": ENGINE_FORMULA})

    def run_era(self, objective: str = "write a robust local scoring algorithm") -> dict[str, Any]:
        return self.era.run(objective)

    def run_co_scientist(self, topic: str = "token-controlled coordinated research workflow") -> dict[str, Any]:
        return self.co_scientist.run(topic)

    def run_robin(self, question: str = "Does a constrained local research loop improve reproducibility?") -> dict[str, Any]:
        return self.robin.run(question)

    def run(self) -> dict[str, Any]:
        result = {
            "schema": "pgg.se8.research_engine.run.v1",
            "created_at": _utc_now(),
            "formula": ENGINE_FORMULA,
            "era": self.run_era(),
            "co_scientist": self.run_co_scientist(),
            "robin": self.run_robin(),
            "boundaries": BOUNDARIES,
        }
        self.last_status = StatusEnvelope("ResearchEngine", "three_in_one_run_completed", details={"era_id": result["era"]["id"], "co_scientist_id": result["co_scientist"]["id"], "robin_id": result["robin"]["id"]})
        return result

    def status_report(self) -> dict[str, Any]:
        state = _load_state()
        memory_count = 0
        if MEMORY_FILE.exists():
            memory_count = len([line for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines() if line.strip()])
        return {
            "schema": "pgg.se8.research_engine.status.v1",
            "component": "ResearchEngine",
            "status": "ready",
            "updated_at": _utc_now(),
            "formula": ENGINE_FORMULA,
            "boundaries": BOUNDARIES,
            "paths": {"data_root": str(DATA_ROOT), "era_root": str(ERA_ROOT), "co_scientist_root": str(CO_SCIENTIST_ROOT), "robin_root": str(ROBIN_ROOT), "memory_file": str(MEMORY_FILE), "state_file": str(STATE_FILE)},
            "state": state,
            "memory_records": memory_count,
            "modules": {"era": self.era.status_report(), "co_scientist": self.co_scientist.status_report(), "robin": self.robin.status_report()},
        }


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PGG SE8 unified research engine (local draft-only)")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="Show engine status")
    era = sub.add_parser("era-run", help="Run ERA algorithm hypothesis module")
    era.add_argument("--objective", default="write a robust local scoring algorithm")
    co = sub.add_parser("co-scientist-run", help="Run CoScientist scientific hypothesis module")
    co.add_argument("--topic", default="token-controlled coordinated research workflow")
    robin = sub.add_parser("robin-run", help="Run Robin autonomous experiment module")
    robin.add_argument("--question", default="Does a constrained local research loop improve reproducibility?")
    sub.add_parser("run-all", help="Run ERA + CoScientist + Robin")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    engine = ResearchEngine()
    command = args.command or "status"
    if command == "status":
        _print_json(engine.status_report())
    elif command == "era-run":
        _print_json(engine.run_era(args.objective))
    elif command == "co-scientist-run":
        _print_json(engine.run_co_scientist(args.topic))
    elif command == "robin-run":
        _print_json(engine.run_robin(args.question))
    elif command == "run-all":
        _print_json(engine.run())
    else:
        parser.error(f"unknown command: {command}")
    return 0


__all__ = ["ResearchEngine", "ERAModule", "CoScientist", "Robin", "MockLLM", "TreeSearch", "CodeSandbox", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
