# OmniRoute Route-Enforce Batch Canary + Portable Restore Settlement

## Trigger

Use when moving OmniRoute route-enforce beyond a single canary into bounded batch evidence, or when settling a day’s Hermes/PGG evolution into core references, manifest, and portable restore.

## Batch canary semantics

`run_route_enforce_batch_canary()` is a bounded evidence gate, not production takeover. It should:

1. Run exact/general canary samples through `execute_route_enforce_canary()`.
2. Run legal/audit/AGI denial samples and require them to remain denied.
3. Confirm rollback after every execution: config returns to `enabled=false`, `mode=observe_only`.
4. Summarize `success_count`, `deny_count`, `rollback_ok`, `results_head/tail`, and a boundary statement.

## Web API pitfall

When exposing batch or single enforce canary endpoints in `hermes_cli/web_server.py`, never let broad `except Exception` wrap `HTTPException(400)` validation failures into HTTP 500. Add:

```python
except HTTPException:
    raise
except Exception as exc:
    ...
```

This applies to normal OmniRoute endpoints, substitution canaries, fallback windows, and enforce canary/batch endpoints.

## Test gates

Targeted tests should cover both pure router logic and Web API behavior:

```bash
cd /Users/appleoppa/.hermes/hermes-agent
source venv/bin/activate
python -m py_compile agent/pgg_archon_quantum_channel_router.py hermes_cli/web_server.py
pytest -q tests/test_pgg_archon_quantum_channel_router_policy.py tests/hermes_cli/test_web_server.py -q
```

Recommended assertions:

- Batch canary sample count is clamped to the bounded window.
- Exact/general samples can PASS via monkeypatched provider execution.
- Hard-denied legal/audit/AGI cases are denied and counted.
- `rollback_ok` is true after the run.
- Web API writes a latest snapshot file and returns `ok` from `passed`.
- Validation failures remain HTTP 400.

## Rust compile settlement

If the session also touches Rust routing/eval gates, compile the relevant crates before claiming core settlement:

```bash
cd rust_modules/hermes_pgg_promptfoo_gate && /Users/appleoppa/.cargo/bin/cargo test && /Users/appleoppa/.cargo/bin/cargo build --release
cd rust_modules/hermes_pgg_omniroute && /Users/appleoppa/.cargo/bin/cargo test && /Users/appleoppa/.cargo/bin/cargo build --release
```

For PyO3 crates, also run the PyO3 import/codesign gate from the Rust skill; plain `cargo build` is not enough.

## Claude audit boundary

If the user asks for Claude participation, call the real Claude provider and save the raw response. If the provider returns `403 All available accounts exhausted` or another provider-side failure, record Claude as `BLOCKED` in manifest/reference and do not role-play or imply Claude reviewed.

## Settlement pattern

After tests/compile pass:

1. Write a concise reference under the governing class-level skill.
2. Add a pointer from SKILL.md.
3. Update `~/.hermes/data/EVOLUTION_MANIFEST.json` with status, evidence, commit, tests, Rust gates, and boundary.
4. Sync live skill/manifest changes into `portable_restore/` if the current work involves GitHub restore.
5. Run secret scan + restore verify again after sync.
