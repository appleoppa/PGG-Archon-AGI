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

# Hermes Config & Runtime Diagnosis — Compact

## Trigger

Use for Hermes config, providers, model visibility, key_env alignment, gateway/profile drift, single-gateway hygiene, secure key rotation, and doctor/runtime cleanup.

## Principles

- Never print secrets. Check key presence and variable names only.
- Terminal shells do not automatically load `.env`; explicitly source in a subshell or use Hermes credential resolution.
- Distinguish config syntax, credential resolution, provider availability, model authorization, gateway runtime, and Web UI cache.
- For Feishu/Lark, only default profile should connect unless user explicitly authorizes otherwise.

## Quick baseline

1. Identify active profile and config path.
2. Inspect only relevant config keys, not full secrets files.
3. Verify provider name, model id, API mode, base URL, and key_env alignment.
4. Test provider with the correct endpoint format for that provider.
5. Restart gateway/Web UI if runtime cached old config.
6. Read logs for the first real failure, not the last cascading error.

## Context compression / compaction instability

For repeated context compression failures, hangs, or premature `Session hygiene: auto-compressing`, do not stop at token thresholds. Also inspect `compression.hygiene_hard_message_limit` and `auxiliary.compression.timeout`: message-count hygiene can compress short-message sessions before token limits, and auxiliary summary calls can time out under gateway/provider load. Use the runbook at `references/context-compression-timeout-and-hygiene-2026-06-02.md`. For the default profile's verified GPT-5.5 compression-provider stabilization (`hygiene_hard_message_limit=400`, `auxiliary.compression=gpt-5.5`, timeout `180`), see `references/gpt55-compression-provider-2026-06-02.md`.

## CLI namespace pitfall: gateway vs Web UI

- `hermes gateway restart/status/start/stop` manages the Hermes messaging gateway / LaunchAgent.
- `hermes-web-ui restart/status/start/stop` manages the local Web UI server only.
- Do not use `hermes-web-ui gateway restart`: current Web UI CLI does not have a `gateway` subcommand; `gateway` may be treated as a positional server command/port fallback and can look like a hang or foreground server startup.
- When a user reports this exact pattern, verify with `hermes gateway status` and `hermes-web-ui status`, then run the correct command for the intended service.

## Cron no-agent pitfalls

For `no_agent=true` cron jobs, inspect both scheduler config and script runtime. The cron `script` field is a script path, not shell command parsing: do not store arguments in it (`script.sh arg` becomes a literal missing filename). Use wrapper scripts under `~/.hermes/scripts/` for parameterized modes. Also verify `deliver=origin` has a non-null origin; otherwise set `deliver=local` or an explicit channel. Long scripts can be marked error even after producing partial artifacts when the runner timeout is hit; bound default workload and use env-var overrides for manual deep runs. Detailed checklist: `references/cron-no-agent-script-args-timeout-2026-06-02.md`.

## Provider pitfalls

- **Web UI catalog regeneration trap**: `~/.hermes-web-ui/config.json.modelVisibility` alone may not remove built-in/stale models from the bottom selector. Current Web UI can regenerate `~/.hermes-web-ui/cache/provider-model-catalog.json` from built-in provider list (`PI` in `dist/server/index.js`), `~/.hermes/auth.json` credential pools, and all profile `custom_providers`. For “UI 去重/删内置”, verify the cache after restart. If built-ins such as `deepseek/copilot/zai/minimax` or stale custom providers reappear, back up `dist/server/index.js`, apply a minimal whitelist around the catalog write path only, run `node -c`, delete the cache, restart Web UI, then verify cache `bad_providers=[]`. Do not change Hermes core provider capability unless the user explicitly asks for global purge.
- **Built-in vs custom provider boundary**: when deleting Web UI built-in providers such as `minimax`, `minimax-cn`, or `copilot`, preserve user-defined custom providers whose names contain the same vendor string, e.g. `custom:minimax_m3`, unless the user explicitly asks to delete them. Do exact-id filtering (`minimax`, `minimax-cn`, `copilot`) and/or built-in endpoint filtering (`api.githubcopilot.com`, built-in `api.minimax.*`) rather than broad substring filters like `"minimax" in provider`. Verify `modelVisibility`, `hiddenProviders`, `disabledProviders`, cache keys, and runtime bundle filters separately. See `references/chuangagent-responses-webui-provider-scope-20260605.md`.
- For MiniMax M3, configure `custom:minimax_m3` as OpenAI-compatible `chat_completions` with `base_url: https://api.minimax.chat/v1`, `model/default_model: MiniMax-M3`, and `key_env: MINIMAX_API_KEY`. Add it to both `providers` and `custom_providers`, then verify `/v1/models`, direct `/v1/chat/completions`, and Hermes CLI (`hermes -z 'Return exactly: OK' --provider custom:minimax_m3 -m MiniMax-M3 --cli`). See `references/minimax-m3-provider-setup-2026-06-03.md`.
- For MiMo v2.5 Pro with the user's current audit key, prefer OpenAI-compatible `chat_completions` at `base_url: https://token-plan-cn.xiaomimimo.com/v1`, `model/default_model: mimo-v2.5-pro`, `key_env: MIMO_V25_PRO_API_KEY`. The generic official endpoint `https://api.xiaomimimo.com/v1` can return HTTP 401 with this key even when the token-plan endpoint works; verify direct `/chat/completions` before changing key assumptions.
- For Agnes, configure OpenAI-compatible `chat_completions` at `base_url: https://apihub.agnes-ai.com/v1`, `model/default_model: agnes-2.0-flash`, `key_env: AGNES_AI_API_KEY`; verify direct `/chat/completions` with a compact JSON response.
- GPT/Claude local custom providers must use Responses API format when configured that way.
- **GPT55/Claude ChuangAgent `codex_responses` quirk**: this proxy may ignore `max_output_tokens` on `/responses` (response echoes `max_output_tokens: null`) and GPT may spend the whole tiny default budget on reasoning, returning `output=[]` even with HTTP 200. For ad-hoc provider tests/calls, send `max_tokens` or `max_completion_tokens` (≥500 for real tasks) instead of relying only on `max_output_tokens`, and extract text from `output[].content[].text` after any `reasoning` item. Do not mark GPT as failed until this variant is tested.
- **`gpt55_5yuantoken` / `claude_opus46_5yuantoken` ChuangAgent rule**: for this user's Hermes config, GPT/Claude custom providers must remain `api_mode: codex_responses`. **Important base_url distinction:**
  - GPT: `base_url: https://chuangagent.eu.cc/v1`
  - Claude: `base_url: https://chuangagent.eu.cc` (root only — NO `/v1` suffix)
  - Fallback (both): `https://5yuantoken.org/v1` (currently shares upstream, also 502 when ChuangAgent is down)
  Do not set both to the same base_url. Do not downgrade to `chat_completions` even if direct `/v1/responses` calls return transient 502. Validate with the real Hermes binary (`/Users/appleoppa/.local/bin/hermes -z 'Return exactly: OK' --provider custom:gpt55_5yuantoken --model gpt-5.5` and the analogous Claude command), because Hermes' `codex_responses` adapter may succeed where a naive curl/urllib probe returns 502 upstream errors. When ChuangAgent is overloaded, direct HTTP returns 502 consistently while the Hermes CLI adapter still gets through (observed 2026-06-04/05/06). See `~/.hermes/scripts/gpt55_retry_adapter.sh` for a retry wrapper that routes through Hermes CLI by default. For Claude specifically, a hand-written urllib `/v1/responses` probe can return `403 All available accounts exhausted` while the formal Hermes `AIAgent(... provider='custom:claude_opus46_5yuantoken', model='claude-opus-4-6', api_mode='codex_responses', base_url='https://chuangagent.eu.cc', api_key=$CLAUDE_OPUS47_5YUANTOKEN_API_KEY ...)` path succeeds and returns visible output; treat naive direct failures as diagnostics, not final provider health, until the formal adapter probe fails too. Claude may use `CLAUDE_OPUS47_5YUANTOKEN_API_KEY` for the `claude_opus46_5yuantoken` provider if direct/Hermes smoke verifies it. **Web UI caveat**: fixing `~/.hermes/config.yaml` is not sufficient; the Web UI `/api/hermes/available-models` path must propagate custom provider `api_mode` and `key_env` into model groups, and `custom:claude_opus46_5yuantoken` must be present in the custom-provider catalog allowlist. If those fields are dropped, the UI can display or pass default `chat_completions` even when CLI uses `codex_responses`, causing high-cost GPT/Claude routing. Verify config readback + Web UI bundle markers + real CLI smoke + user/UI-side selection after restart. Full detail in `references/chuangagent-responses-webui-provider-scope-20260605.md`.
- DeepSeek commonly uses chat-completions.
- 401 means credential/auth; 404/400 often means endpoint/model/API-mode mismatch; 503 may be provider availability/account/model entitlement.
- **Reasoning models (DeepSeek-V4-Flash, MiMo-v2.5-Pro, etc.)**: `max_tokens` covers BOTH reasoning and output tokens combined. With too small a budget, all output may go to `reasoning_content` (non-standard field in `choices[0].message`), leaving `content=""`; for real audits use a larger budget such as DeepSeek/MiMo `max_tokens>=4096` and record both visible `content` length and `reasoning_content` length. `reasoning_content` alone is diagnostic evidence, but promotion/LLM quorum should count only visible final `content` unless the gate explicitly allows otherwise.

### Concrete fix path for the `content=""` symptom

When a reasoning-model call returns HTTP 200 with `content=""` and a non-empty `reasoning_content`:

1. Bump `max_tokens` in the calling site. For DeepSeek-V4-Flash and MiMo-v2.5-Pro use `max_tokens=4096` or higher so the reasoning budget does not eat the final-answer budget. For GPT/Claude `responses` mode prefer `max_tokens`/`max_completion_tokens` over `max_output_tokens` (the chuangagent proxy may echo `max_output_tokens: null` and waste the budget on reasoning).
2. Extract `reasoning_content` separately. Do not fold it into the "visible output" used by downstream gates; the `pgg_archon_llm_quorum_gate` `_counts_as_pass` rule is `status == "ok_visible" and visible_chars > 0 and verdict == "PASS"`. Reasoning-only output is a real failure by that rule, but it is a recoverable failure (raise `max_tokens`, retry) not a structural one.
3. Update `agent/pgg_archon_provider_benchmark.py` `default_pgg_model_providers()` so the reasoning model rows carry the new `max_tokens`. Do not bury the bump in an ad-hoc script.
4. Add a regression test that posts a small prompt with `max_tokens=10` and asserts the script's `ProviderCallOutcome.ok is False`, then re-runs with the bumped `max_tokens` and asserts `ok is True` and the visible text contains the requested JSON. The test is what stops the next session from quietly reverting the fix.

## Session DB location

The canonical message transcript database is `~/.hermes/state.db` (NOT `~/.hermes/data/session.db`). The `data/` directory may contain stale 0-byte copies from past gateway crashes. When diagnosing DB issues:
1. Check `~/.hermes/state.db` first — it's typically hundreds of MB with thousands of messages.
2. `~/.hermes/data/session.db` and `~/.hermes/data/state.db` are often empty stubs; deleting them is safe.
3. Verify integrity with `sqlite3 ~/.hermes/state.db "PRAGMA integrity_check;"` — should return `ok`.
4. If truly corrupt, delete and restart gateway; the system will recreate it.

## Session routing ledger cleanup

For requests like “清理过期 sessions”, distinguish transcript DB cleanup from active-profile session routing metadata. The JSON ledger `~/.hermes/sessions/sessions.json` may contain per-channel session records with `expiry_finalized`; expired routing records can be removed by keeping only records where `expiry_finalized is not true`. Always inspect counts first, create a reversible backup under `~/.hermes/workspace/治理/session_cleanup_<date>/`, rewrite atomically, and read back `expired_count == 0` before reporting completion. Detailed runbook: `references/session-ledger-expired-cleanup-2026-06-03.md`.

## Hermes Desktop session-history retention cleanup

When Desktop/TUI shows hundreds or thousands of sessions, do not assume it reads `~/.hermes/sessions/sessions.json`. Desktop session history normally comes from `~/.hermes/state.db`; the displayed count may match `select count(*) from sessions where message_count>0`. For retention requests such as “保留最近4天，前面的清除”, back up `state.db` with SQLite `.backup`, preflight cutoff counts, delete old `messages` and `sessions` in a transaction, null `parent_session_id` references to deleted sessions to avoid FK failures, rebuild/optimize `messages_fts` and `messages_fts_trigram`, then `VACUUM` to reclaim space. Verify `sessions_before_cutoff=0`, `orphan_messages=0`, `broken_parent_refs=0`, and report the Desktop-visible `message_count>0` count. Detailed runbook: `references/desktop-state-session-retention-cleanup-2026-06-03.md`.

## Noise/probe session hiding

When the user says sessions appear that they did not intentionally create — especially `Return exactly: OK`, `只回复：M3_OK`, provider smoke tests, or empty internal sessions — prefer archiving over deletion. Back up `~/.hermes/state.db`, identify candidates by joining each session to its first user message, and set `sessions.archived=1` only for stale `message_count=0` rows or tiny no-tool exact-reply probes. Do not archive larger/tool-using troubleshooting sessions just because the first prompt contains `Return exactly`. For automation, use a silent no-agent cron script with the script path relative to `~/.hermes/scripts/`. Detailed runbook: `references/noise-session-archive-filter-2026-06-03.md`.

## Cron dependency audit pattern

When multiple cron jobs fail after code cleanup/rename operations:
1. Read `~/.hermes/cron/jobs.json` to identify all jobs with `last_status=error`.
2. Extract the `script` field from each broken job.
3. For `no_agent=true` jobs, verify the script exists at `~/.hermes/scripts/<name>`.
4. Read each script and check that all imported Python modules and called scripts exist.
5. Disable jobs whose dependencies are permanently deleted (set `enabled=false`, add `paused_reason`).
6. For jobs with transient failures (network timeout, execution timeout), leave enabled — they self-heal.
7. After fixes, restart gateway to pick up cron config changes.

## Adjacent local agent runtime / PilotDeck provider routing

When debugging a physically separate local agent such as PilotDeck, do not treat Hermes provider health as proof that the adjacent runtime is fixed. Inspect that agent's own config, router events, model capability declarations, startup env loading, and provider API shape. In particular, a token-saver/router tier may select a cheap no-tools model (e.g. `supportsToolUse: false`) even when the agent request includes tools, producing `Model ... does not support tools`. Fix the route, not just the bridge: keep no-tools models out of agent/tool-use tiers, store direct credentials in that agent's hidden env file with `0600`, source it from that agent's startup scripts, and smoke-test both direct API tool calls and the agent runtime's own `streamModel()`/equivalent. If GPT/Claude upstream requires Responses API but the adjacent runtime only implements `/chat/completions`, do not pretend YAML-only direct config is enough; use a compatible direct provider or implement a Responses adapter. Detailed runbook: `references/pilotdeck-direct-llm-tooluse-routing-2026-06-03.md`.

Post-fix verification must distinguish “config fixed” from “runtime currently usable.” If the user asks whether it is fixed now, re-check live processes/ports and health endpoints before answering. For PilotDeck-class runtimes, `/health` may be the valid gateway health endpoint while old ad-hoc endpoints such as `/api/config/validate` can 404; do not convert that 404 into a false failure. Verify UI/server/gateway ports separately, and if a long-lived dev launcher is needed, start it as a tracked background process and then confirm `health` plus UI HTTP 200 before saying “可用”.

When the user asks to “重新打通 PilotDeck 通道” and continue synchronized evolution, follow the layer-by-layer reconnect and evidence-chain verification pattern: start existing wrappers for bridge/gateway/UI server/Vite client, fix native Node module ABI drift with `npm rebuild better-sqlite3` if needed, verify live config path and POST config validation, run a real `createRemoteGateway().submitTurn()` smoke that reaches `turn_completed` with `errors=[]`, then run the existing evidence-chain wrapper and update Hermes `EVOLUTION_MANIFEST.json`. Full runbook: `references/pilotdeck-channel-reconnect-and-evidence-chain-2026-06-03.md`.

For subsequent “继续共同补短/共同进化” after reconnection, do not leave `submitTurn()` as an ad-hoc smoke only. Promote it into the formal PilotDeck evidence-chain invariant: additive wrapper under `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/reports/`, JSON/MD reports, JSONL append, manifest readback. Verified pattern from 2026-06-05: round10 requires `RemoteGateway.submitTurn -> turn_completed -> SYNC_CHANNEL_OK -> errors=[]`; round11 extends this with client-observed `duration_ms`, `first_text_ms`, event counts, and a cross-round trend index. Round12 adds router-decision readback with strict truth boundaries: distinguish `RouterRuntime.ts` source `pilotdeck_router_decision` emit evidence and live YAML router config from actual `RemoteGateway` stream exposure. If `runtime_stream_exposed=false`, record `PARTIAL_RUNTIME_TRACE_UNAVAILABLE_SOURCE_AND_CONFIG_READBACK_PASS` and do not claim full causal route. Round13 closes that gap by bridging `RouterEventBus.emit(pilotdeck_router_decision)` to the existing `agent_status` GatewayEvent via `InProcessGateway.emitForSession`, while still appending router/events.jsonl. Redact `requestPatch` before stream exposure and assert `redaction_guard_in_code=true`; do not add a new GatewayEvent type unless needed. Parse PilotDeck YAML with PyYAML/structured parser, not hand-written indentation scanning, or `router.scenarios` may be silently missed. Keep changes additive: no provider routing mutation, no config mutation, no external-code execution unless explicitly authorized. Next hardening target after Round13 is a regression test ensuring `runtime_stream_exposed=true` and `requestPatch/messages/systemPrompt` stay redacted. For the concrete 2026-06-05 bounded submitTurn smoke script shape, evidence-chain readback fields, SHA-256/JSONL checks, and manifest key pattern, see `references/pilotdeck-reconnect-submitturn-smoke-and-manifest-20260605.md`.

Additional PilotDeck pitfalls from the 2026-06-03 repair:

- Opening `PilotDeck.app` may read default `~/.pilotdeck/pilotdeck.yaml` even when the hidden deployment under `~/.pilotdeck-agi/home/.pilotdeck` is configured. If the UI shows onboarding / configure-LLM after a successful hidden-directory fix, compare `/api/config.path` and `/api/projects.fullPath`; a placeholder `_placeholder` config at `~/.pilotdeck` is a different entrypoint, not proof the configured hidden home failed. See `references/pilotdeck-entrypoint-symlink-onboarding-and-model-pool-2026-06-03.md`.
- Do not remove useful no-tools providers just to fix an agent tools-routing error. Preserve chat-only/auditor models with `supportsToolUse: false` unless the user explicitly asks to delete them; keep them out of agent/tool-use router tiers and fallback instead.
- Before making a model the PilotDeck main LLM, run a direct tool-call smoke test against that provider and only then set `supportsToolUse: true` or route tool-bearing agent requests to it.

## Scoped active-config provider removal

When the user asks to delete a provider config without saying “本机所有/全局清理”, treat it as an active-profile config edit, not a whole-machine purge:

1. Load `hermes-agent` first, confirm active profile scope, and edit only the active profile config unless the user explicitly expands scope.
2. Back up the config under `~/.hermes/workspace/config-backups/` before changing it; do not print secret values in the report.
3. Remove whole structured provider entries from both forms if present: `providers.<name>` mapping and `custom_providers[]` list item.
4. Remove fallback references that point to the provider, including top-level `fallback_providers` and nested chains such as `auxiliary.compression.fallback_chain`.
5. Treat obvious spelling variants in the user's request as aliases for lookup, e.g. “agens” likely means `agnes`/`agnes_ai`, but report the exact keys removed.
6. Verify with YAML parse plus targeted grep/readback over the active config: provider keys, custom provider names, fallback lists, and default model provider.
7. State that a Hermes session/gateway restart may be required for cached runtime config to fully update.

## Provider purge workflow

When the user asks to remove all local configuration for a provider, treat it as a scoped purge across active Hermes config, not as a casual line deletion:

1. Classify hits into active config, profiles, per-agent catalogs, runtime env, active operating rules, and excluded docs/tests/logs/external repos.
2. Remove whole structured YAML/JSON provider nodes, auth maps, model catalog entries, fallback entries, credential-pool entries, and `.env` variables without printing secrets.
3. Include named profiles and department agent configs when the request says “本机所有”.
4. Unset macOS launchd env vars for the provider if present, but distinguish persistent config cleanup from the current shell’s inherited environment.
5. Do not rewrite external cloned repositories or bundled docs/tests just because they contain the provider name.
6. Avoid retaining secret-bearing backups after an “all local config” purge; use a redacted manifest-only backup if an audit trail is needed.
7. Validate JSON/YAML parsing and verify zero hits inside the active configuration scope.

Detailed checklist: `references/provider-purge-runbook.md`.

## Post-install / mixed-runtime repair pattern

When a user has an existing local Hermes multi-profile deployment and installs or updates another Hermes Agent, do not assume either a clean install or a completed migration. Use the runbook `references/post-install-migration-runtime-repair-20260603.md`.

Key lessons:
- Back up config, `.env`, cron, LaunchAgents, status/doctor output, and repo git status before edits.
- Verify active CLI/config/profile/runtime paths separately; a new CLI may still read the old `~/.hermes`.
- Fix reversible runtime defects first: shell-quote `.env` values with spaces, restore CLI symlinks only when targets exist, and install compiled extension modules into the active venv with import/API smoke tests.
- Refresh cron `last_status` through `hermes cron run <id>` plus `hermes cron tick`; direct script success is useful but does not update scheduler state.
- Pause and clearly rename old jobs that depend on removed/replaced modules rather than restoring obsolete Python overlays.
- For untracked PGG/APEX overlays, create a manifest and reference scan first; soft-archive only after no-reference verification, then observe before hard deletion.
- If the user requests cross-verification, call the secondary model for real and record provider/model/endpoint/status plus visible output evidence.

### Overlay archive + update preflight variant

For the common post-install state where untracked local PGG/APEX overlays make `git status` noisy and the user wants repair before update, use `references/post-install-overlay-archive-update-preflight-20260603.md`. The class pattern is: deterministic wrapper PATH repair for non-interactive shells, hash-manifest overlay classification, copy-only archive with source left in place, exact-path `.git/info/exclude` to clean local git status, then `git fetch` + incoming commit diff audit before any `hermes update`.

## Multi-model provider health check

When testing all configured providers (e.g., after config changes, network issues, or `hermes update`), use a single Python script that reads API keys from `~/.hermes/.env` and calls each provider's `/chat/completions` endpoint directly via urllib. Do NOT rely on execute_code — its subprocess does not inherit shell env; use `terminal` with `source ~/.hermes/.env && python3 ...` instead.

Pattern:
1. Read `~/.hermes/config.yaml` to enumerate all providers (base_url, model, key_env, api_mode).
2. Source `~/.hermes/.env` in the same shell to load keys.
3. For each provider, POST to `{base_url}/chat/completions` with a minimal payload.
4. Report latency, HTTP status, and reply content per provider.

**Reasoning model symptom**: DeepSeek-V4-Flash, MiMo-v2.5-Pro, and similar reasoning models return `content=""` with `max_tokens≤20` because all budget goes to `reasoning_content`. This is NOT a provider failure — increase `max_tokens≥500` to get actual output. The `reasoning_content` field is non-standard, lives in `choices[0].message`, and is separate from `content`.

## Hermes config v26 migration + profile hygiene

When `hermes doctor` reports config version drift such as `v24 → v26` on default or `v23 → v26` on named profiles, use the official `doctor --fix` migration but treat it as a configuration change: baseline, back up default and profile configs, migrate, clean inert warnings, and smoke-test real model calls. Important lessons: Hermes stores `_config_version` (not necessarily `config_version`); profile aliases may need absolute paths (`~/.local/bin/pgg-law`) when tool PATH omits `~/.local/bin`; standard provider credential warnings (for example `DeepSeek invalid API key`) do not prove the active custom provider failed if a custom-provider smoke test succeeds. Detailed runbook: `references/config-v26-profile-migration-2026-06-03.md`.

## Gateway crash loop diagnosis

When the gateway restarts repeatedly (multiple PIDs in short succession in `gateway.log`):
1. Read `~/.hermes/logs/gateway.log` for the FIRST `NameError`/`ImportError`/`AttributeError` — not the last cascading error.
2. Check `hermes gateway status` for PID history and `LastExitStatus`.
3. Run `hermes update` if the error is in `conversation_loop.py` or `run_agent.py` — upstream fixes often land on `main` within hours.
4. After `hermes update`, verify the specific file was actually overwritten (check `ls -la` timestamp).

## Output contract

Report:

```text
status:
root_cause:
checked_keys_no_secrets:
fix_applied:
verification:
restart_needed:
```

## Rust evolution module (hermes_apex_evolution)

The Python PGG Archon evolution system (`agent/pgg_archon_*`, `agent/apex_*`, `tools/pgg_archon_tools`) was removed from the Hermes main branch. The replacement is a Rust-compiled Python module: `hermes_apex_evolution` v0.1.0 (Super Evolution 13), installed in the venv as `.so`.

**API**:
- `py_evaluate(workspace, output_file)` → APEX ΔE formula evaluation, returns JSON string
- `py_scout(topics_list, output_file)` → external source scouting (arXiv), may fail on network
- `py_audit(roots_list, output_file)` → code architecture audit (duplicates, large files, stale pyc)
- `start_evol_watcher(watch_dirs, log_path, threshold_int)` → start background file watcher
- `stop_evol_watcher()` / `evol_watcher_status()` → watcher control
- `version()` → version string

**Critical pitfalls**:
1. `evol_watcher` is **process-local** (thread in current process). Starting it in one Python process does NOT make it visible from another. For cron use, run watcher + evaluation in a single Python process.
2. `threshold` parameter must be `int`, not `float`.
3. Progress messages print to **stdout** mixed with return values. Use output files (`output_file` parameter) instead of parsing stdout.
4. `py_scout` depends on arXiv API — may fail on network issues.

**Cron pattern**: Single-process script that starts watcher, runs evaluate + audit, reads output files, generates report. See `references/rust-evolution-module-2026-06-03.md`.

**Post-install / migration hardening**: when a fresh Hermes install reuses an old `~/.hermes` tree, verify Rust module import, guard legacy Python APEX/SE20 cron jobs, hash-manifest untracked overlays before deletion, and keep GitHub/open-source scout read-only unless explicitly authorized. See `references/post-install-migration-hardening-20260603.md`.
   VENV="$HOME/.hermes/hermes-agent/venv"
   PYVER=$("$VENV/bin/python" - <<'PY'
import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')
PY
)
   SP="$VENV/lib/$PYVER/site-packages"
   cp "$HOME/.hermes/apex-evolution-engine/target/release/libhermes_apex_evolution.dylib" "$SP/hermes_apex_evolution.abi3.so"
   codesign --remove-signature "$SP/hermes_apex_evolution.abi3.so" 2>/dev/null || true
   codesign --force --sign - "$SP/hermes_apex_evolution.abi3.so"
   "$VENV/bin/python" - <<'PY'
import hermes_apex_evolution as m
print(m.version())
PY
   ```
6. Do not restore deleted legacy modules such as `agent.apex_runtimeos_autonomy` just to silence old cron errors. Prefer pausing/marking old jobs or replacing them with the Rust health job when the dependency chain is intentionally removed.

**Cron pattern**: Single-process script that starts watcher, runs evaluate + audit, reads output files, generates report. See `references/rust-evolution-module-2026-06-03.md`.

## Rust module core integration pattern

When integrating a Rust .so module into Hermes core (replacing deleted Python modules):

1. **Native tool**: Create `tools/<name>_tool.py`, register with `registry.register(name=..., toolset="hermes-cli", schema=..., handler=..., emoji=..., max_result_size_chars=...)`. Handler returns JSON string.
2. **Gateway startup hook**: Create `~/.hermes/hooks/<name>/HOOK.yaml` (events: `gateway:startup`) + `handler.py` (async def handle(event_type, context)). Hook runs on every gateway start.
3. **Launchd daemon**: For persistent background threads (like evol_watcher), create a standalone daemon script + `~/Library/LaunchAgents/ai.hermes.<name>.plist` with `KeepAlive` + `SuccessfulExit=false`. Write PID file for external status checks.
4. **Cron health check**: Create `~/.hermes/scripts/<name>.sh` that runs the full evaluation pipeline in a **single Python process** (watcher is process-local, cannot cross process boundaries).
5. **AGENTS.md**: Add a `## <Name> (Rust)` section documenting module, tool, daemon, hook, cron, formula, and API.
6. **Memory**: Save integration architecture for cross-session persistence.

Critical: Rust module threads are process-local. `start_evol_watcher()` in process A is invisible to process B. For cron, run watcher + evaluate + audit in one Python invocation.

Detailed runbook: `references/rust-module-core-integration-2026-06-03.md`.

## Multi-LLM parallel evaluation pattern

When user says "调用所有llm" or wants multi-model evaluation before a decision:
1. Use `delegate_task` with `tasks` array (up to 3 parallel) to invoke different LLM models.
2. Pass identical context + evaluation dimensions to each subagent.
3. Synthesize consensus — if all agree, high confidence; if split, present both sides.
4. Subagents run with `mimo-v2.5-pro` by default; to force GPT/Claude, the subagent's provider must be explicitly set or the task must be routed through the correct provider.
5. Multi-LLM evaluation is for DECISION SUPPORT, not execution — after consensus, execute directly.

## System-wide diagnosis pattern

When user asks to diagnose overnight errors or system-wide issues, run 3 parallel subagents:
- **Agent 1**: Logs + processes + gateway — `gateway.log`, `ps aux`, `launchctl list`, disk space
- **Agent 2**: Session DB + launchd + ports — `state.db` integrity, plist status, port listeners, config changes
- **Agent 3**: Cron jobs + skills + memory + workspace — `jobs.json` error scan, recent file changes, lock files

Each agent returns a structured report. Synthesize into timeline + root cause + fix plan.

## Full local config audit after reinstall / duplicate install

When the user says they had a local Hermes Agents deployment and then installed another Hermes Agent, do not answer from config presence alone. Run a class-level migration/runtime audit: install identity, active config/env paths, profiles, providers with key_env presence, real provider smoke tests using the correct API mode, gateway/launchd/Web UI health, session DB integrity, cron error chain, and dirty repo/overlay classification. Report “config reuse/profile present” separately from “capabilities fully migrated.” See `references/full-local-config-audit-after-reinstall-2026-06-03.md`.

## Hermes Desktop official-origin verification

When the user asks whether the Hermes Agent Desktop app is official, distinguish CLI/source deployment, Desktop app bundle identity, and download origin. Verify the provided URL directly, then inspect `/Applications/Hermes.app` bundle id/version/signing if present. The checked official Desktop page is `https://hermes-agent.nousresearch.com/desktop`, which links to `github.com/NousResearch/hermes-agent` and downloads from `hermes-assets.nousresearch.com/Hermes-Setup.dmg`. If `spctl` rejects the app because `TeamIdentifier=not set`, report it as official-origin but not Apple Developer ID/notarization verified, not automatically fake. See `references/desktop-official-origin-verification-2026-06-03.md`.

## Reference

Full command catalogue and edge-case repair notes are archived at:

- `references/chuangagent-responses-webui-provider-scope-20260605.md` — ChuangAgent GPT/Claude provider config, Web UI model visibility, upstream 502 retry adapter (also references `~/.hermes/scripts/gpt55_retry_adapter.sh`).
- `references/full-skill-archive-20260601.md`
- `references/multi-model-provider-health-check-2026-06-03.md` — provider testing script, reasoning model pitfall, known provider table
- `references/gpt55-codex-responses-token-param-20260603.md` — ChuangAgent GPT55 `/responses` empty-output diagnosis: use `max_tokens`/`max_completion_tokens` for visible text, not `max_output_tokens` only.
- `references/chuangagent-eu-cc-gpt55-chat-completions-endpoint-2026-06-04.md` — `gpt55_5yuantoken` working base_url is `https://chuangagent.eu.cc/v1/chat/completions` (per `~/.hermes/config.yaml`); 5yuantoken.com direct SSL-EOFs, minimax.chat 401s. Includes smoke recipe and 5-LLM 5/5 verification record.
- `references/launchd-plist-env-injection-2026-06-04.md` — backing up plists, idempotent `plutil -insert`, `launchctl unload`+`load` cycle, real verification vs `launchctl getenv` trap.
- `references/chuangagent-webui-responses-api-mode-ui-verified-20260605.md` — UI-verified GPT/Claude ChuangAgent Responses API rule: config.yaml alone is insufficient; Web UI available-models must propagate custom provider api_mode/key_env.
- `references/gateway-crash-loop-diagnosis-2026-06-03.md` — PID tracking, root error extraction, post-update verification
- `references/cron-dependency-chain-audit-2026-06-03.md` — step-by-step audit for broken cron jobs after code cleanup
- `references/rust-evolution-module-2026-06-03.md` — hermes_apex_evolution API, pitfalls, cron pattern, replaced modules
