# LLM Provider Audit + Context Limit Normalization

Use when the user asks to detect, reorganize, or make all Hermes LLM configurations通畅, especially with accurate context windows.

## Durable pattern

1. Load the Hermes configuration skill first for Hermes Agent tasks, but do not edit protected bundled skills.
2. Inspect `~/.hermes/config.yaml` and `.env` without printing secrets. Verify `key_env` presence only.
3. Treat `providers` and `custom_providers` as two surfaces that must stay aligned:
   - `name`
   - `model` / `default_model`
   - `api_mode`
   - `base_url`
   - `key_env`
   - top-level `context_length`
   - per-model `models.<model>.context_length`
4. For GPT/Claude custom providers in this setup, keep `api_mode: codex_responses` and test `/v1/responses`; do not regress them to `/v1/chat/completions`.
5. For Anthropic-compatible MiniMax, test `/anthropic/v1/messages`; `/models` may return 404 and is not proof the message API is broken.
6. Confirm provider reachability with tiny live calls, not only `/models` listings. Use retries for transient SSL EOF / read timeouts; capture the retry outcome rather than hard-coding a negative tool claim.
7. Align auxiliary users of LLM metadata, especially:
   - `auxiliary.compression.context_length`
   - `auxiliary.session_search.context_length`
   - route/debate maps if they carry model metadata
8. Back up `config.yaml` before rewriting.
9. Verify by both config validation and live probes. If core metadata behavior matters, run targeted model metadata tests.

## Context limits used in the 2026-06-01 audit

These were aligned with the local `agent/model_metadata.py` fallback table and live provider availability probes:

- `gpt-5.5`: 1,050,000 tokens
- `claude-opus-4-7`: 1,000,000 tokens
- `deepseek-v4-flash`: 1,000,000 tokens
- `MiniMax-M2.7-highspeed`: 204,800 tokens
- `mimo-v2.5-pro`: 1,048,576 tokens

## Verification evidence shape

Report compact fields:

- backup path
- config validation status
- provider/model/API mode/context length
- HTTP status for each tiny live call
- retry note if a transient network error resolves
- targeted test result count if tests were run

Do not print API keys or raw `.env` values.
