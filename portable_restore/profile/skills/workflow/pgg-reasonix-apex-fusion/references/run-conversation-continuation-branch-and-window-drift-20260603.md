# run_conversation continuation gate: branch drift + helper-window drift — 2026-06-03

## Trigger
Use when continuing `agent/conversation_loop.py::run_conversation` governance across chats or after a previous scoped commit.

## Durable lessons

1. **Verify branch before trusting readiness.** A new conversation may start on `main` or another branch even when the handoff references `pgg-archon-upstream-absorb-20260531-0913`. Before running slicer/readiness gates, check:
   - `git status --short`
   - `git branch --show-current`
   - `git rev-parse --short=9 HEAD`
   If the branch lacks `agent/pgg_archon_run_conversation_slicer.py` or the helper tests, it is not the active governance branch. Switch to the handoff branch only if the worktree is clean or after explicitly preserving local changes.

2. **Do not treat wrong-branch ModuleNotFoundError as a code failure.** If importing `agent.pgg_archon_run_conversation_slicer` fails while the handoff says the slicer exists, first diagnose branch/repo state, not Python packaging.

3. **Helper extraction can shrink `run_conversation` enough to break stale line-count gates.** After multiple helpers move code out of the function, thresholds like `function_lines > 4000` can become false while the governance target remains valid. Update readiness thresholds and contract wording to reflect current helper-extracted state; do not revert working helper extractions just to satisfy old counts.

4. **Late RC windows drift after pre-provider helper extraction.** RC-S03/RC-S04/RC-S07/RC-S08/RC-S09 signals may slide into adjacent 500-line windows. For moved-but-still-present semantic signals, update read-only contracts to accept `window OR all-function AST signal` (or `run_conversation OR helper`) rather than weakening the contract or stopping at WATCH.

5. **AST contracts must include extracted helpers when they own the semantic gate.** If `_sanitize_tool_call_arguments` and `_repair_message_sequence` move into `_repair_messages_before_api_call`, the provider-preparation AST contract should scan `run_conversation` plus that helper. This preserves behavior-level guardrails without forcing helper code back inline.

6. **Avoid monkeypatching global `logging.getLogger` in pytest.** Patching `agent.conversation_loop.logging.getLogger` can also affect pytest's own logging teardown because the module object is shared. Prefer injecting `agent.logger` for log assertions, or for fallback paths simply assert the fallback logger has an `.info` method and that zero repairs return `(0, 0)`.

7. **Scoped commits must ignore unrelated untracked files.** If an unrelated untracked file appears (for example `tools/apex_evolution_tool.py`), mention it in the evidence report and commit only the files changed by the current helper extraction.

## Verification pattern
After any branch correction or slicer contract drift fix, rerun:

```bash
venv/bin/python -m pytest tests/agent/test_conversation_loop_bootstrap_helpers.py -q
venv/bin/python -m pytest tests/agent/test_pgg_archon_run_conversation_slicer.py -q
venv/bin/python -m py_compile agent/conversation_loop.py agent/pgg_archon_run_conversation_slicer.py tests/agent/test_conversation_loop_bootstrap_helpers.py tests/agent/test_pgg_archon_run_conversation_slicer.py
git diff --check
venv/bin/python -m apex_god.health
venv/bin/python -m apex_god.evolution_manifest --update
```

Record RC-S01~RC-S09 statuses, readiness matrix status/score, manifest `generated_at` + SHA256, and commit hash in the evidence report.
