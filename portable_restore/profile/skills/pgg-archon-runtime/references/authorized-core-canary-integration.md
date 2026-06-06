# Authorized core canary integration pattern

Use this when the user explicitly authorizes PGG Archon / Hermes core integration after prior dry-run/readiness phases.

## Durable pattern

1. Treat explicit authorization as permission to apply a bounded core patch, not permission for unrestricted takeover.
2. Before editing `run_agent.py`, create a timestamped backup under the existing evolution workspace backup directory.
3. Patch the smallest stable entry point only. Preferred shape:
   - import a dedicated `agent.pgg_archon_core_bridge_canary` module inside `AIAgent.run_conversation`;
   - call an observe-only hook before forwarding to `agent.conversation_loop.run_conversation`;
   - do not alter `system_message`, model routing, tool routing, prompt cache, or conversation loop semantics.
4. Feature flag must default off. Example flag: `PGG_ARCHON_CORE_BRIDGE_CANARY_ENABLED`.
5. When enabled, write only redacted JSONL receipts: hashes, lengths, mode, booleans, timestamps, receipt hash. Never store user message literals, API keys, tokens, or secrets.
6. Test both disabled and enabled paths:
   - disabled path writes nothing;
   - enabled path appends one receipt;
   - receipt contains `core_write=false`, `tool_execution_changed=false`, `secret_material_recorded=false`;
   - run-agent forwarding remains behavior-preserving under mocks.
7. Materialize phases as source + tests + JSON/Markdown report + GeneDB gene + experiment + readback.
8. Run `git diff --check`, targeted tests, PGG module status, and a real GPT/Claude review via Responses API for core/evolution changes.
9. Report truth boundary: this is authoritative core canary integration, not production takeover, unbounded runtime, or final unrestricted AGI.

## Verification commands used in the session

```bash
venv/bin/python -m py_compile run_agent.py agent/pgg_archon_core_bridge_canary.py tests/agent/test_pgg_archon_core_bridge_canary.py
venv/bin/python -m pytest tests/agent/test_pgg_archon_core_bridge_canary.py -q
git diff --check
venv/bin/python -m pytest tests/agent/test_pgg_archon_core_bridge_canary.py tests/agent/test_pgg_archon_phase184_188_core_integration.py tests/agent/test_pgg_archon_phase189_193_live_core_canary.py -q
python3 ~/.hermes/agent/pgg_archon_module_status.py
```

## Pitfalls

- Do not claim `authoritative_core_integration` is fully complete merely because the hook exists; distinguish canary/observe-only integration from production takeover.
- Do not enable a persistent unbounded runtime from chat. A live receipt probe is acceptable when explicitly authorized; long-running/unbounded runtime remains a separate high-risk gate.
- If the current Hermes gateway is long-running, note that source changes may require a restart/new process to take effect outside tests.
