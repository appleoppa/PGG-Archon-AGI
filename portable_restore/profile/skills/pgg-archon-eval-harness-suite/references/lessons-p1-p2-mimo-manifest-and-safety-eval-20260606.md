# Lessons — P1/P2 MiMo manifest gate + bounded safety/eval hardening (2026-06-06)

## Scope

Session class: PGG Archon eval / safety / manifest-gate hardening.

This reference captures reusable rules from two scoped closures:

- P1: `audited_manifest_gate + mimo_micro_auditor + legal_boundary_gate`
- P2: bounded safety/eval smoke tools (`safety_provider_run`, adapted GSM8K smoke, case closed-loop eval, evidence-gain smoke, GPT55 Hermes CLI runner, promptfoo finalize)

Boundary: internal engineering anti-overclaim and smoke/evidence tooling only. Not legal correctness proof, not official benchmark score, not AGI level proof.

## P1 — Manifest PASS must require a real MiMo judge result

Hard rule:

```text
manifest PASS is allowed only when:
1. requested_status == PASS
2. judge_called == true
3. results is non-empty
4. timeout_count == 0
5. reported_pass_count == eligible_pass_count recomputed from rows
6. every row has status == OK_PARSED and audit_verdict == PASS
```

Do not trust top-level `pass_count` alone. Recompute eligibility from `results` rows.

Statuses that must never count as PASS:

```text
LOCAL_PRECHECK_ONLY
OK_UNPARSED
ERROR
UNAVAILABLE_TIMEOUT
missing judge_called
returncode != 0, even if stdout contains parseable JSON PASS
```

Implementation pattern:

- `MicroAuditSummary` includes `judge_called`.
- `call_mimo=False` produces `LOCAL_PRECHECK_ONLY` with `audit_verdict=None`.
- `decide_manifest_status` appends `mimo_judge_not_called` when judge was not called.
- `run_one_mimo_audit` treats subprocess non-zero return code as `ERROR` before parsing stdout.
- Manifest entry should include `audit_gate.judge_called` so future readers need not open the summary file to detect no-MiMo downgrade.

Test cases to include:

- `judge_called=True + pass_count=len(results) + results=[{}]` => WATCH.
- `LOCAL_PRECHECK_ONLY + audit_verdict=PASS` => WATCH.
- `OK_UNPARSED + audit_verdict=PASS` => WATCH.
- Only all `OK_PARSED/PASS` rows => PASS.
- `--no-mimo` CLI smoke => WATCH with `judge_called=false`.

## P1 dependency pitfall

After committing a new gate module, immediately run an import smoke from a clean staged perspective. In this session, `audited_manifest_gate.py` imported a new untracked `pgg_archon_legal_boundary_gate.py`; tests passed in the dirty workspace but a clean checkout would have failed. Fix by staging/committing the dependency and its tests as a separate scoped dependency commit.

Minimum import smoke:

```bash
PYTHONPATH=$HOME/.hermes/hermes-agent python3 - <<'PY'
from agent.pgg_archon_audited_manifest_gate import decide_manifest_status
from agent.pgg_archon_legal_boundary_gate import evaluate_legal_boundary_text
print('IMPORT_OK')
PY
```

## P2 — MiMo is a held-out judge, not a normal processing provider

MiMo policy after user correction:

```text
MiMo / mimo_v25_pro_auditor = fixed third-party audit/benchmark judge.
Agnes = ordinary/non-critical processing channel; instability recorded honestly.
```

For ordinary safety/eval provider pools:

- Defaults must exclude `mimo` and `mimo_v25_pro_auditor`.
- Explicitly passing either alias to a normal processing pool must fail closed with a clear `ValueError`.
- MiMo may still be called in an explicit audit/judge path such as audited manifest gate or targeted third-party review.

Test case:

```python
with pytest.raises(ValueError, match="reserved for third-party judge"):
    _reject_third_party_judge_in_processing_pool(["deepseek", "mimo"])
```

## P2 — bounded smoke status must not overclaim

For adapted external / local smoke / evidence gain tools:

- Provider returncode must be `0` before an item can count as passed.
- Timeout should normalize to returncode `124`.
- A correct-looking answer in stdout with non-zero returncode must not count as passed.
- Smoke runner summary should separate execution completion from verdict:
  - `run_status: COMPLETED`
  - `status: WATCH`
- Evidence completeness improvements should be exposed as `evidence_improved: true/false`, while `after_status` remains `WATCH` unless a real external gate explicitly permits PASS.

Do not use `status: OK` for local/adapted smoke when downstream code may read it as benchmark PASS.

## P2 — Hermes CLI runner pattern

For GPT55 / Claude / Hermes provider-path smoke runners:

- Prefer Hermes CLI/provider path over raw provider URL calls when testing the actual user-facing Hermes runtime.
- Resolve CLI via `HERMES_BIN` or `PATH` only.
- Do not silently fallback to a machine-specific path; if unresolved, return rc `127` with an explicit error.
- Include `--cli`, `--provider custom:<provider>`, and `--model <model>` in argv when intentionally testing classic CLI execution.
- Timeout returns rc `124`; missing binary returns rc `127`; neither can count as pass.

## Multi-LLM review pattern

When calling multiple LLMs:

- GPT/Claude should perform code/governance review.
- MiMo should be called only as third-party judge.
- DeepSeek can provide ordinary reference review.
- MiniMax/Agnes timeouts are recorded as ERROR and do not block remaining clean channels.
- If an LLM process exits non-zero, do not count a parsed JSON PASS from partial stdout as clean PASS. Re-run a targeted shorter prompt if the channel matters.

## Commit discipline

For these harness/gate closures:

1. Build a review pack under `~/.hermes/workspace/pgg-archon-governance/<topic>/`.
2. Run focused pytest + py_compile.
3. Run GPT/Claude + MiMo targeted review after must-fix changes.
4. Stage only scoped files.
5. Pre-commit check must ensure Router/Web/Rust/pnpm/workspace are not staged unless that is the current scoped group.
6. Commit.
7. Write `EVOLUTION_MANIFEST.json` with commit, evidence paths, tests, LLM verdicts, and truthful boundary.

## Related commits from this session

These are examples only; do not encode them as future requirements:

- P1 manifest gate: `e6ae47ec3`
- P1 legal boundary dependency: `d7f71e6ae`
- P2 safety/eval smoke tooling: `f69ed043f`
