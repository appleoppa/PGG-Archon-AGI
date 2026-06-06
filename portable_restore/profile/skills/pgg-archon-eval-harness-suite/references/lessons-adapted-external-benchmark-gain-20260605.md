# Lessons — Adapted external benchmark smoke + evidence-gain loop (2026-06-05)

## Trigger

Use when PGG Archon / Apple Didi needs to improve AGI scoring evidence by addressing:

- “external benchmark” gap without claiming official benchmark pass
- cross-domain smoke beyond legal/system status surfaces
- before/after evolution-gain verification
- multi-LLM role-matrix orchestration where Agnes is held out as third-party auditor

## Role matrix convention

When user asks to “调用所有 LLM” for AGI/eval evolution and specifies roles:

- MiniMax = scheduler/orchestrator only; if long task times out, retry once with short scheduling prompt and record status.
- GPT = primary reasoning / logic.
- Claude = primary coding / architecture.
- DeepSeek + MiMo = support reviewers / gap checkers.
- Agnes/agents = **third-party audit only**; never include in ordinary processing, generation, coding, case drafting, or optimization pools.

Per-provider failures are isolated. Do not discard successful provider guidance because MiniMax/Agnes timed out; do not fabricate missing provider participation.

## Adapted external benchmark smoke pattern

A useful first step after a registry-only bridge is a tiny public-dataset smoke:

1. Fetch a public upstream sample with provenance and hash, e.g. GSM8K test JSONL from `openai/grade-school-math`.
2. Call a real Hermes provider on a small bounded sample (`limit=3` or `limit=5`).
3. Require an explicit final-answer marker, e.g. `FINAL_ANSWER: <number>`.
4. Score deterministically (numeric exact match for GSM8K smoke).
5. Write raw model output, latency, returncode/stderr, source hash, sample_count, passed_count, accuracy, and boundary.

Boundary wording must be explicit:

```text
Adapted external GSM8K smoke using public sample + real Hermes model call;
not official GSM8K score, not L2/full AGI proof.
```

This pattern proves that the evaluation chain can run on external public data. It does **not** prove model competence or official benchmark standing.

## Evidence-gain loop pattern

Before/after gain should measure exactly what changed. If the change is “registry-only → real smoke artifact exists”, the gain is **evidence-completeness gain**, not cognitive/model gain.

Required fields:

- before_score / after_score computed by script
- before_reason / after_reason
- evidence_path to the smoke report
- aggregate pass_delta / score_delta_mean / regression_count
- boundary: “Evidence-completeness gain only; not model capability gain.”

Do not rename evidence-gain into “AGI capability gain”. If the only improvement is artifact completeness, keep the manifest status at WATCH even if the gain report itself is PASS.

## Agnes third-party audit handling

Generate an audit packet containing artifact paths and hashes:

- bridge_report path + sha256
- adapted_external_smoke path + sha256
- evolution_gain_report path + sha256
- claims_to_audit
- boundary

Call Agnes with a short prompt that only asks for audit fields:

```json
{
  "audit_verdict": "PASS|WATCH|BLOCKED",
  "evidence_checked": [],
  "unsupported_claims": [],
  "missing_artifacts": [],
  "risk_level": "LOW|MEDIUM|HIGH",
  "truth_boundary": "..."
}
```

If Agnes times out or returns unparsed output, write `UNAVAILABLE_TIMEOUT` / `OK_UNPARSED` and do not claim third-party PASS.

## Verification gates

Minimum closure for this class of task:

- focused pytest covering provider policy / bridge / Agnes isolation passes
- py_compile for new runner modules passes
- benchmark smoke report exists and has `sample_count > 0` and raw model outputs
- gain report exists and includes script-computed delta
- manifest entry written and read back
- closure summary lists artifact sha256 values

## Pitfalls

- A 3/3 adapted GSM8K smoke is still only a tiny smoke, not a math benchmark.
- `source_type=adapted_external` must not be silently upgraded to `official_harness`.
- `official_harness` registration alone is not an official run.
- Evidence-completeness gain can be PASS while the overall AGI evolution status remains WATCH.
- Agnes unavailable means third-party audit is missing; do not fill in a plausible audit verdict yourself.
