# PyO3 property-test + ignored-overlay validation pattern

Use when hardening small Rust/PyO3 audit surfaces and validating local ignored runtime overlays without turning them into hard dependencies.

## Trigger

- A Rust/PyO3 surface currently has only fixed corpus tests and needs stronger boundary coverage.
- A local ignored overlay is a promotion candidate, but bulk-committing the overlay would be unsafe.
- You need evidence that a module is importable/smoke-testable while preserving clean-checkout behavior.

## PyO3 property-test pattern

1. Add `proptest` as a dev dependency only:

```toml
[dev-dependencies]
proptest = "1.6"
```

2. Keep runtime dependencies unchanged; do not add proptest to `[dependencies]`.
3. For small independent PyO3 extension modules that also need `cargo test`, prefer:

```toml
pyo3 = { version = "0.20", features = ["abi3-py311"] }
```

Avoid `extension-module` in these small crates if `cargo test` must run on macOS; it can produce Python symbol link failures.

4. Add one property test per invariant:

- status surfaces: `failed_count == checked_count.saturating_sub(ok_count)` and PASS/WATCH state logic.
- ECC/scoring surfaces: score and penalty stay in `0..=100`; status remains in the allowed enum.
- inventory/overlay surfaces: numeric fields are extracted exactly or safely default to zero.

5. Run the full loop:

```bash
for d in rust_modules/hermes_pgg_status rust_modules/hermes_pgg_ecc rust_modules/hermes_pgg_overlay; do
  (cd "$d" && cargo fmt && cargo test --release) || exit 1
done
rust_modules/build_and_install.sh
./venv/bin/python -m pytest tests/test_rust_pgg_surfaces.py tests/test_anti_hallucination_e2e.py -q
```

## Skip-friendly ignored-overlay validation

For ignored/local overlays, tests must not make a clean checkout fail. Pattern:

```python
if not overlay_path.exists():
    pytest.skip(f"local ignored overlay absent: {overlay_path}")
module = importlib.import_module(module_name)
```

Then validate only:

- import succeeds;
- expected real public symbols exist;
- the values are callable/classes;
- a small read-only smoke call works if the signature permits it.

If a smoke call requires richer runtime context, skip after symbol verification rather than fabricating inputs.

## Pitfalls

- Do not invent expected symbols from memory. Introspect `dir(module)` and `inspect.signature()` first, then write the test.
- If an initial overlay test fails because the symbol names were wrong, fix the test against real symbols; do not modify the ignored overlay just to satisfy the test.
- For typed APIs, construct the real dataclass/context object (for example `MeasurementResult` + `ParameterMeasurement`) instead of passing a generic dict.
- Do not treat local overlay tests as a reason to bulk-commit, delete, or promote ignored overlays.
- Report property-test counts truthfully: fixed corpus tests and proptest cases are both useful but not the same as fuzzing or external benchmarking.

## Evidence to record

- `cargo test --release` output per crate.
- Python pytest output.
- build/install output and `.so` hashes if relevant.
- A clear boundary statement: internal engineering verification only; not full AGI, not external benchmark, not legal correctness proof.
