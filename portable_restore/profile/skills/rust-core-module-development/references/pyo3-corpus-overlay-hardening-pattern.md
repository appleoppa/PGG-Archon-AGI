# PyO3 Rust Surface Corpus + Overlay Governance Hardening Pattern

Use when a Rust-native PyO3 surface was already added and needs to move from “import/build smoke” toward stronger internal engineering evidence without overclaiming capability.

## Durable lesson

A `.so` count or successful import can raise an internal readiness metric, but it is not enough evidence for maintainability. Harden with three evidence layers:

1. Rust unit tests for each crate.
2. Python pytest over the installed `.abi3.so` boundary.
3. ABI/hash/codesign registry plus lightweight performance baseline.

Keep all claims bounded: internal engineering verification only; not full AGI, not external benchmark, not domain correctness proof.

## PyO3 macOS test pitfall

For small independent PyO3 modules that must run both `cargo test` and Python import tests:

- Prefer `pyo3 = { features = ["abi3-py311"] }` with macOS dynamic lookup configuration.
- Avoid enabling `extension-module` in those crates if `cargo test` produces missing Python symbols such as `_PyExc_BaseException` / `_PyExc_SystemError`.
- After release build, copy the dylib to `venv/lib/python*/site-packages/<module>.abi3.so`, then run:

```bash
codesign --remove-signature <module>.abi3.so || true
codesign --force --sign - <module>.abi3.so
python - <<'PY'
import importlib
for name in ['hermes_pgg_status', 'hermes_pgg_ecc', 'hermes_pgg_overlay']:
    m = importlib.import_module(name)
    print(name, m.version())
PY
```

## Corpus / property-style tests without adding heavy dependencies

When avoiding new test dependencies, still add fixed corpus tests that exercise malformed and extreme inputs. Label them honestly as corpus/property-style, not full fuzzing.

Recommended cases:

- empty string
- `null`
- arrays where an object is expected
- negative overflow values
- positive overflow values
- type mismatches: strings, booleans, nested objects
- missing summary fields or weird summary shapes

For scoring surfaces, assert invariants, not just exact outputs:

- score is always in `[0,100]`
- penalty is always in `[0,100]`
- invalid JSON returns a valid JSON report
- status remains bounded to known values such as `PASS`/`WATCH`/`BLOCKED`

## Python pytest boundary checks

Add Python tests against the installed `.abi3.so`, not only Rust source tests:

- import all modules
- check version/boundary wording
- validate JSON schema fields
- check invalid input behavior
- verify `_PyInit_<module>` appears in `nm -gU <module>.abi3.so`
- compute SHA256 of each installed `.so`
- run a lightweight loop benchmark and keep wording bounded as “baseline”, not system benchmark

## ABI/hash registry

Generate a registry JSON with:

- module name
- installed path
- bytes
- sha256
- `file` output
- `_PyInit_*` symbol output
- `codesign --verify --verbose=2` result on macOS

This registry is evidence for reproducibility and binary identity; it does not prove production runtime participation.

## Overlay decision matrix pattern

When ignored overlays exist under `.git/info/exclude`, do not bulk commit or delete them. Build a decision matrix first:

- `PROMOTE_CANDIDATE_AFTER_DEDICATED_TESTS` — high-value formula/gate/sequence modules that need tests before tracking.
- `PROMOTE_CANDIDATE_LOW_RISK` — importable and referenced by tracked surfaces.
- `ARCHIVE_OR_PROMOTE_AFTER_REVIEW` — importable with public symbols but no tracked usage.
- `ARCHIVE_CANDIDATE_KEEP_RUNTIME_COPY_UNTIL_CONFIRMED_UNUSED` — low-reference modules; archive only after log/skill usage scan.
- `KEEP_LOCAL_RUNTIME_OVERLAY_PENDING_DEEP_ABSORPTION` — directory overlays that are current runtime dependencies.

The decision report should explicitly state: no deletion, no bulk commit, no restoration of historical code, and no runtime capability claim from importability alone.

## Verification gate before commit

Run and record:

```bash
git diff --check
for d in rust_modules/hermes_pgg_status rust_modules/hermes_pgg_ecc rust_modules/hermes_pgg_overlay; do
  (cd "$d" && cargo test --release) || exit 1
done
rust_modules/build_and_install.sh
python -m pytest tests/test_rust_pgg_surfaces.py tests/test_anti_hallucination_e2e.py -q
```

If using an internal evolution evaluator, rerun it and store output JSON. Report structural/runtime boundaries separately.

## Cross-model audit lesson

If LLM audit is performed before final test evidence is attached, a model may correctly return WATCH for “missing current test output.” After tests are run, include those outputs in completion evidence and say that the condition was satisfied; do not silently upgrade the model’s score.

Responses API quirk: a provider may return HTTP 200 with usage but `output=[]` or empty visible text. Count it as an attempted call but not an effective audit conclusion.
