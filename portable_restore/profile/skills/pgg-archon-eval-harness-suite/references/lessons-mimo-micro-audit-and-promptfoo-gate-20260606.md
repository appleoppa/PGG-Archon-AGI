# MiMo micro-audit + promptfoo audited manifest gate lessons (2026-06-06)

## Context

During PGG Archon eval hardening, the user changed the held-out third-party judge role:

- `mimo_v25_pro_auditor` / MiMo is now the independent third-party audit / benchmark judge.
- `agnes_ai` / Agnes is back in the ordinary processing/collaboration pool.
- Do not keep old “Agnes as third-party judge” assumptions in new eval code.

This session also extended promptfoo smoke from 2 → 10 → 30 items and standardized a MiMo micro-audit gate for Manifest PASS/WATCH decisions.

## Durable pattern

### 1. Provider-role split

Default processing provider pool should include ordinary collaborators and exclude the held-out judge:

- Processing: GPT, Claude, DeepSeek, MiniMax, Agnes.
- Held-out judge: MiMo only.

Third-party judge providers should return MiMo only. If MiMo times out, mark `UNAVAILABLE_TIMEOUT` / `WATCH`; never substitute Agnes or a local precheck as “MiMo PASS”.

### 2. Promptfoo official CLI smoke

The reliable path was:

```bash
PROMPTFOO_DISABLE_TELEMETRY=1 \
PROMPTFOO_PYTHON=$HOME/.hermes/hermes-agent/venv/bin/python3 \
npm exec --yes --package promptfoo@0.121.15 -- \
  promptfoo eval --config promptfooconfig_30.yaml \
  --output artifacts/promptfoo_results_30.json
```

Important fixes discovered:

- `npx promptfoo@latest eval --help` can cold-start slowly; `npm exec --package promptfoo@0.121.15` is more reliable.
- Local `npm install --save-dev promptfoo` may create a lockfile but no `node_modules` if npm config has `omit=["dev"]`; do not rely on local `.bin` without checking.
- Inline prompts can be parsed incorrectly by promptfoo; use `file://prompt.txt`.
- Promptfoo Python provider timeout is effectively milliseconds; configure `timeout: 120000` and convert ms→seconds before passing to `subprocess.run(..., timeout=...)`.

### 3. 30-item smoke shape

A useful bounded smoke suite:

- 10 toy arithmetic items
- 10 public GSM8K sample items
- 10 case-0006 provided-fact / boundary checks

The truthful interpretation is: official CLI smoke / evidence probe only. It is not an official GSM8K/MMLU/LegalBench score, not legal correctness proof, and not L2/full AGI proof.

### 4. MiMo micro-audit strategy

Large evidence packets caused MiMo or Agnes timeouts. The stable pattern is one micro-claim per call:

```text
artifact=<path> sha256=<sha>
claim=<one boundary claim>
expected_boundary=<one sentence>
JSON only: {audit_name, audit_verdict, reason}
```

Use three separate claims for promptfoo 30-suite:

1. `benchmark_overclaim`: smoke pass ≠ official benchmark score.
2. `legal_overclaim`: provided-fact / boundary extraction ≠ legal correctness or filing-ready work.
3. `agi_overclaim`: 30-item smoke ≠ L2/full AGI proof.

PASS requires all micro-audits PASS and timeout_count=0.

### 5. Audited Manifest gate

Manifest status should be requested, not assumed. Gate rule:

```text
requested_status == PASS
AND MiMo judge was actually called
AND audit_count > 0
AND pass_count == audit_count
AND timeout_count == 0
→ final_status = PASS
else WATCH
```

If `call_mimo=False`, local prechecks may run but Manifest must downgrade to WATCH with `mimo_judge_not_called`. This prevents local deterministic checks from impersonating third-party review.

### 6. Legal deterministic boundary gate

A local deterministic legal boundary precheck can verify that required disclaimers are present:

- provided-fact extraction is not legal correctness proof
- constructed / reasonable example cases are not real cases
- CMS BLOCKED is not PASS
- not directly submit; human lawyer review required

This gate is useful before MiMo review, but its result is **not** MiMo PASS and **not** legal correctness. If the report lacks these boundary statements, keep WATCH and fix the report text/schema rather than bypassing the gate.

## Pitfalls

- Do not convert a timed-out MiMo legal audit to PASS just because the local deterministic legal gate passes.
- Do not claim “official benchmark score” from promptfoo toy/GSM8K smoke, even when 30/30 passes.
- Do not claim legal correctness from case-0006 provided-fact extraction; it only verifies bounded extraction and boundary handling.
- Do not claim L2/full AGI from smoke evidence. At most it improves L1→L2 evidence maturity.
- If a shell heredoc/inline script silently produces no report, write the script to disk and rerun; read back report existence and Manifest key before declaring completion.

## Verification artifacts from the session

Representative module names created/used:

- `agent/pgg_archon_mimo_micro_auditor.py`
- `agent/pgg_archon_audited_manifest_gate.py`
- `agent/pgg_archon_promptfoo_finalize.py`
- `agent/pgg_archon_legal_boundary_gate.py`

Representative tests:

- `tests/test_pgg_archon_mimo_micro_auditor.py`
- `tests/test_pgg_archon_audited_manifest_gate.py`
- `tests/test_pgg_archon_promptfoo_finalize.py`
- `tests/test_pgg_archon_legal_boundary_gate.py`

Representative Manifest keys:

- `latest_mimo_standard_micro_auditor_20260605`
- `latest_promptfoo_30_suite_audited_gate_20260605`
- `latest_promptfoo_30_suite_finalize_gate_20260605`
- `latest_promptfoo_30_suite_finalize_legal_gate_20260606`

Treat artifact paths and keys as examples, not permanent dependencies.
