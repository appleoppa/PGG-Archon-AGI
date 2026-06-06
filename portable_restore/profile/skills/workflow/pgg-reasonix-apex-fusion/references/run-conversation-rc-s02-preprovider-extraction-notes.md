# RC-S02 pre-provider helper extraction notes

## Trigger
Use alongside `references/run-conversation-rc-characterization-extraction.md` when `agent/conversation_loop.py::run_conversation` has already completed RC-S01 helper extraction and the next candidate is still before provider call（模型调用）and tool execution（工具执行）.

## Durable learnings from the pre-API steer extraction round

1. **Readiness matrix（就绪矩阵）must evolve with actual allowed scope.** If prior commits already moved from RC-S01 into RC-S02 pre-provider/pre-tool helpers, do not leave the matrix status named `RC_S01_MINIMAL_EXTRACTION_READY_WITH_GUARDRAILS`. Update it to a truthful guarded RC-S02 pre-provider status and keep blocked scopes explicit: provider call execution, provider routing, tool execution, scheduler, and security boundary.
2. **Function-length thresholds are brittle after successful helper extraction.** A real reduction of `run_conversation` below an old `>4000` assertion is progress, not failure. Characterization tests should assert a conservative lower bound (for example `>3500` while the function remains large) or semantic anchors, not a stale exact-era threshold.
3. **Late RC windows need tail anchoring.** After repeated helpers are extracted above or from inside the function, fixed `start + 4000` RC-S09 windows can become empty and produce false WATCH. Anchor the final cleanup/persistence window to the tail, e.g. `min(rc_s01_start + 4000, max(fn.lineno, fn_end - 499))`, while preserving all-function semantic checks for moved helper calls.
4. **Pre-API `/steer` drain is a safe RC-S02 pre-provider helper only if behavior tests cover all branches.** Test: string tool content injection, multimodal content block append, no-tool requeue without lock, no-tool requeue with lock, empty guidance no-op, and AST contract proving `run_conversation` delegates to the helper.
5. **When slicer gates fail from helper-extraction drift, fix the read-only characterization layer immediately.** Do not stop after saying WATCH; patch anchors/tests and rerun the full gate set in the same round.

## Verification bundle for this class of round

Minimum commands remain:

```bash
venv/bin/python -m pytest tests/agent/test_conversation_loop_bootstrap_helpers.py -q
venv/bin/python -m pytest tests/agent/test_pgg_archon_run_conversation_slicer.py -q
venv/bin/python -m py_compile agent/conversation_loop.py agent/pgg_archon_run_conversation_slicer.py tests/agent/test_conversation_loop_bootstrap_helpers.py tests/agent/test_pgg_archon_run_conversation_slicer.py
git diff --check
venv/bin/python -m apex_god.health
venv/bin/python -m apex_god.evolution_manifest --update
```

Commit only the round files; evidence reports still belong under `/Users/appleoppa/.hermes/workspace/进化/证据/...` and should not be staged unless explicitly part of the repo.
