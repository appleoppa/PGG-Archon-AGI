# Context Compression Hangs — Diagnostic Pattern

Use when Hermes/Web UI/CLI appears stuck during “compressing context”, “context compaction”, or long conversations stall around session split.

## Durable lesson

Context compression is not a local instant operation. Hermes serializes earlier turns and calls an auxiliary LLM to create a structured checkpoint summary. If `auxiliary.compression` is `provider: auto` with empty `model`, it may reuse the main provider/model. For custom/aggregator endpoints this can hang or fail when the compression request is large, even if normal chat works.

## High-signal checks

1. Load `hermes-agent` first.
2. Inspect targeted config fields only:
   - `model.provider`, `model.default`
   - `compression.enabled`, `threshold`, `target_ratio`, `protect_last_n`, `protect_first_n`
   - `auxiliary.compression.provider`, `model`, `timeout`, `context_length`
   - `context.engine`
3. Search logs for these patterns:
   - `Failed to generate context summary`
   - `Request timed out`
   - `Session split detected`
   - `Auxiliary compression`
   - `Unknown Model`
   - provider gateway HTML/Cloudflare `502`
4. Interpret evidence carefully:
   - `Session split detected (... compression)` proves compression was triggered.
   - `Failed to generate context summary: Request timed out` indicates the auxiliary summary call stalled or exceeded timeout.
   - `Unknown Model` in auxiliary/session summarization means the auxiliary route/model name is invalid for that provider.
   - Provider HTML/Cloudflare 5xx means upstream/proxy instability, not necessarily Hermes frontend failure.

## Common fix pattern

Prefer setting a dedicated, stable, fast auxiliary model for compression instead of `auto`, especially when the main model is a custom/aggregator endpoint.

Example shape:

```yaml
auxiliary:
  compression:
    provider: <known-working-provider>
    model: <known-working-fast-summary-model>
    timeout: 60
```

For custom providers, verify the exact provider identifier and whether the auxiliary router accepts `custom:<name>` or needs explicit `base_url`/`api_key`/`api_mode` before editing. Do not guess the syntax.

## Reporting style

Report as a diagnosis, not speculation:

- State the compression mechanism in one sentence.
- Provide a compact evidence table: config, log pattern, implication.
- Separate “high certainty” findings from “needs live verification”.
- Avoid dumping full logs or full config; quote only decisive lines.

## Pitfalls

- Do not say the frontend is frozen unless process/browser evidence supports it; often it is waiting on an auxiliary LLM call.
- Do not disable compression as the default permanent fix; it is usually an emergency workaround.
- Do not record one provider’s temporary outage as a durable rule. Capture the routing pattern and verification steps instead.
