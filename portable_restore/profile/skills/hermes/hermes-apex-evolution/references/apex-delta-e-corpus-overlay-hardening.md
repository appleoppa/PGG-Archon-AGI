# Rounded APEX ΔE Evidence Hardening: Corpus Tests + Overlay Matrix

Use after an internal APEX ΔE / β·Ω uplift reaches a high score through real Rust `.so` modules and needs stronger evidence before being reported as stable.

## Pattern

1. Keep ΔE wording bounded:
   - internal process/readiness score
   - not full AGI
   - not external benchmark
   - not legal/domain correctness proof

2. Add hardening evidence beyond `.so` count:
   - Rust unit tests per PyO3 crate
   - Python pytest against installed `.abi3.so`
   - malformed input corpus for JSON/scoring surfaces
   - ABI/hash/codesign registry
   - lightweight performance baseline clearly labeled as baseline

3. For ignored runtime overlays:
   - do not bulk commit
   - do not delete
   - do not recover historical code blindly
   - generate a promote/archive/delete decision matrix first

4. Completion evidence should include:
   - git commit id
   - exact test counts and command output
   - evaluator output JSON and score fields
   - model audit attempts and which produced effective text
   - SHA256 for evidence/report files
   - explicit boundary language

## Audit timing pitfall

If GPT/Claude/other auditors receive only source diff and not current test output, a WATCH verdict for “missing test evidence” is valid. After tests are run, record that the condition was satisfied in the completion evidence. Do not rewrite or inflate the original model score.

## Provider quirk

A Responses-compatible endpoint can return HTTP 200 with token usage but `output=[]` / empty visible text. Treat this as a real attempted call but not as an effective audit conclusion.

## Related detailed reference

See `rust-core-module-development` → `references/pyo3-corpus-overlay-hardening-pattern.md` for commands, corpus examples, and PyO3/macOS pitfalls.
