# PyO3 verifier interpreter pitfall — 2026-06-06

## Trigger

Use when a standalone verifier script imports a PyO3 extension installed in the Hermes venv, especially modules under:

```text
/Users/appleoppa/.hermes/hermes-agent/venv/lib/python3.11/site-packages/*.so
```

## Problem observed

A verifier script used system Python (`#!/usr/bin/env python3`) and manually injected the Hermes venv `site-packages` into `sys.path` to import `hermes_pgg_pilotdeck.abi3.so`. On macOS this crashed with:

```text
Fatal Python error: PyInterpreterState_Get: the function must be called with the GIL held
Abort trap: 6
```

This was not a Rust compile failure. It was a verifier interpreter / ABI mismatch.

## Correct fix

Use the same venv Python that the PyO3 module was installed and smoke-tested under:

```python
#!/Users/appleoppa/.hermes/hermes-agent/venv/bin/python
import hermes_pgg_pilotdeck
```

Do not use system Python plus manual `sys.path` injection for venv-installed `.so` files.

## Verification gate

After fixing the shebang, rerun:

```bash
/Users/appleoppa/.hermes/scripts/verify_pilotdeck_rust_absorption.py
/Users/appleoppa/.hermes/hermes-agent/venv/bin/python - <<'PY'
import json, hermes_pgg_pilotdeck as p
out=json.loads(p.evaluate_default_json())
print(p.version())
print(out['pass'], out['watch'], out['blocked'], out['total'])
PY
```

Expected result for the PilotDeck absorption module:

```text
PASS=14 / WATCH=0 / BLOCKED=1 / TOTAL=15
```

## Boundary language

Classify the initial crash as `verifier-interpreter bug`, not as Rust module failure, once `cargo test`, `cargo build --release`, `build_and_install.sh`, and venv Python import smoke all pass.
