# 2026-06-02 Token Gate / CodeGenesis diagnostics lessons

## Trigger

During a PGG Archon AGI continuation loop, the user asked for optimization and then repeatedly said “继续 / 怎么停了”. The task involved Rust Reasonix/APEX fusion gate verification and Hermes Agent CodeGenesis quality scanning.

## Durable workflow lessons

1. **Do not stop at a partially verified optimization.**
   - If readiness/benefit is >75%, low-risk and reversible, continue through: edit → targeted tests → health check → EVOLUTION_MANIFEST update → commit → concise evidence report.
   - If interrupted by a user asking “怎么停了”, immediately resume tool execution; do not answer with only status unless the task is truly finished.

2. **Split gate summary from full manifest.**
   - `self_evolution_token_gate_latest.json` should be a compact gate summary for automation consumers.
   - `fusion_manifest_latest.json` should keep the full Rust fusion manifest.
   - Add/keep a deterministic verifier such as `scripts/verify_gate_outputs.py` so future gate runs fail if the two schemas regress.

3. **For CodeGenesis WATCH states, improve observability before touching core code.**
   - Do not blindly fix files like `gateway/run.py` or `hermes_cli/auth.py` just because scanner reports parse errors.
   - First make the scanner report concrete diagnostics:
     - `parse_error_samples`: relative path, line, parser message.
     - `top_duplicate_lines`: count, first_seen, preview, and SHA-256 sample hash.
   - Then run targeted scanner tests, `py_compile`, `git diff --check`, health check, and manifest update.

4. **Keep commits scoped.**
   - Stage only the files changed for the current optimization.
   - Do not mix unrelated dirty files from other AGI/PGG workspaces into the commit.

## Verification pattern

Recommended closeout for this class of task:

```bash
cd ~/.hermes/hermes-agent
venv/bin/python -m pytest tests/agent/test_pgg_archon_codegenesis_scanner.py -q
venv/bin/python -m py_compile agent/pgg_archon_codegenesis_scanner.py
/usr/bin/git diff --check -- agent/pgg_archon_codegenesis_scanner.py
venv/bin/python -m apex_god.health
venv/bin/python -m apex_god.evolution_manifest --update
```

For the Rust fusion gate:

```bash
cd ~/.hermes/workspace/进化/rust/pgg_reasonix_apex
cargo test
scripts/self_evolution_token_gate.sh
python3 scripts/verify_gate_outputs.py
```

## Reporting style

Use concise field-based Chinese output: status, changed files, tests, health, manifest hash, commit hash, remaining risks. Avoid long explanations while the user is pushing “继续”.
