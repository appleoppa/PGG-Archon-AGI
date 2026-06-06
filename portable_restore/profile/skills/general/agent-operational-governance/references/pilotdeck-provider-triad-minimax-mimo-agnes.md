# PilotDeck provider triad: MiniMax + MIMO + Agnes

## When to use

Use when configuring PilotDeck as an independent agent runtime with a three-model learning/evolution pool, especially when replacing a GPT bridge/no-tools collaboration model with MiniMax while preserving MIMO as the default tool executor and Agnes as chat-only/audit.

## Durable pattern

1. Scope and back up first.
   - Active PilotDeck hidden home: `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck`.
   - Back up `pilotdeck.yaml` and `.env` under `backups/<timestamp>/` before editing.
   - Verify `~/.pilotdeck` symlinks to the hidden home when Desktop/default startup is involved.

2. Remove GPT cleanly when requested.
   - Delete `gpt55_5yuantoken` or other `gpt*` providers from `model.providers`.
   - Remove PilotDeck-local `GPT55_5YUANTOKEN_API_KEY` from `.env` if PilotDeck no longer uses it.
   - Do not remove Hermes-side GPT config unless the user explicitly asks; PilotDeck and Hermes are separate scopes.

3. Add MiniMax from Hermes env into PilotDeck env/config.
   - Copy only the `MINIMAX_API_KEY` value from Hermes `.env` into PilotDeck `.env`; never print the key.
   - Provider block:

```yaml
minimax_m3:
  protocol: openai
  url: https://api.minimax.chat/v1
  apiKey: ${MINIMAX_API_KEY}
  timeoutMs: 180000
  models:
    MiniMax-M3:
      displayName: MiniMax M3 Learning/Evolution LLM
      capabilities:
        supportsToolUse: true
        supportsStreaming: true
        supportsParallelToolCalls: false
        supportsThinking: true
        supportsJsonSchema: false
        supportsSystemPrompt: true
        maxContextTokens: 1000000
        maxOutputTokens: 8192
```

4. Recommended role boundary.
   - `MIMO`: default agent, tools execution, router default/fallback, memory.
   - `MiniMax`: learning/evolution, complex/reasoning tokenSaver tiers, tools-capable direct provider.
   - `Agnes`: chat-only/no-tools audit scenario.

Example router shape:

```yaml
router:
  scenarios:
    default: mimo_v25_pro_auditor/mimo-v2.5-pro
    learning: minimax_m3/MiniMax-M3
    evolution: minimax_m3/MiniMax-M3
    audit: agnes_ai/agnes-2.0-flash
  fallback:
    default:
      - mimo_v25_pro_auditor/mimo-v2.5-pro
      - minimax_m3/MiniMax-M3
    learning:
      - minimax_m3/MiniMax-M3
      - mimo_v25_pro_auditor/mimo-v2.5-pro
    evolution:
      - minimax_m3/MiniMax-M3
      - mimo_v25_pro_auditor/mimo-v2.5-pro
    audit:
      - agnes_ai/agnes-2.0-flash
      - minimax_m3/MiniMax-M3
  tokenSaver:
    judge: mimo_v25_pro_auditor/mimo-v2.5-pro
    tiers:
      simple:
        model: mimo_v25_pro_auditor/mimo-v2.5-pro
      medium:
        model: mimo_v25_pro_auditor/mimo-v2.5-pro
      complex:
        model: minimax_m3/MiniMax-M3
      reasoning:
        model: minimax_m3/MiniMax-M3
```

5. Update local governance scripts/reports after provider changes.
   - If existing invariant/evidence scripts still assert GPT bridge presence or port `18888`, update them to the new triad; otherwise the evidence chain will report stale requirements.
   - Do not keep a local GPT bridge as a hidden prerequisite after removing the GPT provider.

## Verification ladder

Run all of these before claiming completion:

1. Direct MiniMax entitlement and capability probe:
   - `GET https://api.minimax.chat/v1/models` returns HTTP 200 and includes `MiniMax-M3`.
   - `POST /chat/completions` returns normal assistant text.
   - A `tools` payload returns `tool_calls` before marking `supportsToolUse: true`.
2. Build PilotDeck: `npm run build` from the PilotDeck repo.
3. Restart PilotDeck gateway/UI; verify ports `18789`, `3001`, `5173`.
4. Read `/api/config`; confirm active providers are exactly MIMO/MiniMax/Agnes and config path is the hidden home.
5. POST `/api/config/validate`; require `valid=true`, no errors.
6. Run/update invariant checker; require checks for GPT removed, MiniMax tools, MIMO tools, Agnes no-tools, router scenarios, fallback, tokenSaver tiers, symlink.
7. Gateway smoke test: submit a real turn and require `turn_completed`, no error event, and a visible marker such as `CHANNEL_TRIAD_OK`.
8. Re-run PilotDeck evidence-chain and update Hermes `EVOLUTION_MANIFEST.json` with a compact readback.

## Pitfalls

- MiniMax may include `<think>` text before the requested visible answer. Do not treat that alone as failure if the response shape and final content are valid.
- Removing GPT from PilotDeck does not imply removing GPT from Hermes; keep scope isolated.
- If the previous pipeline score drops because it expected GPT bridge port `18888`, update the checker to the new architecture rather than restarting an obsolete bridge.
- Agnes remains `supportsToolUse: false`; never route tools-bearing default tasks to Agnes.
