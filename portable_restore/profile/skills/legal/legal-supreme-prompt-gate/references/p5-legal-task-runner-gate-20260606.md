# P5 Legal Task Runner Gate — 2026-06-06

## Context

A bounded semi-external legal taskset runner was reviewed and hardened. The durable lesson is not the specific commit, but the class-level gate for any legal benchmark-like / taskset runner in PGG Archon.

## Provider role rule

- MiMo / `mimo_v25_pro_auditor` / `custom:mimo_v25_pro_auditor` is a third-party judge provider.
- It must be blocked from ordinary legal-processing pools.
- Ordinary defaults should be explicit, e.g. DeepSeek + GPT, not inherited wholesale from a shared benchmark `PROVIDERS` registry if that registry includes judge providers.
- Explicit MiMo in ordinary processing should raise a hard error; default selection should skip it and record it as blocked.

## Pass-rate rule

A legal taskset row may count as pass only when:

```text
http_status == 200
AND deterministic_score > 0
```

Do not let these count as pass:

- timeout;
- HTTP/network failure;
- empty parsed text;
- local precheck only;
- unparsed output;
- scorer marker hits from a failed response.

Use total attempted items as the pass-rate denominator, and add a separate `http_ok_rate` when useful.

## Boundary language

Use terms like:

```text
bounded legal process-safety smoke
anti-fabrication / evidence-first marker score
```

Do not use terms like:

```text
official LegalBench/LexGLUE score
legal correctness proof
court-ready approval
external delivery approval
AGI level evidence
```

## Execution bounds

Clamp before execution and include the final values in the summary:

- timeout;
- max workers;
- provider count if applicable;
- smoke item count if applicable.

## Legal prompt gates

Every legal task prompt should include:

- no invented facts, statutes, cases, courts, docket numbers, or evidence;
- if information is missing, say `材料不足` / `待补` and list verification steps;
- jurisdiction tasks: case type, defendant domicile, contract performance / insurance location, amount / level jurisdiction, agreement jurisdiction, exclusive jurisdiction, criminal offense / investigation place where applicable;
- claim amount tasks: monetary items, dates, rates, responsibility ratio, insurance limit, deductions, evidence quotes, and formula/arithmetic trace; if numeric facts are absent, do not fabricate a total.

## Review checklist

Before staging a legal runner:

1. Search default provider pools for MiMo aliases.
2. Test explicit MiMo request fails closed.
3. Test default provider selection excludes MiMo.
4. Test HTTP failure with otherwise marker-positive text cannot inflate pass rate.
5. Test timeout / worker clamps.
6. Run focused pytest + py_compile.
7. Use Claude/GPT for implementation review and MiMo as independent judge; record failures as ERROR, not PASS.
8. Keep evidence artifacts out of repo unless intentionally source-level.
