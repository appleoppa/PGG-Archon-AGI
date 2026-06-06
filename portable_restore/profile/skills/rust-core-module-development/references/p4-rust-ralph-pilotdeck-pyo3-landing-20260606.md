# P4 Rust Ralph/PilotDeck PyO3 Landing Lessons — 2026-06-06

## Context

During P4 Rust closure for Hermes/PGG, two new PyO3 crates (`hermes_pgg_ralph`, `hermes_pgg_pilotdeck`) were landed as bounded Rust surfaces. The useful reusable lesson is not the specific crate names; it is the verification and anti-overclaim pattern for small Rust/PyO3 surfaces that are not yet wired into runtime.

## Durable pattern

1. **Inventory before build**
   - Read each `Cargo.toml` and classify crate types (`cdylib`, `rlib`) and PyO3 features (`abi3-py311`).
   - Measure whether large directories are source or build artifacts. In this session each crate directory looked hundreds of MB only because `target/` was ~347MB.
   - Verify `target/` is ignored before staging.

2. **Do not count `cargo build` as Python readiness**
   - Run per-crate:
     - `cargo fmt -- --check`
     - `cargo test --locked`
     - `cargo build --release --locked`
   - Then expose the built artifact to the intended Python environment as an extension module, codesign on macOS, and run import smoke.

3. **Use build script with explicit environment override**
   - A good install script should infer repo root from script location but allow overrides:
     - `HERMES_AGENT_ROOT`
     - `PYO3_PYTHON`
     - `HERMES_PY_SITE`
   - It should copy/install `.abi3.so`, codesign it on macOS, and run import smoke for every module it installs.

4. **Skip-friendly pytest for installed PyO3 artifacts**
   - If a clean checkout will not have compiled `.so` artifacts, Python pytest should use `pytest.importorskip(...)`.
   - After `build_and_install.sh`, the same test becomes a strict import/API smoke because the module is present.
   - This avoids making source-only checkouts fail while still verifying installed artifacts in the landing gate.

5. **Anti-overclaim defaults for source-only fixtures**
   - If a Rust module emits sample governance/status data, default fixtures should normally be `WATCH`/source-only unless caller-supplied evidence proves PASS.
   - Include boundary text such as: source exists + config schema exists + import smoke passes, but this does not prove runtime integration, scheduler participation, PilotDeck runtime execution, external benchmark success, or AGI level.

6. **External/LLM review loop**
   - When the user asks for Claude/GPT review, make a real provider call with a compact review pack containing code, tests, build output, stage list, and truth boundary.
   - If the first review returns WATCH with must-fix items, repair and rerun targeted review before committing.

## Pitfalls observed

- **Bulk replacement can silently corrupt field names.** A replacement that changed status wording also accidentally turned `passed` into `source_onlyed`. Run grep/fmt/tests immediately after broad text edits and fix before continuing.
- **Do not stage local build products.** Forbidden staged patterns should include `target/`, `.dylib`, `.so`, `.rlib`, `.rmeta`, and venv/site-packages artifacts.
- **Import PASS is not runtime integration.** After import smoke, search Python/Web/tests outside `rust_modules/` for actual references. If none exist, report the boundary plainly.

## Verification example

```bash
cd /Users/appleoppa/.hermes/hermes-agent
for crate in rust_modules/hermes_pgg_ralph rust_modules/hermes_pgg_pilotdeck; do
  (cd "$crate" && /Users/appleoppa/.cargo/bin/cargo fmt -- --check)
  (cd "$crate" && /Users/appleoppa/.cargo/bin/cargo test --locked)
  (cd "$crate" && /Users/appleoppa/.cargo/bin/cargo build --release --locked)
done

HERMES_AGENT_ROOT=/Users/appleoppa/.hermes/hermes-agent \
  PYO3_PYTHON=/Users/appleoppa/.hermes/hermes-agent/venv/bin/python \
  /Users/appleoppa/.hermes/hermes-agent/rust_modules/build_and_install.sh

PYTHONPATH=/Users/appleoppa/.hermes/hermes-agent \
  /Users/appleoppa/.hermes/hermes-agent/venv/bin/python -m pytest -q tests/test_pgg_rust_pyo3_imports.py
```

## Boundary wording

Safe claim: Rust PyO3 source surfaces compile, install, codesign, import, and pass focused smoke locally.

Unsafe claim without more evidence: runtime integration, production Web/API participation, external benchmark success, legal correctness, full AGI, or T-level advancement.
