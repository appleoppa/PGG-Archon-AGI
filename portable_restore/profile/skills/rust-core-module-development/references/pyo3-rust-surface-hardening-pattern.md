# PyO3 Rust Surface Hardening Pattern

Use when adding small Rust-native/PyO3 modules to Hermes/PGG as additive read-only capability surfaces.

## Pattern

1. Keep each Rust surface bounded and explicit:
   - status/summary functions only unless deeper integration is intentionally required.
   - JSON input/output contracts.
   - `boundary` field in every returned report.
   - no filesystem mutation, no model calls, no provider routing, no core scheduler/security mutation.

2. Build shape for small modules:
   - `crate-type = ["cdylib"]`
   - PyO3 features: prefer `abi3-py311` for small independent extension modules that also need `cargo test`.
   - On macOS keep `.cargo/config.toml` dynamic lookup flags:
     - `-C link-arg=-undefined`
     - `-C link-arg=dynamic_lookup`
   - install as `<module>.abi3.so` into the active Hermes venv `site-packages`.
   - run `codesign --remove-signature || true` then `codesign --force --sign -`.

3. Important PyO3 pitfall:
   - `pyo3 = { features = ["extension-module", "abi3-py311"] }` can make `cargo test` binaries fail on macOS with missing Python symbols such as `_PyExc_BaseException`.
   - For independent small modules, remove `extension-module` and use `abi3-py311` plus dynamic lookup config so both Python import and Rust unit tests work.

4. Verification gates:
   - `cargo fmt`
   - `cargo test --release` for every crate.
   - Rebuild and install into the intended venv.
   - Python import smoke for each module.
   - `pytest` covering:
     - importability
     - JSON schema/contract
     - invalid input boundary
     - PASS/WATCH/BLOCKED branches where applicable
     - no mutation/capability boundary strings
   - ABI/symbol check:
     - `file <module>.abi3.so`
     - `nm -gU <module>.abi3.so | grep PyInit_`
     - `codesign --verify --verbose=2 <module>.abi3.so`
   - SHA256 registry for every installed `.so`.
   - lightweight performance baseline if the surface will be called often.

5. Reporting discipline:
   - Treat increased `.so` count as an internal Rust-native readiness/process signal only.
   - Do not claim full AGI, 10x, external benchmark success, legal correctness, or runtime participation solely from import/build success.

## Minimal build script shape

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="/Users/appleoppa/.hermes/hermes-agent"
SITE="$ROOT/venv/lib/python3.11/site-packages"
export PYO3_PYTHON="$ROOT/venv/bin/python"
for crate in hermes_pgg_status hermes_pgg_ecc hermes_pgg_overlay; do
  (cd "$ROOT/rust_modules/$crate" && cargo build --release)
  cp "$ROOT/rust_modules/$crate/target/release/lib${crate}.dylib" "$SITE/${crate}.abi3.so"
  codesign --remove-signature "$SITE/${crate}.abi3.so" 2>/dev/null || true
  codesign --force --sign - "$SITE/${crate}.abi3.so"
  "$ROOT/venv/bin/python" -c "import $crate; print($crate.version())"
done
```
