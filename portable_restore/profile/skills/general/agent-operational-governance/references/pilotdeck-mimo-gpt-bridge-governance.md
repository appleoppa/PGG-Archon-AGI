# PilotDeck MIMO-main + GPT-collaboration governance

Use this reference when repairing or extending PilotDeck as an independent agent while preserving Hermes/PilotDeck filesystem isolation.

## Stable layout

- PilotDeck physical root: `/Users/appleoppa/.pilotdeck-agi`
- PilotDeck configured home: `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck`
- Default app entrypoint: `/Users/appleoppa/.pilotdeck -> /Users/appleoppa/.pilotdeck-agi/home/.pilotdeck`
- Bridge/sync root: `/Users/appleoppa/.agent-bridge`

The symlink is intentional: PilotDeck.app/default startup reads `~/.pilotdeck`; without the symlink it may read a placeholder onboarding config and ask for LLM setup even when the hidden configured home is valid.

## Model boundary pattern

Target model roles:

```text
MIMO:
  provider/model: mimo_v25_pro_auditor/mimo-v2.5-pro
  role: main agent/router/fallback/memory/tokenSaver/tools/reasoning

GPT:
  provider/model: gpt55_5yuantoken/gpt-5.5
  route: http://127.0.0.1:18888/v1 via local Hermes bridge
  role: collaboration/evolution no-tools model
  supportsToolUse: false
  supportsStreaming: true

Agnes:
  provider/model: agnes_ai/agnes-2.0-flash
  role: chat-only/no-tools
  supportsToolUse: false
```

Do not promote GPT or Agnes into the main tools route when the user wants MIMO as the PilotDeck主控 LLM.

## GPT bridge pattern

PilotDeck can use GPT-5.5 through a local OpenAI-compatible bridge instead of calling GPT directly via `/v1/chat/completions` upstream.

Example provider block:

```yaml
gpt55_5yuantoken:
  protocol: openai
  url: http://127.0.0.1:18888/v1
  apiKey: <LOCAL_BRIDGE_PLACEHOLDER>
  timeoutMs: 180000
  models:
    gpt-5.5:
      displayName: GPT-5.5 Collaboration via Hermes Bridge (no-tools)
      capabilities:
        supportsToolUse: false
        supportsStreaming: true
        supportsParallelToolCalls: false
        supportsThinking: true
        supportsJsonSchema: false
        supportsSystemPrompt: true
        maxContextTokens: 1000000
        maxOutputTokens: 8192
```

Bridge startup script used in this deployment:

```bash
/Users/appleoppa/.pilotdeck-agi/state/pilotdeck-agi-overlay/bin/start_pilotdeck_llm_bridge.sh
```

Start long-lived bridge processes with Hermes `terminal(background=true)`, not shell `&`, so lifecycle/output remains tracked.

## Runtime guard requirement

Config flags like `supportsToolUse: false` are not sufficient by themselves. Add/verify router runtime assertions so any request containing tools that selects Agnes (or another no-tools provider) is rerouted to the default MIMO model and the mutation is recorded.

Expected mutation shape:

```json
{
  "from": "agnes_ai/agnes-2.0-flash",
  "to": "mimo_v25_pro_auditor/mimo-v2.5-pro",
  "reason": "selected model is chat-only/no-tools while request contains tools"
}
```

## Verification checklist before reporting success

1. Config readback:
   - providers include `mimo_v25_pro_auditor`, `agnes_ai`, and if enabled `gpt55_5yuantoken`.
   - `agent`, router default/fallback, `memory`, and tokenSaver point to MIMO.
   - GPT and Agnes are providers-only/no-tools.
2. Bridge health:
   - `127.0.0.1:18888` listening.
   - `/health` returns HTTP 200 and includes `gpt55_5yuantoken`.
3. Real model probes:
   - MIMO chat and tool-call probe return real HTTP 200/tool_calls evidence.
   - GPT bridge non-stream returns `GPT_BRIDGE_OK` or equivalent.
   - GPT bridge stream returns `GPT_STREAM_OK` or equivalent.
   - PilotDeck ModelRuntime call returns `GPT_COLLAB_OK` or equivalent through PilotDeck, not just through Hermes.
4. Service ports:
   - Gateway `18789`
   - UI server `3001`
   - UI client `5173`
   - LLM bridge `18888`
5. Repo state:
   - commit only code changes that belong in the PilotDeck repo.
   - config/report/state-overlay files may live outside the repo; report that distinction.
6. Reports:
   - Ask PilotDeck to write/read back its own self-check report under the hidden PilotDeck home.
   - Archive Hermes-side sync under `/Users/appleoppa/.agent-bridge/reports/`.

## Reporting style for this user

When the user says a PilotDeck/Hermes dialog is stuck, do not ask them to repeat everything. Use session logs/state files to resume, continue silently where possible, and report concise evidence: ports, provider/model layout, key probe tokens, config SHA, report paths, and git status.
