---
name: hermes-config-runtime-diagnosis
description: "Diagnose and repair Hermes runtime configuration as a class of problems: LLM providers, key_env alignment, Web UI model visibility, profile/gateway drift, single-gateway hygiene, provider switching tools, secure key rotation, and post-upgrade doctor cleanup."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, config, providers, gateway, profiles, web-ui, key-env, diagnosis, runtime]
    related_skills: [hermes-agent]
---

## LLM Provider Audit Pointer

When auditing all LLM providers or context windows, use `references/llm-provider-audit-context-limits.md`: align `providers` + `custom_providers`, preserve GPT/Claude `codex_responses`, verify tiny live calls, normalize per-model `context_length`, and report compact evidence without secrets.

# Hermes Config & Runtime Diagnosis

## Overview

Use this umbrella for Hermes configuration/runtime failures where the root cause may span `~/.hermes/config.yaml`, `.env`, Web UI state, provider routing, profile directories, gateway processes, launchd services, or provider-switching tools. Treat provider connectivity, Web UI visibility, and gateway/profile drift as one operational class: they often write to the same config files and can revert each other.

This skill intentionally absorbs narrower session skills:

- Former `llm-provider-diagnosis`: provider connectivity, `key_env`, model/provider mapping, custom provider migration, Web UI visibility, secure key rotation, Claude cost guardrails, CC Switch integration.
- Former `hermes-gateway-profile-hygiene`: post-upgrade gateway/profile drift, single default gateway policy, LaunchAgent cleanup, config migration, profile metadata repair, local runtime dependencies.

Detailed session notes and checklists live in `references/`.

## When to Use

- Hermes sessions fail to start because a model/provider cannot resolve.
- User asks to check, repair, add, migrate, or audit model/provider configuration.
- API providers return 401/403/HTTP 000/SSL errors, or chat works in curl but not Hermes.
- Web UI cannot show or select a model/provider, or reports `GatewayManager not initialized`.
- Multiple profiles/gateways are running, platform credentials conflict, or `model.provider` changes keep reverting.
- Long gateway/agent sessions are burning token quota during context compression or compression triggers too late.
- After an upgrade, `hermes doctor`, `hermes gateway list`, or `hermes profile list` shows drift.
- A profile is missing `config.yaml`, `.env`, alias metadata, or has unsafe messaging credentials.
- API keys need secure rotation or inline `api_key` values need migration to `.env` + `key_env`.
- Provider-switching tools such as CC Switch / Claude Code / Codex / Gemini / Hermes / legacy Claw-family tools may have written out-of-band provider state.

Do not use this for general Hermes feature usage without a runtime/config symptom; load `hermes-agent` first for ordinary Hermes CLI/config documentation.

## Operating Principles

1. **Protect secrets.** Never print `.env` values or API keys. Inspect key names, lengths, and connectivity results only.
2. **Trust live state over assumptions.** Verify config, processes, gateway list, profile list, Web UI API, and provider endpoints before declaring success.
3. **Provider names must align.** `model.provider` must match a key under `providers:`; `custom:<provider>` references that same provider key.
4. **Prefer `key_env` over inline keys.** Inline `api_key` values in YAML are security debt; migrate them to `.env` variables.
5. **Default gateway unless explicitly directed.** For this user's architecture, messaging should normally run through the `default` profile only; department/worker profiles should not independently connect to Feishu/Lark.
6. **Stop writers before editing config.** Running gateways, Web UI bridge processes, and profile managers may rewrite config after you edit it.
7. **Archive/backup before destructive cleanup.** Move stale LaunchAgents/backups to archives and copy configs before migrations.
8. **Differentiate provider outages from local config bugs.** Test multiple providers and endpoints before editing working configuration.

## ⚠️ Key Pitfall: `.env` Not Auto-Loaded in Terminal

**Hermes `key_env` values live in `~/.hermes/.env` but are NOT automatically sourced into shell sessions or `terminal()` calls.** When you run `curl` or `python3` from the terminal tool to test provider connectivity, the expected env vars are absent — the `.env` file is only read by Hermes' internal credential system at agent init time, not by your login shell.

Symptoms:
- `echo "$MINIMAX_CN_API_KEY"` returns empty
- `curl` tests to provider endpoints return 401
- But `hermes doctor` shows ✓ (key configured)
- And `hermes auth list` shows the credential source

Fix: source the file explicitly inside your test command, or use Hermes' own credential resolution:

```bash
# Option A: source in subshell
source ~/.hermes/.env && curl ... -H "x-api-key: $MINIMAX_CN_API_KEY" ...

# Option B: load raw bytes in Python (preferred — no secrets in output)
source ~/.hermes/.env && python3 -c '
import os, json, urllib.request
key = os.environ["MINIMAX_CN_API_KEY"]
req = urllib.request.Request(...)
...
'

# Option C: Use Hermes internal credential resolution (see "Test via Hermes Credential System" below)
```

## Quick Baseline

Run targeted checks; avoid dumping secrets or huge files:

```bash
hermes --version
hermes config path
hermes config check
hermes gateway status
hermes gateway list
hermes profile list
hermes doctor
```

Inspect provider mapping without secrets:

```bash
python3 - <<'PY'
import yaml, pathlib
cfg = yaml.safe_load(pathlib.Path('/Users/appleoppa/.hermes/config.yaml').read_text())
m = cfg.get('model', {})
print(f"default={m.get('default')} provider={m.get('provider')}")
for name, p in cfg.get('providers', {}).items():
    print(f"{name}: model={p.get('model') or p.get('default_model')} url={p.get('base_url')} key_env={p.get('key_env')}")
print('custom_providers=', list((cfg.get('custom_providers') or {}).keys()))
PY
```

## Provider Diagnosis & Repair

### 1. Validate configuration alignment

Check the three-way contract:

| Location | Required value |
|---|---|
| `config.yaml` `model.provider` | Existing key in `providers:` |
| `providers.<name>.key_env` | Environment variable name, not a secret or `***` |
| `.env` | Matching `KEY_NAME=actual_key` line |

Common fix:

```yaml
model:
  default: deepseek-v4-flash
  provider: deepseek_v4_flash
providers:
  deepseek_v4_flash:
    base_url: https://api.deepseek.com
    api_mode: chat_completions
    model: deepseek-v4-flash
    key_env: DEEPSEEK_V4_FLASH_API_KEY
```

### 2. Extract keys safely when needed

Hermes may redact `.env` reads as `***`; `grep` and `source` can silently return masked values. If an actual key is required for connectivity testing, read raw bytes in Python and never print the key:

```python
from pathlib import Path
prefix = b'VAR_NAME='
data = Path('/Users/appleoppa/.hermes/.env').read_bytes()
idx = data.find(prefix)
assert idx >= 0
end = data.find(b'\n', idx + len(prefix))
key = data[idx + len(prefix): end if end >= 0 else None].decode()
print('loaded key length', len(key))
```

### Test via Hermes Credential System (instead of raw curl)

For the most reliable test, bypass shell env var issues by using Hermes' own credential resolution. This avoids `.env` sourcing problems and mimics exactly what Hermes does at runtime:

```python
from hermes_cli.auth import resolve_api_key_provider_credentials

creds = resolve_api_key_provider_credentials('minimax-cn')
# Returns: {'provider': 'minimax-cn', 'api_key': '...', 'base_url': 'https://api.minimaxi.com/anthropic', 'api_mode': None, 'source': 'MINIMAX_CN_API_KEY'}
key = creds['api_key']
url = creds['base_url'] + '/v1/messages'
# ... then make the API call with `key`
```

This is the authoritative path — it uses the same credential sources and resolution order as agent initialization. If this succeeds but `curl` fails, the issue is a missing env var in the shell, not a configuration problem.

### 3. Test endpoints and chat completions

For OpenAI-compatible providers, load the key from `.env` inside the test process and do not echo it:

```bash
python3 - <<'PY'
import os, json, urllib.request
key = os.environ['PROVIDER_KEY_ENV']
req = urllib.request.Request(
    'BASE_URL/chat/completions',
    data=json.dumps({'model':'MODEL_NAME','messages':[{'role':'user','content':'hi'}],'max_tokens':10}).encode(),
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
)
with urllib.request.urlopen(req, timeout=20) as r:
    print(r.status, r.read(200).decode(errors='ignore'))
PY
```

For `anthropic_messages` providers such as MiniMax:

```bash
curl -s https://api.minimaxi.com/anthropic/v1/messages \
  -H 'Content-Type: application/json' \
  -H "x-api-key: $MM_KEY" \
  -H 'anthropic-version: 2023-06-01' \
  -d '{"model":"MiniMax-M2.7-highspeed","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
```

For `codex_responses` / Responses-style providers, use the configured base URL and `/responses`; do not invent alternate subdomains.

### 4. Diagnose HTTP 000 / SSL failures

If curl returns HTTP 000 or `SSL_ERROR_SYSCALL`:

```bash
dig +short PROVIDER_DOMAIN @8.8.8.8
networksetup -getwebproxy Wi-Fi
curl -v --connect-timeout 10 https://PROVIDER_DOMAIN/v1/models 2>&1 | head -40
```

If DNS resolves to `198.18.x.x`, a Clash-family proxy may be using fake-IP routing. Test other providers at the same time. If only one supplier fails while DeepSeek/GLM/MiniMax work, classify as provider-specific outage/proxy rule mismatch rather than local Hermes config failure.

## Provider-Specific Notes

- **5yuantoken / chuangagent:** trust the base URL in `config.yaml`; Responses-style providers may use `https://chuangagent.eu.cc/v1/responses`. Known intermittent outage pattern: both GPT and Claude on the same supplier fail with SSL/HTTP 000 and later recover without config changes.
- **MiniMax:** `base_url=https://api.minimaxi.com/anthropic`, `api_mode=anthropic_messages`, auth header `x-api-key`, include `anthropic-version: 2023-06-01`, no normal `/v1/models` endpoint.
- **GLM/ZhipuAI:** `https://open.bigmodel.cn/api/paas/v4`, OpenAI-compatible bearer auth.
- **DeepSeek:** `https://api.deepseek.com`, OpenAI-compatible bearer auth.

## Web UI Model Visibility

Do not brute-force edit `config.yaml` just because a model is absent from the Web UI. Check layers in order:

1. Web UI profile API (`~/.hermes-web-ui/.token` supplies the bearer token).
2. `~/.hermes-web-ui/config.json` `modelVisibility`.
3. `~/.hermes-web-ui/hermes-web-ui.db` `model_context` table.
4. GatewayManager/node server initialization.
5. Finally, `~/.hermes/config.yaml` provider definitions.

Example visibility entry:

```json
{
  "modelVisibility": {
    "custom:gpt55_5yuantoken": {"mode": "include", "models": ["gpt-5.5"]}
  }
}
```

After editing `~/.hermes-web-ui/config.json`, restart the Web UI node server; restarting bridges or gateways alone does not reload model visibility. If using a Safari Web App, force-quit the web app too.

### GatewayManager not initialized

Manual `hermes gateway run` processes are not registered with the Web UI GatewayManager. Repair pattern:

```bash
# kill Web UI node server PID and all hermes gateway run processes
rm -f ~/.hermes/gateway.lock ~/.hermes/gateway.pid ~/.hermes/gateway_state.json
rm -f ~/.hermes/profiles/*/gateway.*
# wait for Web UI auto-restart; do not manually start gateways
```

## Profile & Gateway Hygiene

### Prefer Feishu WebSocket long connection for agent bridges

When configuring Feishu/Lark for Hermes-adjacent agents, do not default to webhook Request URL + tunnel. Hermes succeeds primarily because its Feishu adapter supports `connection_mode=websocket` and connects outbound to `msg-frontier.feishu.cn`; this avoids public URL, localtunnel, Challenge code, and user-facing token-field friction.

Operational rule:

1. If the target can use long connection, select **使用长连接接收事件 / WebSocket long connection** in the Feishu console.
2. Do not ask the user to keep retrying Request URL verification unless webhook mode is genuinely required.
3. Prefer the default Hermes gateway for Feishu/Lark. Do not recreate retired project-specific bridges unless the user explicitly requests a new sidecar and accepts its maintenance burden.
4. Verify by reading a real `connected to wss://msg-frontier.feishu.cn/ws/v2` log line and then sending a live Feishu message to the bot.

Retired sidecar note: NanoGPT-specific bridge/deployment references were removed. For future Rust sidecars, use `rust-sidecar-gateway-patterns` for generalized patterns only.

### Enforce single default messaging gateway

For non-default profiles that should not directly receive platform events:

```bash
hermes --profile <profile> gateway stop || true
hermes --profile <profile> gateway uninstall || true
hermes gateway start
hermes gateway list
```

Expected shape: `default` running, department/worker profiles stopped.

### Clean stale LaunchAgents safely on macOS

```bash
archive="$HOME/.hermes/archives/launchagents-gateway-backups-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$archive"
for f in "$HOME"/Library/LaunchAgents/ai.hermes.gateway*.plist.bak_*; do
  [ -e "$f" ] || continue
  mv "$f" "$archive/"
done
/bin/ls -1 ~/Library/LaunchAgents | grep '^ai\.hermes\.gateway' || true
```

### Migrate config after upgrades

```bash
cfg="$(hermes config path)"
cp "$cfg" "$cfg.bak-v$(date +%Y%m%d-%H%M%S)"
hermes config migrate
hermes config check
```

### Inventory profile files without secrets

```bash
python3 - <<'PY'
from pathlib import Path
import re
base = Path.home()/'.hermes/profiles'
for p in sorted(x for x in base.iterdir() if x.is_dir()):
    env = p/'.env'; cfg = p/'config.yaml'
    keys = []
    if env.exists():
        for line in env.read_text(errors='ignore').splitlines():
            m = re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
            if m: keys.append(m.group(1))
    risky = [k for k in keys if 'FEISHU' in k.upper() or 'LARK' in k.upper()]
    print(p.name, 'config=', cfg.exists(), 'env=', env.exists(), 'feishu_lark_keys=', risky)
PY
```

Create missing aliases with:

```bash
hermes profile alias <profile> --name <profile>
```

### Model provider reversion trap

If `model.provider` keeps reverting after gateway restart:

1. Stop all gateway processes and profile gateways.
2. Clean default/profile gateway lock files.
3. Re-edit config with the correct `model.provider` key.
4. Restart only the required gateway or let Web UI manage it.
5. Re-read config after restart to verify it did not revert.

### Context compression token-explosion guardrail

When a long Hermes/gateway task hits quota pressure, audit compression as a runtime path, not only as a model/provider problem:

1. Separate the **compression trigger threshold** from the **summarizer input cap**. The trigger decides when to compress; the input cap prevents the compression request itself from becoming quota-expensive.
2. Avoid pure percentage triggers across mixed-context models. Prefer hybrid config: `absolute_threshold_tokens: 150000` capped by `threshold_safety_percent` (for example `0.70`), while preserving `compression.threshold` as legacy/fallback.
3. Confirm the compression provider is lightweight enough that summarization does not consume expensive primary quota unnecessarily.
4. Inspect the compressor implementation for a global serialized-input cap before the summary request is made; a known-good pattern is an `80_000` character cap.
5. Ensure the serializer keeps newest turns first when truncating (`reversed(turns)` pattern) and emits an omission note for skipped older turns.
6. Confirm redaction runs before compaction so secrets do not enter summaries.
7. Check gateway pre-agent hygiene separately; it may have its own trigger logic and must honor both `compression.threshold` and hybrid absolute/safety config instead of a hardcoded value such as `0.85`.
8. Audit **tool output retention** after compression is fixed. Large `session_search`, `search_files`, `terminal`, `execute_code`, and web results can dominate the transcript before the compressor ever runs. Prefer a configurable `tool_result_budget` with small previews and per-turn caps.
9. Audit **SessionDB hidden reasoning persistence** after tool output is capped. `reasoning`, `reasoning_content`, `reasoning_details`, `codex_reasoning_items`, and `codex_message_items` can silently dominate long-term transcripts. Prefer default-off durable storage via `session_storage.persist_reasoning: false` while keeping live in-memory provider replay intact.
10. Restart/reload the gateway after code changes, then verify logs show the configured threshold and a successful compression line.
11. Re-check process count; repair attempts can leave both a manual gateway process and a launchd-managed gateway running.

See `references/context-compression-hygiene-2026-05-31.md` for the detailed repair and verification recipe, `references/hybrid-compression-threshold-2026-05-31.md` for the absolute-threshold implementation checklist, `references/tool-result-budget-token-guardrail-2026-05-31.md` for configurable tool-output budget implementation, and `references/sessiondb-reasoning-storage-guardrail-2026-05-31.md` for durable reasoning/codex storage reduction.

## Secure Key Rotation

Use the five-step pipeline in `references/secure-key-rotation.md`:

1. Vector input through a `chmod 600` temp file; do not ask the user to paste keys into chat.
2. Regex-replace the exact `key_env=` line in `.env`.
3. Verify with a minimal API request and never print the key.
4. Destroy the temp file with macOS-safe overwrite + remove.
5. Confirm session recording/sync risk paths and advise revoking any exposed old key.

## Provider Switching Tools

CC Switch and similar tools can write provider state outside Hermes. When diagnosing cross-agent provider issues:

- Use GitHub API for latest CC Switch release discovery.
- Inspect `~/.cc-switch/cc-switch.db` only while the app is stopped.
- Understand app-specific JSON shapes for Hermes/OpenAI, Claude/Anthropic, Codex, and legacy Claw-family tools.
- Ensure only one `is_current=1` row per `app_type`.
- Restart the target CLI after database changes.

## Claude Cost Guardrails

The user has a standing cost-control preference: Claude/Anthropic must not be an automatic fallback or route target. Audit all layers when repairing routing:

1. `provider_routing.ignore` includes Claude provider/model names.
2. `fallback_providers` contains no Claude entries.
3. `hetu_luoshu_router.mirrors` contains no Claude entries.
4. `route_chain_gate.trigger_phrases` does not include Claude-triggering phrases.
5. Hardcoded router scripts do not route C-tier or cron jobs to Claude.

See `references/claude-cost-guardrail-audit-20260529.md` for the multi-file checklist.

## Local Runtime Dependencies

If `hermes doctor` says browser/computer-use tools are hidden:

```bash
cd ~/.hermes/hermes-agent && npx playwright install chromium
hermes computer-use install
hermes computer-use status
```

On macOS, actual screen control may still require manual Privacy & Security grants for Accessibility and Screen Recording.

## Support References

- `references/secure-key-rotation.md` — secure temp-input → `.env` update → verify → destroy pipeline.
- `references/2026-05-22-super-router-webui-profile-integration.md` — super-router / Web UI profile integration walkthrough.
- `references/claude-cost-guardrail-audit-20260529.md` — Claude cost guardrail audit and file checklist.
- `references/provider-config-consistency-after-audit.md` — post-audit provider config consistency repairs.
- `references/nanogpt-feishu-websocket-bridge-202605.md` — Hermes-style WebSocket long-connection pattern for NanoGPT/other agent Feishu bridges.
- `references/context-compression-hygiene-2026-05-31.md` — compression token-explosion guardrails, gateway threshold drift check, and runtime verification recipe.
- `references/hybrid-compression-threshold-2026-05-31.md` — hybrid `absolute_threshold_tokens` + safety-cap implementation checklist for mixed-context models.
- `references/tool-result-budget-token-guardrail-2026-05-31.md` — configurable tool-result budget, previews, and per-turn caps to prevent large tool outputs from dominating context.
- `references/sessiondb-reasoning-storage-guardrail-2026-05-31.md` — default-off durable storage for hidden reasoning/codex blobs while preserving live provider replay.
- `references/provider-dotenv-not-in-terminal-2026-05-31.md` — `.env` not auto-loaded in terminal sessions, MiniMax China endpoint verification details, and Hermes internal credential resolution technique.

## Verification Checklist

- [ ] `hermes config check` passes.
- [ ] `model.provider` exists under `providers:`.
- [ ] Relevant providers pass endpoint/chat tests or are clearly classified as provider-side/network failures.
- [ ] Every `providers.<name>.key_env` has a matching `.env` key name.
- [ ] No inline `api_key` remains unless explicitly justified and reported.
- [ ] Web UI visibility/config/db layers are consistent when the symptom is UI selection.
- [ ] Web UI node server restarted after visibility changes.
- [ ] Gateway list shows only intended profiles running.
- [ ] Profile configs and aliases are consistent.
- [ ] LaunchAgent backups were archived, not deleted.
- [ ] Lock files were cleaned only after processes were stopped.
- [ ] `hermes profile list`, `hermes gateway list`, and relevant `hermes doctor` sections verify the final state.
- [ ] Remaining warnings are labeled as fixed, requires user/API setup, or intentionally not fixed.
