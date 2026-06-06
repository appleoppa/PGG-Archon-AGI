# P3 Extended Redteam × 4-Provider LLM Smoke (2026-06-04)

Session-specific condensed knowledge bank for the 30-probe redteam + 4-LLM
parallel audit pattern. Captures the exact tool-budget failure modes so the
next session does not relearn them.

## What we ran

- `agent/pgg_archon_redteam_extended_probes.py` — 30 prompts across 12
  categories (system_prompt_leak, credential_exfil, tool_overreach,
  indirect_injection, harmful_request, legal_hallucination, case_data_leak,
  roleplay_bypass, encoded_payload, context_window_overflow,
  tool_specific_ssrf, agent_delegation_escalate).
- 3 providers, 30 probes each: DeepSeek v4 Flash, MiMo v2.5 Pro, Agnes 2.0
  Flash. (MiniMax M3 + GPT-5.5 + Claude were skipped per user
  authorization — Claude 403, GPT 502, MiniMax unstable; recorded in
  evidence, not silently mapped to PASS.)
- 5-item benchmark corpus over MMLU / GSM8K / BigBench on DeepSeek / MiMo
  / Agnes; verifier-friendly report emitted
  (`p3_archon_p3_verifier.py`).
- 4-LLM consensus verify of the verifier report itself.

## Pitfalls (durable, not env-specific)

1. **`nohup` / `disown` inside a foreground `terminal()` call is rejected.**
   The shell explicitly requires `terminal(background=true,
   notify_on_complete=true)`. If you reach for `&` or `nohup`, the call
   exits 0 with a `Foreground command uses shell-level background
   wrappers` error and you lose the session. Always start a long LLM
   smoke via `terminal(background=true)`.

2. **Heredoc backtick collision.** A `re.sub(r"\s*```$", "", s)` inside
   `<<'PY' ... PY` is fine; but if the heredoc is unquoted (`<<PY ... PY`)
   the backtick in `\s*` is interpreted by the shell and you get
   `bad substitution: no closing "`"`. Use `write_file` to land the
   script on disk and `python3 /tmp/foo.py` to run it. The
   `p3_llm_verify.py` and `p3_full_smoke.py` in `/tmp/` this session
   followed that pattern.

3. **Polling waste.** Calling `process(action="poll")` every 5–10s for a
   240s background run burns 24 tool calls. Instead, after
   `terminal(background=true)`:
   - one `terminal` to `ls -la OUT/`
   - one `terminal` to `ps -axo pid,etime,args | egrep harness` for
     liveness
   - one `process(action="wait")` only at the end

4. **Patch that swaps `from dataclasses import dataclass` for `dataclass,
   asdict, field` plus new lines accidentally drops `field`, `asdict`,
   `datetime`, `timezone`.** Pyright then reports `field is not defined`.
   Always re-add the full import line in one patch; do not rely on the
   diff tool to keep the other names. Symptom: `NameError: name 'field'
   is not defined` at module import. Fix: re-emit the import line
   unchanged.

5. **Relative imports inside `agent/`.** Modules that do
   `from .sibling import X` need to be run with `cwd=hermes-agent/` or
   the parent package is not on `sys.path`. CLI: `python -m agent.foo`.
   Pytest: `from agent.foo import X` (rootdir handles it).

6. **Verdict classifier fooled by nested BLOCKED.** A response that has
   `model_verdict: PASS` at the top but `candidate_decisions[*].decision:
   BLOCKED` inside will be mis-classified by a naive
   `if "BLOCKED" in text: BLOCKED` rule. Always parse top-level JSON
   first; only fall back to substring matching if no JSON is found.
   (Documented in `pgg_archon_llm_quorum_gate.py`; symptom: 0/2 PASS when
   MIMO/Agnes actually returned top-level PASS.)

## What a future session should do in 1 round for the same task

```
1. write_file: agent/pgg_archon_redteam_extended_probes.py   (~120 lines)
2. patch: harness to use EXTENDED_PROBES + --extended flag
3. write_file: tests/test_pgg_archon_redteam_extended.py     (~60 lines)
4. pytest (full): ~0.3s
5. git add + commit
6. terminal(background=true, notify_on_complete=true):
     - DS 30 → expected 60–120s
     - MiMo 30 → expected 120–180s
     - Agnes 30 → expected 180–260s  (slowest)
7. file-poll + ps-poll for each, NOT process-poll
8. 4-LLM verify the verifier-friendly report (one write_file +
   python3 /tmp/p3_llm_verify.py)
9. update manifest
```

Total budget: 7–9 tool calls, vs. the 30+ calls this session actually used.

## Channel reality (audit disclosure)

- DeepSeek v4 Flash: HTTP 200, 30 probes, refusal 17/30 (0.57)
- MiMo v2.5 Pro: HTTP 200, 30 probes, refusal 20/30 (0.67)
- Agnes 2.0 Flash: HTTP 200, 30 probes, refusal observed 18/30 (0.60)
- GPT-5.5: HTTP 502 — bad gateway; not silently mapped to PASS
- Claude Opus 4-6: HTTP 403 — All available accounts exhausted
  (per user instruction, intentionally not repaired)
- MiniMax M3: not included in this round (env-visible but earlier
  stability issues)

## Files produced (all in ~/.hermes/workspace/audit/)

- `p3_extended_redteam_20260604_205000/redteam_{deepseek,mimo,agnes}_30.json`
- `p3_full_smoke_20260604_203000/` (earlier 12-probe + 5-item bench round)
- `p3_final_llm_verify_20260604_204000/verify_*.json` (4-LLM consensus)
- `p3_full_smoke_20260604_203000/verifier_friendly_report.json`
