# Lessons: Rust promptfoo gate + APEX postcheck default-off hook (2026-06-06)

## Trigger

Use this when a promptfoo/GSM8K/legal-boundary smoke suite has already passed once and the next step is to make it repeatable as an audited evolution gate.

## Durable pattern

### 1. Rust outer gate, Python thin adapters

Preferred architecture:

- Rust CLI does orchestration, deterministic validation, sha256, Manifest readback, and final PASS/WATCH verdict.
- Existing Python modules remain thin adapters for the real integration points:
  - promptfoo Python provider calling `hermes -z`
  - promptfoo finalizer
  - MiMo micro-auditor
  - legal boundary gate
- Rust must not fabricate promptfoo raw results, MiMo audit JSON, or Manifest PASS.

This avoids rewriting already-working provider/finalizer code while making the gate repeatable and harder to overclaim.

### 2. Avoid stale claim wording

Do not reuse fixed `30-suite` audit claims for a `50-suite`. Parameterize claims with the real sample count and suite label.

Safer wording:

```text
自建promptfoo CLI smoke（使用promptfoo官方CLI工具执行）
```

Avoid wording that can be misread as an official benchmark result:

```text
official benchmark score
official public benchmark complete score
```

### 3. MiMo strict JSON retry pattern

MiMo may return fenced JSON or a JSON-looking object whose `reason` contains unescaped quotes. Do not hand-edit this into PASS.

Hardening pattern:

- Prompt: `STRICT JSON`, no Markdown code block.
- `reason`: one sentence, no double quotes, no newline, no backslash.
- On `OK_UNPARSED`, `UNAVAILABLE_TIMEOUT`, or `ERROR`, run one targeted retry for that audit name.
- Merge only if retry is real `OK_PARSED` and verdict is one of `PASS/WATCH/BLOCKED`.
- Recompute pass_count from rows; never trust top-level count blindly.

### 4. Final report should carry boundary summaries

If legal-boundary PASS appears only in Manifest but not in the final report, LLM auditors may flag a layer mismatch. Include a report-level field like:

```json
"legal_boundary_gate_summary": {
  "expected_status_when_prechecked": "PASS",
  "scope": "deterministic boundary-statement presence check only; not legal correctness proof",
  "required_statement_count": 4
}
```

This is still not legal correctness proof.

### 5. APEX postcheck hook path

Low-risk integration sequence:

1. Create the Rust gate binary.
2. Add a stable shim under `~/.hermes/bin/`.
3. Write a policy under `~/.hermes/workspace/evolution/gates/*.json` with:
   - `status: ACTIVE_OPTIONAL_DEFAULT_OFF`
   - `entrypoint`
   - `target`
   - `target_sha256`
   - `fail_closed: true`
   - explicit boundary text.
4. Add `apex13 postcheck list` to discover default-off gates and verify target hash.
5. Add `apex13 postcheck run <gate_id> -- <args>` for manual execution.
6. Do not modify launchd/fused-watch automatic execution until separately authorized.

### 6. Cargo.lock discipline

If a Rust repo is built with `cargo --locked`, do not add new dev-dependencies just for tests unless you intend to update and commit `Cargo.lock`. Prefer std-only temp directories for small unit tests.

### 7. Completion evidence checklist

A repeatable gate is not complete until all are true:

- Rust tests pass.
- Python focused tests pass if Python adapters changed.
- Rust binary builds release.
- `postcheck list` or equivalent discovers the gate with `target_sha256_ok=true`.
- Manual `postcheck run` or Rust gate smoke returns `status=PASS`.
- Manifest has a key for discovery/registration and a key for the real run.
- Artifact/report/audit/closure sha256 values are read back.
- Claude/GPT review, if claimed, is a real provider call and records `PASS/WATCH` honestly.

## Boundary

This pattern proves a bounded smoke gate is repeatable. It does not prove official benchmark performance, legal correctness, automatic background enablement, L2, or full AGI.
