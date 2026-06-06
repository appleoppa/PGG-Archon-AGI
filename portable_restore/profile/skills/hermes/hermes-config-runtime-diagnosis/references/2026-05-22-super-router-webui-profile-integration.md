# Session: 超级路由配置 + Web UI Profile 集成 (2026-05-22)

## Context

This session covered: detecting a broken `model.provider`, adding claude-opus-4-7 + gpt5.5 to providers, building the quantum-channel-router (Rust CLI `qr`), and integrating everything with the Hermes Web UI profile system.

## Key Findings

### 1. model.provider Alignment

The other LLM config system had set `model.provider: deepseek` but the actual provider key in `providers:` was `deepseek_v4_flash`. This is the single most common breakage — always check `model.provider` matches a key in `providers:`.

### 2. Web UI Uses Profiles, Not Raw Providers

The Hermes Web UI does NOT have a model dropdown in the chat interface. Instead, the user selects a **profile**, and each profile has a fixed model assigned via its `config.yaml` (`model.default` + `model.provider`). To make a new model available, either:
- Change the default profile's model
- Create a new profile with the desired model

### 3. modelVisibility in Web UI Config

`~/.hermes-web-ui/config.json` has a `modelVisibility` section that controls which models appear in the Web UI's settings. Without entries here, even correctly configured providers won't show. Format:

```json
"custom:<provider_name>": { "mode": "include", "models": ["model-name"] }
```

After writing this file, the Web UI **node server** must be restarted (not just bridge/gateway).

### 4. Gateway Conflict with Multiple Profiles

Multiple gateway processes cannot share feishu/weixin/telegram credentials. When starting a profile gateway while the default gateway is running, it fails with "already in use". Workaround: stop the default gateway first, or change the default profile's model instead of using a separate profile.

### 5. Quantum Channel Router (`qr`)

Built in Rust as CLI tool. Installed at `~/.cargo/bin/qr`. Source at `~/.hermes/quantum-router/`.

Commands:
- `qr health` — check all provider endpoints
- `qr route "<task>"` — auto-classify (A/B/C/D) and route to best LLM
- `qr tier C` — explicitly request a tier
- `qr cache set/get/stats` — trajectory fingerprint caching

Tier system: A=MiniMax(基础), B=gpt-5.5/deepseek(推理), C=claude-opus-4-7(深度代码), D=glm-4.5(低成本)

### 6. Provider-Specific Notes

- **5yuantoken.eu.cc**: GET /v1/models works with Bearer auth (200). HEAD /v1/models returns 404. Chat completions work.
- **MiniMax (anthropic_messages)**: No /v1/models endpoint. Uses x-api-key header, not Bearer. Must set `anthropic-version: 2023-06-01`.
- **GLM**: Standard OpenAI-compatible chat_completions.
- **DeepSeek**: Standard OpenAI-compatible chat_completions. Fastest latency (~240ms).

## Files Modified

| File | Change |
|------|--------|
| `~/.hermes/config.yaml` | Fixed model.provider, added claude_opus47_5yuantoken, updated hetu_luoshu_router roles |
| `~/.hermes/.env` | Added GPT5_5_API_KEY (later removed as invalid) |
| `~/.hermes/profiles/deepseek/config.yaml` | Synced from main, changed model to gpt-5.5 |
| `~/.hermes/profiles/gpt55/config.yaml` | Created new profile with gpt-5.5 |
| `~/.hermes-web-ui/config.json` | Replaced with clean modelVisibility for all 5 providers |
| `~/.hermes/quantum-router/` | Entire Rust project created |
| `~/.cargo/bin/qr` | Compiled binary (3.7MB) |
| `~/.hermes/skills/quantum-channel-router/` | New skill created |

## Current Provider Configuration

| Provider | Model | Tier | Status |
|----------|-------|------|--------|
| gpt55_5yuantoken | gpt-5.5 | B (推理) | ✅ ok |
| deepseek_v4_flash | deepseek-v4-flash | B (推理) | ✅ ok (fastest) |
| minimax_m27_highspeed | MiniMax-M2.7-highspeed | A (基础) | ⚠️ not_supported (anthropic endpoint) |
| glm45_air | glm-4.5-air | D (低成本) | ✅ ok |
| claude_opus47_5yuantoken | claude-opus-4-7 | C (代码) | ✅ ok |
