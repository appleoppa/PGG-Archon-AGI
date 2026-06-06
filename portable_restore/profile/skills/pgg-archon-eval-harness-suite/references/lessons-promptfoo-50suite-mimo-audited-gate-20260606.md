# Promptfoo 30→50 suite + MiMo audited manifest gate lessons (2026-06-06)

## What changed

PGG Archon eval harness now uses a stronger evidence chain for promptfoo benchmark smokes:

1. `promptfoo` official CLI runs real suites through a Hermes Python provider.
2. `pgg_archon_promptfoo_finalize.py` parses raw result/log and emits a normalized final report.
3. `pgg_archon_legal_boundary_gate.py` verifies required legal anti-overclaim boundary statements are present.
4. `pgg_archon_mimo_micro_auditor.py` runs MiMo as held-out third-party audit/benchmark judge using micro prompts.
5. `pgg_archon_audited_manifest_gate.py` writes Manifest `PASS` only if required audits pass; otherwise `WATCH`.

## Provider-role policy update

- MiMo (`mimo_v25_pro_auditor`) is the independent third-party audit / benchmark judge.
- MiMo must not participate in ordinary processing, drafting, coding, or candidate optimization pools.
- Agnes (`agnes_ai`) is back in ordinary processing/collaboration pools.
- Tests should assert:
  - default processing providers include Agnes;
  - default processing providers exclude MiMo;
  - third-party judge providers contain MiMo only.

## Promptfoo official CLI smoke pattern

Use local promptfoo via `npm exec --package promptfoo@0.121.15` because `npm config omit=["dev"]` can make `npm install --save-dev promptfoo` return success without creating `node_modules/.bin/promptfoo`.

Known-good command pattern:

```bash
cd ~/.hermes/workspace/pgg-archon-governance/eval-harness/promptfoo-smoke
PROMPTFOO_DISABLE_TELEMETRY=1 \
PROMPTFOO_PYTHON=$HOME/.hermes/hermes-agent/venv/bin/python3 \
npm exec --yes --package promptfoo@0.121.15 -- \
  promptfoo eval --config promptfooconfig_30.yaml \
  --output artifacts/promptfoo_results_30.json \
  2>&1 | tee artifacts/promptfoo_run_30.log
```

Important promptfoo provider pitfalls:

- Inline prompt strings may be parsed as empty prompts; use `file://prompt.txt`.
- Python provider `timeout` is interpreted as milliseconds by promptfoo; convert ms→seconds before passing to `subprocess.run(timeout=...)` for Hermes CLI.
- Always use `set -o pipefail` when piping through `tee`; otherwise promptfoo failures can be hidden by the pipe exit code.

## Suite scale results and interpretation

- 2-item toy smoke: 2/2 PASS.
- 10-item extended smoke: 10/10 PASS.
- 30-item suite: 30/30 PASS.
- 50-item suite: 45/50 PASS, 0 errors.

Boundary:

- `official_harness_smoke` means real promptfoo CLI ran. It does **not** mean official public benchmark score.
- GSM8K public sample smoke is not official GSM8K full score.
- Legal `case0006` items are provided-fact / boundary extraction only; they are not legal correctness proof and not filing advice.
- Smoke pass does not prove L2/full AGI.

## Parser pitfall

Promptfoo logs can include symbols on failure lines:

```text
Results:
  ✓ 45 passed (90.00%)
  ✗ 5 failed (10.00%)
  0 errors (0%)
```

The parser must accept optional `✓/✔` and `✗/✖/x` before counts. Do not assume failure lines start with a digit.

## Legal boundary gate

`pgg_archon_legal_boundary_gate.py` checks that final reports explicitly include all four legal boundary statements:

1. provided-fact extraction is not legal correctness proof;
2. constructed cases / 合理构造 examples are not real case numbers;
3. CMS BLOCKED is not PASS;
4. not directly submit; human lawyer review required.

This is a deterministic precheck only. It is not MiMo audit PASS and not legal correctness proof.

The promptfoo finalizer should inject `legal_boundary_statements` when any domain name includes `legal` or `case`.

## MiMo micro-audit pattern

Large audit packets caused MiMo timeouts. Use one short claim per call and require strict JSON:

```json
{"audit_name":"legal_overclaim","audit_verdict":"PASS|WATCH|BLOCKED","reason":"一句话"}
```

If a call times out or is unparsed:

- do not count it as PASS;
- retry once with a shorter fixed JSON-only prompt if low risk;
- if still not parsed, keep Manifest `WATCH`.

MiMo audit should check boundary/overclaim only, not solve or rewrite the artifact.

## Audited Manifest gate

`pgg_archon_audited_manifest_gate.py` enforces:

- requested `PASS` + all eligible MiMo audits PASS + no timeouts → final `PASS`;
- missing judge call, timeout, unparsed/non-PASS audit, or requested status not PASS → final `WATCH`;
- legal deterministic precheck can be recorded, but it cannot replace MiMo PASS.

This prevents report scripts from self-promoting to Manifest PASS.

## Long-run process pattern

50-item promptfoo suite can take ~12 minutes. Use:

```python
terminal(background=True, notify_on_complete=True, ...)
```

During long runs, progress should be reported from real evidence:

- process status / uptime;
- log file size and tail;
- result JSON existence;
- current Hermes child process prompt if needed.

Do not equate "background process started" with completion.

## Current modules/tests

Modules:

- `agent/pgg_archon_promptfoo_finalize.py`
- `agent/pgg_archon_legal_boundary_gate.py`
- `agent/pgg_archon_mimo_micro_auditor.py`
- `agent/pgg_archon_audited_manifest_gate.py`

Tests:

- `tests/test_pgg_archon_promptfoo_finalize.py`
- `tests/test_pgg_archon_legal_boundary_gate.py`
- `tests/test_pgg_archon_mimo_micro_auditor.py`
- `tests/test_pgg_archon_audited_manifest_gate.py`

## Truth boundary to repeat in future reports

> This is a real promptfoo official CLI smoke and a real MiMo boundary audit gate. It is not an official public benchmark score, not legal correctness proof, not filing advice, and not L2/full AGI proof.
