# Rust-native β·Ω and ignored overlay hardening pattern (2026-06 Round6–12)

Use this reference when hardening PGG Archon/Hermes evolution code with Rust-native readiness metrics and ignored runtime overlays.

## Durable pattern

1. Start with a truthful baseline:
   - `git status --short --ignored=matching`
   - current commit
   - import / py_compile / pytest status
   - APEX ΔE via `hermes_apex_evolution.py_evaluate(workspace, out)`
   - list ignored overlays with `git check-ignore -v`

2. Separate scores:
   - Ledger/workspace readiness can be high when evidence exists in workspace artifacts.
   - Fresh agent-root ΔE can be low when `evolution/super_evolution13/source_scout.json` or `evol_events.jsonl` are missing.
   - Report both side by side; never use the higher score to hide the lower baseline.

3. For β·Ω improvement, prefer real Rust-native PyO3 modules over score manipulation:
   - Add small read-only Rust modules only if they expose real deterministic logic.
   - Build with `abi3-py311`; for small extension modules that must also run `cargo test`, avoid PyO3 `extension-module` because macOS test binaries may fail with unresolved Python symbols.
   - Copy `.dylib` to `venv/lib/python3.11/site-packages/<module>.abi3.so`.
   - `codesign --remove-signature ... || true` then `codesign --force --sign - ...`.
   - Verify Python import and smoke call.

4. Harden Rust surfaces with layered tests:
   - Rust unit tests for basic contracts.
   - Python pytest for import, JSON schema, invalid input, ABI `_PyInit_*`, sha256 registry, and lightweight performance.
   - `proptest` property-based tests when fixed corpus tests are not enough.
   - Re-run `cargo test --release`, build/install, Python pytest, and APEX ΔE.

5. Manage ignored overlays with evidence gates:
   - Do not bulk-add or bulk-delete ignored overlay files.
   - Generate a per-file readiness matrix: importability, public symbols, references, absolute paths, DB use, subprocess/launchctl/cron, filesystem writes, env/network access.
   - Classify modules as:
     - `PROMOTE_CANDIDATE_WITH_TESTS`
     - `PROMOTE_ONLY_AFTER_PATH_SIDE_EFFECT_REFACTOR`
     - `KEEP_RUNTIME_OVERLAY_NEEDS_REFACTOR_BEFORE_PROMOTION`
     - `ARCHIVE_CANDIDATE_KEEP_RUNTIME_COPY_UNTIL_CONFIRMED_UNUSED`
   - Only `git add -f` ignored files that are pure/deterministic, have dedicated tests, and pass model review.
   - Keep DB/subprocess/write-heavy modules as runtime overlays until refactored.

6. For overlay candidate tests:
   - If testing ignored local overlays without promoting them, make tests skip-friendly when the file is absent in a clean checkout.
   - If promoting one overlay file, add dedicated tests and force-add only that file plus its tests.
   - Never let a local ignored overlay become an accidental hard dependency unless it is deliberately promoted and tested.

7. Cross-model audit:
   - Provide real code snippets, test output, readiness reports, and git status; `git diff` alone may omit ignored overlays.
   - GPT/Claude Responses API may return HTTP 200 with `output=[]`; record it as no effective text and do not count it as an audit conclusion.
   - When audit says “conditional submit only,” satisfy the condition with test output before committing.

8. Commit discipline:
   - Stage only intended files.
   - For ignored overlay promotion, use `git add -f <single-file>` only after readiness says it is safe.
   - Keep workspace reports and ledgers out of code commits unless explicitly requested.

9. Evidence and ledgers:
   - Write round evidence under `~/.hermes/workspace/进化/.../artifacts/`.
   - Update `/Users/appleoppa/.hermes/data/pgg-core/six_three_evening_core_fusion.json`.
   - Update `/Users/appleoppa/.hermes/data/EVOLUTION_MANIFEST.json`.
   - Read back both before reporting DONE.

## Commands and snippets

```bash
# Rust tests for the 3 PGG Rust surfaces
for d in rust_modules/hermes_pgg_status rust_modules/hermes_pgg_ecc rust_modules/hermes_pgg_overlay; do
  (cd "$d" && cargo fmt && cargo test --release && cargo build --release) || exit 1
done

# Python tests used during hardening
./venv/bin/python -m pytest \
  tests/test_overlay_p1_candidates.py \
  tests/test_pgg_archon_delta_gate.py \
  tests/test_rust_pgg_surfaces.py \
  tests/test_anti_hallucination_e2e.py -q

# Check ignored overlay rules
git check-ignore -v agent/apex_runtimeos_sequence.py \
  agent/pgg_archon_delta_gate.py \
  agent/pgg_archon_ultimate_evolution_ars_cycle.py \
  agent/pgg_archon_ultimate_evolution_formula.py || true
```

## Truthful wording

- “PASS_WITH_BOUNDARY” is appropriate for internal engineering verification.
- Say “internal APEX ΔE process score,” not “external AGI benchmark.”
- Say “controlled single overlay promotion,” not “all overlays fixed.”
- Say “GPT HTTP 200 but output empty; not counted,” when Responses API returns no text.
