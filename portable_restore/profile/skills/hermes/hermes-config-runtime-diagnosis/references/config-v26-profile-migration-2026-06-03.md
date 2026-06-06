# Hermes config v26 migration + profile hygiene (2026-06-03)

## When to use

Use after `hermes doctor` reports `Config version outdated (v24 → v26)` or named profiles report `v23 → v26`, especially when default plus multiple `pgg-*` profiles/gateways are running.

## Safe workflow

1. Load `hermes-agent` if the user is asking about Hermes itself.
2. Baseline without secrets:
   - `hermes status`
   - `hermes doctor`
   - `hermes profile list`
   - `hermes gateway status`
   - Web UI health probe: `http://127.0.0.1:8648/health` with `X-Hermes-Profile: default` when applicable.
3. Back up default and profiles before modifying:
   - create `~/.hermes/workspace/config-backups/hermes-config-v26-migration-<timestamp>/`
   - copy `~/.hermes/config.yaml`
   - copy `~/.hermes/profiles/*/config.yaml`
   - write `SHA256SUMS.txt`.
4. Run official migration first:
   - default: `hermes doctor --fix`
   - profiles: use profile aliases such as `~/.local/bin/pgg-law doctor --fix`; for all aliases, loop over `~/.local/bin/pgg-*`.
5. Read back `_config_version` from every config. YAML parsing may not expose `config_version`; Hermes uses `_config_version`.
6. Clean only clearly inert warnings:
   - Unknown toolset `legal_kb` in `platform_toolsets` can be removed from auto-load lists if Hermes reports `Unknown toolsets: legal_kb`.
   - Keep unrelated budget entries such as `tool_result_budget.tool_overrides.legal_kb` unless the user asks for full removal; they are harmless if a plugin/toolset returns later.
   - Empty custom provider placeholders with `api_mode: anthropic_messages`, `models: {}`, and no `name`/`base_url` can be removed from `custom_providers[]` after backup.
7. Verify after cleanup:
   - `hermes doctor` shows `Config version up to date (v26)`.
   - At least one representative profile doctor shows v26.
   - `hermes profile list` gateways remain running.
   - Web UI `/health` returns 200.
   - Smoke test default + representative profiles with `hermes chat -Q --source smoke-test -q ...` and profile aliases by absolute path if PATH omits `~/.local/bin`.
   - Read matching `agent.log` entries by `session_id` to prove a real API call happened.

## Pitfalls

- Do not interpret standard-provider credential warnings as proof that a custom provider path is broken. Example: `DeepSeek (invalid API key)` in doctor may refer to the standard `DEEPSEEK_API_KEY`, while `custom:deepseek_v4_flash` can still pass a real smoke test.
- Some tool runners have PATH without `~/.local/bin`; profile aliases like `pgg-law` may return `command not found`. Use absolute paths (`$HOME/.local/bin/pgg-law`) instead of saving a false “profile broken” conclusion.
- Gateway processes do not need immediate restart if health, profile list, and fresh CLI smoke tests pass. Recommend restart only if long-lived gateway runtime must fully reload new config.
- Avoid printing secrets or dumping full `.env`; report key presence and provider names only.

## Example verification signals

- `✓ Config version up to date (v26)`
- `OK_NO_BAD_PROVIDER_OR_LEGAL_KB_TOOLSET` from a static hygiene probe
- Web UI health JSON: `status: ok`, `gateway: running`
- Smoke responses such as `PONG_CLEAN_DEFAULT gpt-5.5` plus log lines containing `API call #1 ... provider=custom`.
