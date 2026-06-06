# run_conversation RC-S02 continuation workflow — 2026-06-02

## When to use
Use this reference when continuing `agent/conversation_loop.py::run_conversation()`治理 after RC-S01 characterization/extraction already exists and the user asks to continue under the >75% low-risk rule.

## User execution preference embedded in this workflow
- If next step feasibility is >75%, low risk, and reversible, continue directly without asking.
- Limit score-driven automatic continuation to ≤5 rounds per user prompt.
- If the next extraction score is not stably >75 or touches high-uncertainty boundaries, stop direct extraction and first add characterization tests or explain the boundary.

## RC-S02 safe progression pattern
1. Stay before provider call（模型调用）and tool execution（工具执行）unless explicitly authorized.
2. Extract one mechanical helper（机械辅助函数）per round.
3. Add behavior-level characterization tests（行为级特征保持测试）before or with each helper.
4. If a target scores around 74~78 due boundary uncertainty, first add tests to raise confidence, then extract only if stable >75.
5. Do not modify Hermes core scheduler（核心调度器）or security boundary（安全边界）.

## Helpers extracted in this session
- `_collect_pre_llm_plugin_context(...)`: pre-LLM plugin context collection.
- `_prepare_pre_loop_memory_context(...)`: memory manager turn start + external memory prefetch.
- `_bind_pre_loop_interrupt_state(agent)`: execution-thread interrupt state binding.
- `_initialize_pre_loop_state(agent)`: main loop counters and per-turn mutation tracking initialization.
- `_cleanup_stale_connections_before_turn(agent)`: pre-turn stale connection cleanup.
- `_run_codex_app_server_handoff_if_enabled(...)`: codex_app_server early-return handoff.

## Validation bundle
Run from `/Users/appleoppa/.hermes/hermes-agent` with project venv:

```bash
venv/bin/python - <<'PY'
from agent.pgg_archon_run_conversation_slicer import analyze_run_conversation_slices, build_extraction_readiness_matrix
r = analyze_run_conversation_slices('agent/conversation_loop.py')
for i in range(1, 10):
    k = f'rc_s{i:02d}_characterization'
    print(k, r[k]['contract_status'])
print('matrix', build_extraction_readiness_matrix('agent/conversation_loop.py')['status'])
PY
venv/bin/python -m pytest tests/agent/test_conversation_loop_bootstrap_helpers.py tests/agent/test_pgg_archon_run_conversation_slicer.py -q
venv/bin/python -m py_compile agent/conversation_loop.py agent/pgg_archon_run_conversation_slicer.py tests/agent/test_conversation_loop_bootstrap_helpers.py
git diff --check
venv/bin/python -m apex_god.health
venv/bin/python -m apex_god.evolution_manifest --update
```

## Slicer drift handling
Helper insertion/extraction can move signals out of fixed windows. Do not ignore WATCH. Diagnose exact missing field, then update slicer anchoring to use relative windows plus whole-function/helper AST signals where the original behavior is preserved. This is a drift fix, not a weakening of contract semantics.

## Reporting/commit discipline
- Evidence reports go under `/Users/appleoppa/.hermes/workspace/进化/证据/`, not Desktop.
- Update/read back `/Users/appleoppa/.hermes/data/EVOLUTION_MANIFEST.json` after successful validation.
- Stage only current-round files, typically:
  - `agent/conversation_loop.py`
  - `agent/pgg_archon_run_conversation_slicer.py` if slicer changed
  - relevant tests
- Do not claim CodeGenesis PASS while scanner remains WATCH due high_duplication.
