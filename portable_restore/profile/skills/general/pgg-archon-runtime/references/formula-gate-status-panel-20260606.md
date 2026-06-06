# Formula Gate Status Panel — 2026-06-06

## Trigger

Use this reference when PGG Archon / AGI / evolution work needs to show the user's `/goal` formula visibly, not just “internally”. It was created after the user asked why the formula was not felt during execution.

## Canonical module

```text
agent/pgg_archon_formula_gate_status.py
```

Smoke commands:

```bash
cd /Users/appleoppa/.hermes/hermes-agent
PYTHONPATH=$PWD venv/bin/python -m agent.pgg_archon_formula_gate_status AGI 总纲 T5 进化
PYTHONPATH=$PWD venv/bin/python -m agent.pgg_archon_formula_gate_status AGI 总纲 T5 进化 --json
PYTHONPATH=$PWD venv/bin/python -m pytest -q tests/test_pgg_archon_formula_gate_status.py
```

Expected visible text includes:

```text
【公式门禁状态】
/goal：总纲1：AGI L0-L5 六维评估框架；总纲2：Agent_Evolve = LDR(K) → GapDetect → CodeSelfFix → HotReload → TaskSolve → KnowledgeSettle
状态：PASS/WATCH | 任务类型：agi | 目标：T4-oriented engineering formula gate; not T5 proof
总纲1六维：...
总纲2闭环：...
证据：Manifest=有/缺；latest PASS=N；缺口=...
边界：not T5 proof, not full AGI, not official external benchmark, not legal correctness, not production takeover evidence
```

## Required shape

The status dict must contain:

```text
schema = PGGArchonFormulaGateStatus/v1
goal_formula_rule.source = /goal
goal_formula_rule.north_star = 总纲1 AGI L0-L5 六维
goal_formula_rule.execution_chain = 总纲2 Agent_Evolve...
six_dimensions[6]
agent_evolve_chain[6]
evidence_gates
missing_gates
manifest_summary
boundary
```

## Review lessons

Claude/GPT review found these non-obvious requirements:

1. `/goal` must be a top-level returned field and visible in rendered text; docstring-only is not enough.
2. Do not write “T4-ready” unless you mean achieved; use `T4-oriented engineering formula gate; not T5 proof`.
3. Manifest latest sorting by key is wrong; sort by `created_at/generated_at/timestamp`, falling back to key.
4. Empty task, missing/malformed manifest, and `explicit=False` should produce `WATCH`.
5. The module must remain read-only: no provider calls, network calls, subprocesses, config writes, or scheduler/security mutation.
6. Tests should derive repo root from `Path(__file__).resolve().parents[...]`; avoid hardcoded `/Users/appleoppa/...` paths in reusable tests.

## Boundary

This panel proves that the formula gate is explicit and evidence-aware. It does not prove T5/full AGI, official benchmark success, legal correctness, production takeover, or runtime scheduler enforcement.
