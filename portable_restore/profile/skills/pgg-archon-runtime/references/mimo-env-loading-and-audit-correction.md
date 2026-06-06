# MIMO auditor key loading and correction pattern

## Trigger

Use this when PGG Archon / legal AGI / evolution audit tasks need `mimo_v25_pro_auditor`, or when a prior check says the MIMO key is missing.

## Durable lesson

Do not conclude that MIMO is unconfigured merely because the current Python/tool subprocess lacks `MIMO_V25_PRO_API_KEY` in `os.environ`.

Hermes profile secrets may be stored in `~/.hermes/.env` and loaded by Hermes/gateway paths, while ad-hoc tool subprocesses may not automatically source that file.

## Correct verification order

1. Read `~/.hermes/config.yaml` and confirm the `mimo_v25_pro_auditor` provider has:
   - `api_mode: chat_completions`
   - `base_url: https://token-plan-cn.xiaomimimo.com/v1`
   - `model: mimo-v2.5-pro`
   - `key_env: MIMO_V25_PRO_API_KEY`
2. Check current process env only as one signal, not the final truth.
3. Check `~/.hermes/.env` for `MIMO_V25_PRO_API_KEY` without printing the secret. Report only presence, length, and a short hash fingerprint.
4. If the key exists in `.env` but not `os.environ`, manually load it for the probe and call MIMO.
5. Record real audit evidence:
   - HTTP status
   - response_id
   - response body hash
   - concise audit summary
6. If an earlier report/GeneDB entry incorrectly said “key missing” or “blocked_no_key_env”, append a correction rather than silently overwriting history.

## Safe reporting language

Correct:

```text
MIMO key is configured in ~/.hermes/.env, but the current tool subprocess did not auto-load it. Manual .env load returned HTTP 200.
```

Incorrect:

```text
MIMO key is not configured.
```

## Evidence hygiene

Never print the key. Use length and SHA256 prefix only. If correcting a prior audit, write an append-only correction gene and re-sync affected reports/JSON with readback hash verification.
