# Rust promptfoo gate + fused watcher postcheck lessons — 2026-06-06

## Scope

This reference captures the reusable pattern for turning a one-off promptfoo adaptive 50-suite success into a Rust-native, audited, periodic evolution postcheck.

Boundary: this is a smoke/evidence gate. It is not an official benchmark score, not legal correctness proof, and not L2/full AGI proof.

## Final architecture

1. `pgg-promptfoo-gate` Rust binary orchestrates the deterministic shell:
   - promptfoo raw/log evidence validation
   - Python finalizer call as a thin adapter
   - legal boundary precheck
   - MiMo micro audit gate
   - EVOLUTION_MANIFEST readback
   - sha256 cross-checks
2. `~/.hermes/bin/pgg-promptfoo-gate` symlink exposes the binary.
3. `~/.hermes/workspace/evolution/gates/promptfoo_adaptive_50_rust_gate_policy.json` registers the gate as `ACTIVE_OPTIONAL_DEFAULT_OFF` with target sha256.
4. `apex13 postcheck list/run` discovers and manually runs default-off gates.
5. `apex13 fused-watch` can be explicitly launched with:
   - `--postcheck-gate-id promptfoo_adaptive_50_rust_gate`
   - `--postcheck-interval-secs 21600`
6. launchd plist can carry those args only after backup and short-run verification.

## Durable fixes / patterns

### 1. Do not rely only on promptfoo run logs

A shared promptfoo log can be truncated or overwritten by an interrupted run. Both the Python finalizer and Rust gate should:

1. parse `Results:` from the CLI log first;
2. if unavailable, strictly recompute pass/fail/error counts from promptfoo raw JSON `results.results`;
3. mark the report with `counts_source`, e.g. `promptfoo_raw_json_fallback`.

This is evidence fallback, not fabricated counts.

### 2. launchd has a sparse PATH

MiMo auditor subprocess calls must resolve Hermes CLI robustly. Use an explicit resolver order:

1. `HERMES_CLI`
2. `/Users/appleoppa/.local/bin/hermes`
3. `/Users/appleoppa/.hermes/hermes-agent/venv/bin/hermes`
4. `/usr/local/bin/hermes`
5. `/opt/homebrew/bin/hermes`
6. `hermes` fallback

Do not encode "hermes command is unavailable" as a durable conclusion; fix CLI resolution.

### 3. Policy target sha256 is a feature

When the Rust gate binary is rebuilt, `postcheck list/run` should fail with target sha mismatch until the policy JSON is refreshed. Treat this as drift protection, not a failure to bypass.

Record the policy hash refresh in EVOLUTION_MANIFEST.

### 4. Compact dirty guards

A fused watcher log can be polluted if the gate records a full dirty workspace list. Dirty reporting should include:

- `dirty_count`
- `unrelated_dirty_count`
- `dirty_sample` capped to a small number such as 50
- `unrelated_dirty_sample` capped similarly
- `truncated: true/false`

Never dump hundreds/thousands of untracked files into watcher logs.

### 5. Default-off before periodic

Safe rollout sequence:

1. create Rust gate and run it manually;
2. register policy as `ACTIVE_OPTIONAL_DEFAULT_OFF`;
3. add `apex13 postcheck list/run` discovery/manual execution;
4. short-run fused watcher with a temporary log and explicit postcheck args;
5. patch launchd only after backup;
6. restart launchd;
7. verify process args and first `_postcheck_gate` log line;
8. only then mark Manifest as enabled and verified.

## Verification checklist

- `cargo test --locked` for `hermes_pgg_promptfoo_gate`
- `cargo build --release --locked` for `hermes_pgg_promptfoo_gate`
- Python focused tests for:
  - MiMo auditor
  - audited manifest gate
  - promptfoo finalizer
- `cargo test --locked` and `cargo build --release --locked` for `apex-evolution-engine`
- `apex13 postcheck list --output <json>` returns:
  - `PASS_GATES_DISCOVERED_DEFAULT_OFF`
  - `runnable_count >= 1`
  - `target_sha256_ok: true`
- `apex13 postcheck run promptfoo_adaptive_50_rust_gate -- ...` returns parsed PASS
- launchd process command line includes postcheck args
- fused watcher log contains `_postcheck_gate` with:
  - `exit_code: 0`
  - `status: PASS`
  - `parsed_status: PASS`
  - non-null `manifest_key`
- Manifest linked key has MiMo `judge_called=true`, `pass_count=3`, `audit_count=3`, `timeout_count=0`

## Reporting boundary

Allowed wording:

> Fused watcher has a periodic promptfoo adaptive 50-suite Rust postcheck enabled and first background verification passed.

Forbidden wording:

- official benchmark passed
- legal correctness verified
- full AGI / L2 reached
- no-supervision production takeover
