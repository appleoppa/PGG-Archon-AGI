# Portable Restore + OmniRoute Route-Enforce Batch Canary — 2026-06-06

## Trigger

Use when the user asks to deploy/restore the current local Hermes/PGG Archon evolution state to GitHub, or to move OmniRoute route-enforce from single canary toward bounded batch evidence.

## Portable restore pattern

Validated GitHub-safe restore bundle path inside repo:

```text
portable_restore/
  README.md
  bootstrap/install_macos.sh
  bootstrap/restore_profile.sh
  bootstrap/verify_runtime.sh
  config-templates/env.example
  config-templates/config.yaml.template
  docs/INCLUDE_MANIFEST.json
  docs/SECURITY.md
  profile/SOUL.md
  profile/memories/MEMORY.md
  profile/memories/USER.md
  profile/data/EVOLUTION_MANIFEST.json
  profile/skills/
```

Rules:

1. Never push `~/.hermes` wholesale.
2. Exclude `.env`, `auth.json`, `secrets`, OAuth sessions, `venv/`, `node_modules/`, `__pycache__/`, legal case materials, and large runtime workspace artifacts.
3. If repo `.gitignore` has broad `data/*`, explicitly force/include `portable_restore/profile/data/EVOLUTION_MANIFEST.json`; otherwise local rsync simulation may PASS while remote clone fails.
4. Require both local simulated restore and real remote clone restore:

```bash
git clone --branch <portable-branch> --single-branch https://github.com/appleoppa/PGG-Archon-AGI.git /tmp/pgg-archon-remote-clone
TARGET_HOME=/tmp/pgg-archon-remote-home bash portable_restore/bootstrap/restore_profile.sh
TARGET_HOME=/tmp/pgg-archon-remote-home bash portable_restore/bootstrap/verify_runtime.sh
```

Completion evidence must include `VERIFY_OK`, restored `EVOLUTION_MANIFEST.json` byte count, manifest top-level count, and remote commit SHA.

## OmniRoute route-enforce batch canary pattern

Core source surfaces:

```text
agent/pgg_archon_quantum_channel_router.py::run_route_enforce_batch_canary
hermes_cli/web_server.py::execute_omniroute_route_enforce_batch_canary_api
```

Safety semantics:

- Batch canary is bounded evidence only, not global route-enforce.
- It must use `execute_route_enforce_canary`, which rolls config back after every execution.
- Hard-denied intents remain blocked: `legal`, `audit`, `agi` / chinese legal / audit judge / AGI architecture-coding.
- Success requires exact/general samples to execute successfully, hard-deny samples to be denied, and config after run to remain `enabled=false`, `mode=observe_only`.
- `HTTPException(400)` must be re-raised in Web API handlers; broad `except Exception` must not wrap validation errors into HTTP 500.

Target tests:

```bash
cd /Users/appleoppa/.hermes/hermes-agent
source venv/bin/activate
python -m py_compile agent/pgg_archon_quantum_channel_router.py hermes_cli/web_server.py
pytest -q tests/test_pgg_archon_quantum_channel_router_policy.py tests/hermes_cli/test_web_server.py -q
```

Rust compile gates used during settlement:

```bash
cd /Users/appleoppa/.hermes/hermes-agent/rust_modules/hermes_pgg_promptfoo_gate && /Users/appleoppa/.cargo/bin/cargo test && /Users/appleoppa/.cargo/bin/cargo build --release
cd /Users/appleoppa/.hermes/hermes-agent/rust_modules/hermes_pgg_omniroute && /Users/appleoppa/.cargo/bin/cargo test && /Users/appleoppa/.cargo/bin/cargo build --release
```

## Claude audit boundary

If user requests Claude participation, call Claude provider for real and save raw response. Do **not** infer global Claude availability from one direct/probe call. A probe returning HTTP 403 `All available accounts exhausted` only proves that specific call chain failed; it must be reconciled with the official Hermes provider/CLI path and cross-session evidence. If another session or official path shows Claude OK, record the failing probe as `CLAUDE_PROBE_CHAIN_ERROR_RECORDED`, not `Claude blocked` or `Claude pool exhausted`.

## Truth boundary

This proves a portable restore skeleton and bounded OmniRoute batch canary source/test/compile gate. It does not restore secrets/OAuth sessions/case files, does not enable global route-enforce, and does not prove external AGI benchmark capability.
