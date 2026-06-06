# Quantum Channel Router vs Web UI — Integration Model

## Key Distinction

The `qr` CLI and the Hermes Web UI are **independent model selection systems**:

| System | How Model is Selected | Scope |
|--------|-----------------------|-------|
| **`qr` CLI** | Auto-classifies task (A/B/C/D) → routes to best LLM | Agent-initiated tasks |
| **Web UI** | User selects a Profile → Profile has fixed model | Manual chat sessions |

## How They Work Together

1. **When I (Hermes agent) call `qr route "<task>"`** — I get a routing decision and use the recommended LLM for sub-agents, code execution, or tool calls. This is autonomous.

2. **When you use Web UI Chat** — you're connected to a Profile. The profile's model is used for that conversation, regardless of what `qr` would recommend.

3. **Best practice:** Set the default profile's model to your most capable all-rounder (e.g. gpt-5.5 or deepseek-v4-flash). Use `qr route` for task-specific routing in automated contexts.

## No Direct Integration

`qr` does NOT modify what the Web UI shows. The Web UI:
- Shows models from `model_context` DB table + `modelVisibility` config
- Controls model via profile configuration
- Has its own GatewayManager for gateway lifecycle

To make a model available in BOTH systems, configure it in:
1. `~/.hermes/config.yaml` (providers section) — for `qr`
2. `~/.hermes-web-ui/config.json` (modelVisibility) — for Web UI
3. `~/.hermes-web-ui/hermes-web-ui.db` (model_context table) — for Web UI dropdown
