# Provider purge runbook

Use when the user asks to remove all local configuration for one LLM provider, e.g. `清除本机所有关于 X 的配置`.

## Scope

Treat this as a configuration purge, not a source-code/documentation purge unless the user explicitly asks to delete docs/tests/examples.

Include:

- Active `~/.hermes/config.yaml` provider blocks and fallback entries.
- Active `~/.hermes/auth.json` provider/auth records.
- Active `~/.hermes/.env` secret variables and provider comment blocks.
- Named profile configs under `~/.hermes/profiles/<profile>/config.yaml` and `.env`.
- Department/local agent provider catalogs such as `agents/*/agent/models.json` and `agents/*/agent/auth-profiles.json`.
- Runtime inherited environment where applicable: `launchctl unsetenv <PROVIDER_VAR>` and related base-url vars on macOS.
- User-facing rules that still name the provider in fallback chains or provider-selection policy files, if those files are active context/config rather than historical docs.

Exclude by default:

- Bundled Hermes source docs/tests/examples unless the user asks to modify the product repository itself.
- External cloned repositories under workspace; do not bulk-normalize or rewrite third-party config files just because they contain the provider name.
- Session logs, audit reports, skills/templates, historical prose, and unrelated reports unless they are active configuration or active operating rules.
- Backup directories created during the purge if they would preserve the provider secret/config after a request for “all local configuration” removal. Prefer either no retained secret backup or a redacted manifest-only backup.

## Safe workflow

1. Load `hermes-agent` only for command context if needed, but do not patch protected bundled skills.
2. Search for the provider name in config-like locations first; classify active config vs docs/tests/logs/reports/external repos.
3. Before editing, avoid printing secrets; redact keys and only show variable names/fingerprints if necessary.
4. Remove whole structured provider nodes from YAML/JSON rather than deleting lines blindly.
5. Remove provider entries from `fallback_providers`, credential pools, auth-provider maps, Web UI model catalogs, and per-agent auth maps.
6. Remove provider env vars from active `.env` files and unset launchd environment variables on macOS.
7. If a backup is required, make it redacted or delete the temporary backup after verification so the provider configuration is not still present locally.
8. Validate JSON/YAML parsing after edits.
9. Verify zero hits within the scoped active configuration set and separately report any excluded docs/tests/logs if relevant.
10. Run the relevant Hermes config check or provider-list readback; note if the current already-running shell still inherited a removed environment variable and requires restart.

## Verification fields

Return concise fields:

```text
status:
changed_scope:
active_config_hits_after:
parse_check:
provider_keys_after:
fallback_after:
runtime_env_after:
restart_needed:
excluded_not_modified:
```

## Pitfalls

- `hermes config check` may list optional provider env names even after the provider was removed from custom config; this is a built-in optional catalog, not proof the provider remains configured.
- A running shell can still show an env var inherited before `.env`/launchd cleanup. Distinguish persistent config from current-process environment and recommend restart.
- Do not use broad YAML cleanup across external repos; it can rewrite unrelated third-party files and create noisy diffs.
- Removing a provider from active config should also update durable memories or active operating-rule files that still list it as a fallback, otherwise future sessions may reintroduce it.
