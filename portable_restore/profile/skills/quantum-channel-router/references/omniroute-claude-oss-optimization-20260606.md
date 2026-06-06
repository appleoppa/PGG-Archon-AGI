# OmniRoute Claude + OSS optimization — 2026-06-06

## Trigger

User explicitly requested Claude + GitHub/open-source review to ensure OmniRoute route-suggest/core mirror can land safely and optimally.

## Real Claude evidence

- Provider path: ChuangAgent `/v1/responses` with `claude-opus-4-6`.
- HTTP 200, visible_chars=8358, elapsed≈36s.
- Output: `~/.hermes/workspace/github_absorption/9router/analysis/claude-omniroute-route-suggest-audit-20260606.json`.
- Claude verdict: route-suggest/mirror is `PASS_BOUNDED`; guarded route-enforce should HOLD/NO_NOT_YET because suggested=mimo vs actual=gpt mismatch remains systematic.

## OSS scout evidence

Read-only GitHub API/README scout:

- `BerriAI/litellm`
- `Portkey-AI/gateway`
- `Helicone/helicone`
- `langfuse/langfuse`
- `openlit/openlit`
- `langchain-ai/langsmith-sdk`

Output: `~/.hermes/workspace/github_absorption/9router/analysis/oss-router-observability-scout-20260606.json`.

Absorbed safe patterns: shadow/route-suggest before enforcement, feature flags, separation of observation/decision/execution, provider identity normalization, redacted bounded previews, match/mismatch dashboards.

## Implemented fixes

1. Provider identity normalization in `record_omniroute_core_mirror()`:
   - `suggested_provider_identity`
   - `actual_provider_identity`
   - `suggested_route_class`
   - `actual_route_class`
   - `suggestion_route_class_matches_actual`

2. Preview redaction/limit:
   - Env: `PGG_OMNIROUTE_MIRROR_PREVIEW_CHARS` default 120.
   - Redacts `sk-*`, `Bearer ...`, `token=`, `secret=`, `password=`, `api_key=` assignments.

3. WebUI mirror row now shows route class and preview_limit.

## Verification

- `python3 -m py_compile agent/pgg_archon_quantum_channel_router.py run_agent.py hermes_cli/web_server.py` PASS.
- Direct mirror smoke redacted secrets and normalized `custom:gpt55_5yuantoken` to route_class `gpt`.
- Real gpt-5.5 route_suggest smoke returned `PGG_CLAUDE_OSS_FIX_OK` and recorded `suggested=mimo(mimo) actual=custom:gpt55_5yuantoken(gpt) class_match=false preview_limit=80`.

## Boundary

Do not enter route-enforce yet. Next safe step is v2.4 evaluation dashboard: match rate, mismatch by actual/suggested provider, suggestion latency, error rate, and redaction status.
