# GPT55 ChuangAgent codex_responses empty-output quirk — 2026-06-03

## Symptom

Ad-hoc calls to `gpt55_5yuantoken` at `/v1/responses` can return:

- HTTP 200
- `status=completed`
- non-zero token usage
- `output=[]`
- no visible text

This occurred even with prompts requiring a short exact reply when the caller sent only `max_output_tokens`.

## Root cause observed

The ChuangAgent `codex_responses` proxy for `gpt-5.5` appears not to map `max_output_tokens` the same way as the upstream Responses API. The returned JSON echoed `max_output_tokens: null`; small/default budget was consumed by reasoning, leaving no message output.

This is a provider/proxy compatibility issue, not a credential failure.

## Verified fix

For ad-hoc calls to GPT55/Claude through this proxy:

```json
{
  "model": "gpt-5.5",
  "input": "...",
  "max_tokens": 5000,
  "tool_choice": "none"
}
```

or:

```json
{
  "model": "gpt-5.5",
  "input": "...",
  "max_completion_tokens": 5000,
  "tool_choice": "none"
}
```

Do **not** switch GPT/Claude to `/chat/completions`; keep the Responses endpoint and change only the compatible token-budget parameter for this proxy.

## Extraction pattern

1. Prefer `output_text` if present.
2. Else iterate `output[]`; skip `type=reasoning`; collect `content[].text` from message items.
3. Treat HTTP 200 with no visible text as `LLM_EMPTY_OUTPUT`, not success.
4. Retry once with `max_tokens` or `max_completion_tokens >= 500`.
5. Record `provider`, `model`, endpoint, budget parameter used, `visible_output`, chars, elapsed, and output path.

## Completion evidence pattern

A real fix requires a smoke call such as `只输出 EXACT_OK` producing visible text, plus one substantive task call with visible text. In the session that produced this reference, GPT round3 returned visible output after the fix (`chars=13563`).

## Boundaries

- Do not print API keys.
- Do not claim GPT participated if only metadata/no visible text was returned.
- Do not count `output=[]` as a substantive audit.
- Do not persist this as a universal OpenAI rule; it is a ChuangAgent `codex_responses` proxy quirk.
