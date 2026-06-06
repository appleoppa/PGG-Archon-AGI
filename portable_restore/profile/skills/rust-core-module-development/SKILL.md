---
name: rust-core-module-development
description: Rust 核心模块开发：从零实现 Hermes 核心能力，包括 PyO3 FFI、编译配置、测试验证
tags: [rust, pyo3, ffi, core-development, performance]
---

# Rust Core Module Development — Compact

## Trigger

Use when implementing Hermes/PGG core capability in Rust, especially PyO3 FFI, performance modules, tokenizer/context engine, sidecars, or replacing Python logic with Rust.

## Non-negotiables

- If the purpose is Rust replacement, do not fall back to Python as the final implementation just for speed.
- On macOS PyO3, expect signing/linking pitfalls.
- Verify with compile + Python import + unit tests.

## macOS PyO3 checklist

- Configure dynamic lookup linking.
- Ensure `PYO3_PYTHON` points to the intended venv Python.
- Avoid `#[pyfunction]` names colliding with module names.
- For small independent extension modules that must also run `cargo test`, prefer `pyo3` with `abi3-py311` and dynamic lookup config; `extension-module` can make macOS test binaries fail with missing Python symbols such as `_PyExc_BaseException`.
- After build, run:

```bash
codesign --remove-signature <compiled-extension> || true
codesign --force --sign - <compiled-extension>
```

Without this, macOS may SIGKILL the extension.

**Verifier shebang / ABI pitfall:** if a verification script imports a PyO3 extension installed in the Hermes venv, run it with the same venv Python in the shebang (for example `#!/Users/appleoppa/.hermes/hermes-agent/venv/bin/python`). Do not use system `python3` plus manual `sys.path` injection to load a venv `.so`; on macOS this can crash with `PyInterpreterState_Get` / GIL / ABI errors. Treat that as a verifier-interpreter bug, fix the shebang, and rerun the smoke rather than calling the Rust module failed.

Detailed hardening pattern: `references/pyo3-rust-surface-hardening-pattern.md`.

## Development loop

1. Define Rust API and Python FFI boundary.
2. Add unit tests in Rust and Python import tests.
3. Build in the project venv.
4. Codesign compiled extension on macOS.
5. Run targeted tests and a real smoke call.
6. Document exact command and rollback path.

## Safety

Do not modify Hermes core scheduler/security boundaries without explicit authorization. Prefer additive sidecar or module replacement with tests.

## Rust compile and integration honesty gate

For PGG Archon / Hermes Rust work, completion requires more than `cargo build`:

1. **Classify crates and surfaces first** — list every relevant `Cargo.toml`, crate type (`rlib`, `cdylib`, Tauri app), and intended runtime surface.
2. **Use an independent gate when requested** — if the user asks for Claude/GPT participation, make a real provider call and record that it returned successfully; do not role-play the audit.
3. **Compile/test each crate separately** — record working directory, exact command, exit code, and log path. Do not merge multiple crates into one vague PASS.
4. **PyO3/macOS gate** — for `cdylib` modules, `cargo build` is not enough. Copy or install the produced library as a Python extension (`.so`/`.abi3.so` as appropriate), codesign on macOS if needed, then run Python `import`, `version()`, and at least one exported function call. If a smoke call fails because the smoke used the wrong function signature, fix the smoke and rerun; don’t label it a Rust compile failure.
5. **Tauri/release gate** — if a combined gate times out while compiling a Tauri app, mark the gate WATCH/PARTIAL and rerun the Tauri release build separately with a longer timeout. Do not count `cargo test` or partial compile logs as release build success.
6. **Runtime integration gate after compile PASS** — after compile/import PASS, search for Python/Web/API/test references that actually use the Rust surface. Run targeted tests for those integration points. If tests expose API-contract drift in Python wrappers, fix the compatibility layer or tests and rerun before claiming runtime participation.
7. **Evidence artifact** — write a `result.json` with schema, timestamp, status, expected checks, missing/failing checks, artifacts with sha256, and a boundary statement. Update `EVOLUTION_MANIFEST.json` only after readback.

Boundary language: compile/import PASS proves local buildability and smoke usability on this machine; it does not prove full AGI, external benchmark success, security audit completion, or production runtime participation unless the integration gate also passes.

## Rust compile and runtime integration gate

For Rust work in this profile, do not stop at `cargo build` or `cargo test` when the crate is meant to back Python/UI/runtime behavior. Use a layered gate and report each layer separately:

1. **Inventory**: find every relevant `Cargo.toml`, classify `rlib`, `cdylib`/PyO3, Tauri/desktop, CLI smoke binaries, and whether each is expected to be runtime-facing.
2. **Compile/test**: run `cargo test` and `cargo build --release` per crate; record path, command, exit code, log path, artifact path, and sha256. On macOS, prefer `/Users/appleoppa/.cargo/bin/cargo` if PATH is uncertain.
3. **PyO3 import smoke**: for `cdylib` PyO3 crates, copy or install the release dylib as a Python extension, `codesign --remove-signature || true`, `codesign --force --sign -`, then import with the target Python and call at least one exported function. A wrong smoke-test argument is a test defect to fix and rerun, not proof the Rust module failed.
4. **Runtime integration**: search for non-`rust_modules/` references from Python/Web/tests, then run focused pytest for the actual bridges. Treat API-contract drift (missing compatibility wrappers, changed return shapes, monkeypatch facades) as a real integration defect, not a Rust compile failure.
5. **Evidence settlement**: write a gate `result.json` under `~/.hermes/workspace/pgg-archon-governance/`, update `~/.hermes/data/EVOLUTION_MANIFEST.json`, and read both back before saying PASS.

Truth boundary: `cargo build` PASS ≠ PyO3 import PASS; PyO3 import PASS ≠ runtime integration PASS; focused local integration tests PASS ≠ live Web UI usage, production traffic routing, external benchmark success, or AGI level increase.

## macOS PyO3 / Rust verification gate

For Rust/PyO3/runtime work, do not stop at `cargo check`. A truthful gate should normally include:

1. `cargo test --locked` and `cargo build --release --locked` per crate.
2. For PyO3 `cdylib`, copy/sign or otherwise expose the release artifact with a Python extension suffix and run a real `python import` smoke that calls at least one exported function.
3. For Tauri/Rust UI crates, run the crate’s release build separately with enough timeout; a wrapper timeout is `WATCH`, not `PASS`.
4. Record rustc/cargo/python/macOS architecture, command, exit code, log path, and artifact SHA-256.
5. If a smoke fails because the smoke call used the wrong function signature, fix the smoke and rerun; classify the initial result as smoke-contract failure, not Rust compile failure.
6. When staging a new Rust crate, include `Cargo.lock` when reproducibility matters and include proptest regression seeds when present and relevant.

Boundary: compile/import/build gates prove local surfaces work on this machine; they do not prove production runtime participation or AGI capability.



- `references/full-skill-archive-20260601.md`
- `references/pyo3-verifier-interpreter-pitfall.md` — standalone verifier scripts for venv-installed PyO3 modules must use the same venv Python shebang; avoid system Python + manual `sys.path` injection causing GIL/ABI crashes.
- `references/pyo3-multi-module-beta-omega-pattern.md` — bounded multi-module PyO3 uplift pattern for internal Rust-native readiness metrics, including macOS copy/codesign/import/ΔE verification and truthful boundary wording.
- `references/pyo3-property-overlay-validation-pattern.md` — property-based testing for small PyO3 surfaces plus skip-friendly validation of ignored local overlays without making clean checkouts fail.
- `references/p4-rust-ralph-pilotdeck-pyo3-landing-20260606.md` — P4 Ralph/PilotDeck landing lessons: Claude review loop, `target/` and binary artifact exclusion, anti-overclaim source-only defaults, build script env overrides, PyO3 install/codesign/import smoke, skip-friendly pytest, and post-import runtime-integration boundary.
- `references/pyo3-corpus-overlay-hardening-pattern.md` — harden PyO3 surfaces after initial uplift with Rust unit tests, Python ABI/hash tests, malformed corpus/property-style checks, overlay decision matrices, and bounded cross-model audit wording.
