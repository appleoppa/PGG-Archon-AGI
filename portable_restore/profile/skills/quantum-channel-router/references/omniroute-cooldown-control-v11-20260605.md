# OmniRoute cooldown control v1.1 — 2026-06-05

## Added controls

- Multi-provider task accepts:
  - `cooldown_sec`: per-call cooldown duration; env fallback `PGG_OMNIROUTE_PROVIDER_COOLDOWN_SEC`, default 600.
  - `force_retry`: bypass active cooldown and perform a real provider call.
- Cooldown clear API:
  - `POST /api/omniroute/cooldown/clear` with `{ "provider": "gpt55" }` clears one provider.
  - `{ "provider": "" }` clears all.
- WebUI controls:
  - `cooldown_sec` numeric input.
  - `force retry cooldown provider` checkbox.
  - `解除 gpt55 cooldown` button.
  - `清空全部 cooldown` button.

## Verification pattern

1. Clear provider cooldown:

```bash
curl -sS -X POST http://127.0.0.1:9197/api/omniroute/cooldown/clear \
  -H 'Content-Type: application/json' \
  -H 'X-Hermes-Session-Token: <LOCAL_SESSION_TOKEN_PLACEHOLDER>' \
  -d '{"provider":"gpt55"}'
```

2. Force retry unhealthy provider:

```bash
curl -sS -X POST http://127.0.0.1:9197/api/omniroute/multicall \
  -H 'Content-Type: application/json' \
  -H 'X-Hermes-Session-Token: <LOCAL_SESSION_TOKEN_PLACEHOLDER>' \
  -d '{"task_type":"api_force_retry_probe","task":"Reply exactly: PGG_FORCE_RETRY_OK","providers":["gpt55"],"timeout":45,"cooldown_sec":120,"force_retry":true}'
```

Expected if still unhealthy: actual call returns `http_status=502`, `force_retry=true`, and sets `cooldown_sec=120`.

3. Immediate non-force retry:

Expected: `cooldown_skipped=true`, `http_status=0`, remaining seconds close to configured value.

## Pitfalls

- Do not extend cooldown on a skipped call; otherwise every status refresh/task attempt can keep pushing the provider farther away. Only real failed calls should update cooldown.
- A force retry failure is real participation attempt evidence, but still failed participation (`participated=false`). Do not count it as provider success.
- Clear cooldown is an operational override, not proof that provider health recovered.
