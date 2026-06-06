---
name: hermes-agent
description: Hermes Agent配置、排障、使用手册
version: 2.2.0
author: Hermes Agent + Teknium
license: MIT
metadata:
  hermes:
    tags: [hermes, setup, configuration, cron, gateway, memory, skills]
    related_skills: [hermes-agent-skill-authoring]
---

# Hermes Agent — Compact Operator Skill

## Use When

- The user asks about Hermes Agent setup, config, models, providers, tools, skills, memory, cron, gateway, plugins, profiles, or CLI usage.
- The user asks why Hermes behaves a certain way, including context growth, memory, skills, or cron behavior.
- Do not load huge references unless the user asks for exact command detail or the compact checklist is insufficient.

## Token Discipline

- First answer from this compact skill and live config/state checks.
- Do not read full docs or long config files unless the question needs exact syntax.
- Prefer targeted `hermes config get/path`, key-field scripts, or grep-style search over reading whole files.
- If a topic needs detail, open only the matching reference file or exact section.

## Core Commands

| Need | Command |
|---|---|
| Config path | `hermes config path` |
| Edit config | `hermes config edit` |
| Set config | `hermes config set KEY VALUE` |
| Health check | `hermes doctor` |
| Model/provider | `hermes model` |
| Tools | `hermes tools` / `hermes tools list` |
| Skills | `hermes skills list/search/install` |
| Cron | `hermes cron list/status/run/edit/pause/resume/remove` |
| Gateway | `hermes gateway status/start/stop/restart` |
| Sessions | `hermes sessions list/browse/export` |
| Memory | `hermes memory status/setup/off` |

## Key Paths

| Item | Path |
|---|---|
| Main config | `~/.hermes/config.yaml` |
| Secrets | `~/.hermes/.env` |
| User skills | `~/.hermes/skills/` |
| Sessions | `~/.hermes/sessions/` |
| Logs | `~/.hermes/logs/` |
| Cron jobs | `~/.hermes/cron/jobs.json` |
| Source | `~/.hermes/hermes-agent/` |

## Common Fixes

- Config/tools/skills not taking effect: start a new session or restart gateway.
- `hermes-web-ui restart` on v0.6.7 exits with “hermes-web-ui is not running” if the UI server is currently stopped; use `hermes-web-ui start` in that state, then verify with `hermes-web-ui status` and `curl http://127.0.0.1:8648/health`.
- Custom provider 503: check configured provider/model, key presence without printing secret, `/v1/models`, then tiny chat request. 503 with models available usually means account/model availability, not Hermes config failure.
- Provider 401 / authentication failure: identify the failing provider (check web UI server.log for `available-models 401`, gateway logs for `empty_response`), test the API key directly with curl, verify key_env alignment between config.yaml and .env, and check for parallel built-in+custom provider duplication for the same service. See `references/provider-auth-diagnosis.md`.
- Context compression hangs/stalls: first check `compression.*`, `auxiliary.compression.*`, `context.engine`, and logs for `Failed to generate context summary`, `Request timed out`, `Unknown Model`, provider 5xx/Cloudflare HTML, and `Session split detected`. Compression calls an auxiliary LLM; if `auxiliary.compression` is `auto`, it may reuse an unstable/custom main model. Prefer configuring a dedicated fast/stable compression model after verifying exact provider syntax. See `references/context-compression-hangs.md`.
- “Hermes is slow/cardy/stuck”: distinguish UI/network/model-provider latency from token/context bloat, compression stalls, and live process load. Check current model/provider, context size/compression settings/logs, gateway/process state, and whether a huge skill/memory/config was loaded before guessing.
- Doctor reports missing optional tool API keys even after `hermes tools disable`: first verify `platform_toolsets` and `agent.disabled_toolsets`; Hermes versions before the local May-2026 fix may have doctor listing all registered toolsets rather than the configured enabled set. Do not add fake API keys to silence warnings.
- GitHub Copilot token boundary: keep Copilot provider auth on `COPILOT_GITHUB_TOKEN`/supported OAuth-App tokens, not ordinary `GH_TOKEN`/`GITHUB_TOKEN`; see `references/github-copilot-token-boundary.md` for repair + verification patterns.
- Context budget hygiene: before reading a large skill/config/rule file, prefer listing key fields, searching for a section, or reading a compact umbrella. Full documents belong in references and should be opened only when exact syntax or deep troubleshooting is required.
- Context bloat / system prompt too large (138K+): first check `~/.hermes/memories/MEMORY.md` and `USER.md` for duplication with AGENTS.md. These files are injected into every turn and often contain the same rules already in AGENTS.md. See `references/context-bloat-diagnosis.md`.
- Cron: verify both scheduler state and side-effect evidence. A successful tick is not proof the intended work completed.
- Cron `no_agent` script failures: always check stderr for `ModuleNotFoundError`. If the error references `hermes_cli.<module>` but the module actually lives under `agent/`, the cron `script` field is referencing the wrong import path. See `references/cron-script-module-path-and-macos-ssl.md`.
- Cron batch jobs: when creating a fresh finite batch (e.g. 10 runs), include an explicit unique batch/run_group in the prompt and state that user-facing numbering starts at 1/N for this batch. If the job writes to an existing database, do not infer the displayed round number from old max(cycle_no) unless the user explicitly wants continuation.
- Cron delivery: if the user wants to see each run result, set `deliver='origin'`; use `deliver='local'` only when they want silent/local records.
- Gateway concurrency / “same user multiple chats”: concurrency is controlled by `session_key`, not desktop window or username. Same session key is serialized through `_running_agents`; distinct session keys can run concurrently. Feishu/Lark visible conversations may still share `chat_id/thread_id`, and Feishu has per-chat locks. See `references/gateway-session-concurrency.md`.
- Secrets: store only in `.env` or key-env references; never print or save keys in memory/reports.

## References

Long reference material is intentionally not in this main skill. Use targeted references only when needed:

- `references/custom-provider-header-block.md`
- `references/2026-05-19-custom-provider-availability.md`
- `references/multi-model-routing-secrets.md`
- `references/github-evolution-loop-bootstrap.md`
- `references/context-bloat-diagnosis.md`
- `references/github-factory-multimodel-verification.md`
- `references/cron-script-module-path-and-macos-ssl.md` — cron 脚本断裂（引用不存在的 `hermes_cli.apex_runtimeos`）与 macOS GitHub SSL_ERROR_SYSCALL 查证修复记录
- `references/context-bloat-diagnosis.md`
- `references/provider-auth-diagnosis.md`
- Full previous verbose copy is archived under workspace `存档/token上下文瘦身前备份/`.

## Verification Checklist

- [ ] Loaded this compact skill before Hermes-specific changes.
- [ ] Used targeted checks instead of full-file reads.
- [ ] Did not expose secrets.
- [ ] Reported exact status and evidence level.
- [ ] If config changed, told user whether restart/new session is required.

## APEX Sequence Note

For evolution/learning/configuration tasks that need APEX ordering, use `apex-sequence-logic`: 21354审错优先, 12534融合固化, 14325规划反证. Keep this as a short pointer; do not duplicate the full rule here.
