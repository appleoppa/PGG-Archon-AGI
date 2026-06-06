# Rust-native β·Ω / APEX ΔE Evidence Pattern

Use when improving internal APEX ΔE / β·Ω scores with Rust-native modules.

## Durable lessons

1. Do not raise β·Ω by editing the evaluator or fabricating files. Increase it only with real, importable, signed Rust/PyO3 `.so` modules or explicitly change the scoring rubric with audit evidence.

2. When adding small Rust-native surfaces:
   - keep them read-only and bounded;
   - return JSON with `schema`, `status`, and `boundary`;
   - add Rust unit tests and Python pytest;
   - install into the active Hermes venv and verify import;
   - register SHA256 / ABI / `_PyInit_*` symbols.

3. If APEX ΔE reads 0 for `alpha_psi`, `lambda_phi`, or `evol_code`, inspect the Rust evaluator's exact expected paths before assuming the evidence is missing. A common pattern is to create a truthful index under the evaluator's expected path that points to existing artifacts rather than copying or inventing evidence.

4. Keep score semantics explicit:
   - APEX ΔE is an internal process/readiness score.
   - It is not an external AGI benchmark.
   - It is not legal correctness proof.
   - It is not evidence of 10x or full AGI.

5. LLM audit discipline:
   - GPT/Claude Responses API may return HTTP 200 with `output=[]`; do not count it as a valid audit unless visible text was extracted.
   - If a provider returns an SSE or parameter error, retry with the provider-specific accepted token parameter, but record both attempts.
   - Count only visible model text as successful review.

## Verification pack

Minimum evidence for a completed round:

- `cargo test --release` for every Rust crate.
- Python pytest for import/contract/boundary/invalid-input branches.
- `pytest tests/test_anti_hallucination_e2e.py` or equivalent regression.
- ABI/hash registry:
  - `file *.abi3.so`
  - `nm -gU *.abi3.so | grep PyInit_`
  - `codesign --verify --verbose=2 *.abi3.so`
  - sha256 for every `.so`
- APEX ΔE rerun and JSON readback.
- Manifest/ledger update and readback.
- Commit only source/build/test files, not venv `.so` binaries or transient workspace evidence.
