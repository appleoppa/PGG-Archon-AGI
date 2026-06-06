# PilotDeck submit_turn Smoke — 2026-06-06

## Trigger

Use after PilotDeck protocol smoke v4 passes and you need to verify the gateway can run a minimal real turn, not just `describe_server` / `list_projects`.

## Preconditions

- Gateway is running at `127.0.0.1:18789`.
- `curl http://127.0.0.1:18789/health` returns `{"ok":true}`.
- WebSocket hello smoke passes with exact `protocolVersion: "1.0"`.
- Token is read from `~/.pilotdeck/server-token`; never print token value.

## `GatewaySubmitTurnInput` essentials

Source: `src/gateway/protocol/types.ts`.

Required:

```ts
{
  sessionKey: string,
  channelKey: GatewayChannelKey,
  message: string
}
```

Useful low-risk smoke fields:

```ts
{
  projectKey: "/Users/appleoppa/.pilotdeck-agi/PilotDeck",
  workspaceCwd: "/Users/appleoppa/.pilotdeck-agi/PilotDeck",
  mode: "bypassPermissions",
  maxTurns: 1,
  runId: "pgg-submit-smoke-...",
  telemetry: {
    ownerModule: "gateway",
    executionKind: "manual",
    phase: "pgg_submit_turn_smoke"
  }
}
```

## Minimal safe prompt

```text
低风险 smoke：请只回复一句中文“PilotDeck submit_turn smoke PASS”，不要调用工具，不要修改文件。
```

## Expected PASS chain

```text
open
→ hello(protocolVersion="1.0")
→ hello_ok
→ request(method="submit_turn")
→ turn_started
→ optional context_budget / router status / thinking deltas
→ assistant_text_delta
→ turn_completed(final=true)
```

PASS conditions from verified run:

```text
status=PASS
assistantChars > 0
toolCalls = 0
errorEvents = []
finishReason = completed
usage present
```

Verified local run example:

```text
runId=pgg-submit-smoke-1780725635436
sessionKey=pgg-submit-smoke-386f0961-209d-464e-9a8f-96f9183ac9cd
assistantChars=32
toolCalls=0
eventsCount=23
usage=inputTokens 13097 / outputTokens 39 / totalTokens 13136
```

## Boundary wording

Minimal `submit_turn` smoke proves that PilotDeck gateway can authenticate, route, stream, and complete a short non-tool turn. It does not prove long task execution, tool correctness, autonomous production takeover, external benchmark success, or AGI level increase.

## Evidence settlement

- Evidence dir shape: `~/.hermes/workspace/pgg-archon-governance/pilotdeck-submit-turn-*`
- Summary: `submit_turn_smoke_summary.json`
- Full event log: `ws_submit_turn_smoke.json`
- Rust settlement binary: `rust_modules/hermes_pgg_pilotdeck/src/bin/pilotdeck_sync_evidence.rs`
- Manifest key shape: `latest_pilotdeck_sync_evolution_<unix>`

## Pitfalls

- A successful `describe_server/list_projects` smoke is not enough for turn execution.
- Keep `maxTurns=1` for low-risk smoke.
- For this smoke, any `tool_call_started` should downgrade verdict to WATCH unless explicitly intended.
- Router/config change notifications during the stream are not necessarily failures; classify by final turn event and error events.
