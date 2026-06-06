# Independent Agent Hidden-Bridge Deployment Pattern

Use this reference when absorbing or upgrading an external agent platform into a second/auxiliary AGI-like node while preserving physical isolation from Hermes.

## Durable lesson from PilotDeck session

The user corrected two workflow errors that must be prevented proactively:

1. Do not deploy a separate agent under `~/.hermes/workspace` if the goal is an independent agent. That mixes runtimes and violates physical isolation.
2. Do not create visible project folders in the user's Home root. Independent agent roots and bridge roots must be hidden directories, similar to `~/.hermes`.

Correct class-level layout:

```text
~/.hermes              # Hermes AGI runtime/state/config only
~/.<agent>-agi         # independent external agent runtime/state/config only
~/.agent-bridge        # hidden bridge for snapshots, proposals, localhost services, evidence
```

For PilotDeck specifically the accepted layout was:

```text
~/.pilotdeck-agi       # PilotDeck repo, config, state, memory, overlay
~/.agent-bridge        # Hermes ↔ PilotDeck bridge, LLM bridge, reports, proposals
```

## Required sequence before file operations

1. Identify whether the user wants integration into Hermes or an independent agent.
2. If independent: choose hidden root names before creating files.
3. Check for Home root pollution risk; never create visible folders like `~/PilotDeckAGI` or `~/AgentBridge`.
4. Keep Hermes read-only unless explicitly modifying Hermes; bridge outputs go under the bridge root.
5. After migration or deployment, verify absence of visible pollution paths and presence of hidden roots.

## Bridge pattern for sharing LLMs without mixing agents

When the independent agent has limited model access, do not copy Hermes secrets into the independent agent config. Instead:

- Run a localhost-only bridge under `~/.agent-bridge`.
- PilotDeck/external agent points to `http://127.0.0.1:<port>/v1` using a non-secret placeholder key if its schema requires one.
- Bridge reads Hermes config/environment read-only and forwards to configured providers.
- Preserve provider protocol correctness: GPT/Claude configured for Responses API must be called through `/v1/responses`; chat-compatible providers may use `/v1/chat/completions`.
- Bridge writes smoke-test evidence and sync reports under `~/.agent-bridge` only.

## Verification checklist

- Gateway/UI health checks for the independent agent pass.
- LLM bridge health lists expected providers.
- Each shared model has a real smoke test through the bridge.
- Independent agent config reads the bridge URL, not real API keys.
- No visible Home root folders remain from the deployment.
- Bridge snapshot/proposal files exist and make clear that writes are proposals, not automatic core mutations.

## Report language

Use bounded claims: independent agent, second node, bridge, shared LLM, proposal, evidence gate. Do not claim full AGI, unsupervised takeover, or replacement of Hermes scheduler/security boundary.
