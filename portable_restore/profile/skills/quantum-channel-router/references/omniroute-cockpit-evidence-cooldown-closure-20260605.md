# OmniRoute cockpit evidence/cooldown closure — 2026-06-05

## What was closed

- Service-side evidence package generation for every `execute_omniroute_multi_provider_task()` result.
- Provider cooldown ledger after failed participation (`~/.hermes/data/omniroute_provider_cooldown.json`).
- Cooldown-aware multi-provider execution: a provider in active cooldown is recorded as `cooldown_skipped=true` with `http_status=0` instead of being retried.
- Snapshot API fields:
  - `provider_cooldown`
  - `evidence_package`
  - `paths.cooldown`
  - `paths.evidence_dir`
- SSE watcher includes cooldown and latest evidence package file, so the WebUI refreshes when those files change.
- Static Node WebUI shim displays cooldown, evidence package, per-provider OK/ERR/COOLDOWN, evidence path, and disagreement hash hints.

## Verification pattern

```bash
cd /Users/appleoppa/.hermes/hermes-agent
python3 -m py_compile agent/pgg_archon_quantum_channel_router.py hermes_cli/web_server.py
launchctl kickstart -k gui/$(id -u)/ai.hermes.omniroute-dashboard-api
curl -sS -H 'X-Hermes-Session-Token: <LOCAL_SESSION_TOKEN_PLACEHOLDER>' \
  http://127.0.0.1:9197/api/omniroute/snapshot
```

Trigger first failure/recording:

```bash
curl -sS -X POST http://127.0.0.1:9197/api/omniroute/multicall \
  -H 'Content-Type: application/json' \
  -H 'X-Hermes-Session-Token: <LOCAL_SESSION_TOKEN_PLACEHOLDER>' \
  -d '{"task_type":"api_cooldown_evidence_probe","task":"Reply exactly: PGG_COOLDOWN_OK","providers":["deepseek","mimo","gpt55"],"timeout":45}'
```

Expected if gpt55 is unhealthy:

- DeepSeek/MiMo: `participated=true`, `http_status=200`, visible answer.
- gpt55 first run: `participated=false`, `http_status=502`.
- evidence file appears under `~/.hermes/workspace/github_absorption/9router/analysis/evidence/`.
- cooldown file appears at `~/.hermes/data/omniroute_provider_cooldown.json`.

Trigger second run:

- gpt55 should be `cooldown_skipped=true`, `http_status=0`, reason references prior 502.
- Do not call this a GPT outage; phrase precisely as “OmniRoute gpt55 provider channel/cockpit probe is in cooldown”.

## Pitfalls

- Evidence package code in the agent module is not enough: the FastAPI snapshot must import/read it and expose fields.
- SSE must watch the cooldown/evidence files; otherwise the static page looks stale despite correct backend state.
- Avoid saying “gpt55 502” without context; user may be using a current GPT session successfully. Say “OmniRoute gpt55 channel returned 502 in provider-call ledger”.
- `browser_vision` may capture screenshot even if vision analysis fails with provider auth error; verify screenshot path with `stat` before reporting.
- Cooldown skip is a bounded operational optimization, not a provider benchmark or evidence that the provider is globally unusable.
