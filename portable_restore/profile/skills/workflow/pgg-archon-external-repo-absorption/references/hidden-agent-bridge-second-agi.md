# Hidden Agent Bridge / Second AGI Absorption Reference

Use this reference when absorbing an external agent platform into the PGG Archon/Hermes ecosystem as an auxiliary or second AGI candidate.

## Durable lesson from PilotDeck absorption

The user corrected a serious workflow mistake: do not create visible project folders directly under the user's Home directory for auxiliary agents or bridge layers. Even if the intent is physical isolation from Hermes, visible Home-root folders such as `~/PilotDeckAGI` or `~/AgentBridge` violate the user's file hygiene rule.

Correct pattern:

```text
Hermes root:       ~/.hermes
Aux agent root:    ~/.<agent-name>-agi        # example: ~/.pilotdeck-agi
Bridge root:       ~/.agent-bridge            # hidden, neutral exchange layer
```

Do not deploy the external agent under `~/.hermes/workspace` if the user requires it to be a physically separate agent. Do not create visible Home-root project folders. Use hidden roots analogous to `~/.hermes`.

## Preflight before writing files

Before cloning, moving, generating reports, or starting services:

1. Identify whether the target is a Hermes-internal artifact or an independent agent.
2. If independent, choose a hidden root outside `~/.hermes`, e.g. `~/.pilotdeck-agi`.
3. Choose an independent hidden bridge root, e.g. `~/.agent-bridge`.
4. Verify no visible Home-root pollution will be created.
5. After migration or generation, scan for stale visible paths and stale `~/.hermes/workspace` runtime references.
6. Verify running process CWD, config root, memory root, UI/Gateway health, and bridge outputs.

## Bridge architecture

For two independent agents, use a neutral bridge rather than shared runtime/state:

```text
~/.hermes                 # Hermes AGI runtime/state/config
~/.pilotdeck-agi          # PilotDeck or other auxiliary agent runtime/state/config
~/.agent-bridge           # snapshots, learning packs, proposals, reports, local proxy services
```

Allowed data flow:

- Hermes -> Bridge: read-only snapshots, core config summaries, evolution manifests, skill summaries.
- Bridge -> auxiliary agent: learning packs, formula mappings, shared LLM proxy endpoint, proposals.
- Auxiliary agent -> Bridge: capability diffs, formula-gate evidence, audit summaries.

Disallowed data flow:

- Auxiliary agent writing into `~/.hermes`.
- Hermes and auxiliary agent sharing runtime/state/config folders.
- Bridge automatically mutating either agent core without an explicit gate.
- Copying actual API keys into the auxiliary agent.

## Shared LLM pattern

If the auxiliary agent should use Hermes-connected models but must not hold secrets, expose a localhost-only bridge service under the hidden bridge root. The auxiliary agent points at the bridge URL, not at real provider endpoints or secret values.

Example shape:

```text
LLM Bridge: http://127.0.0.1:<local-port>/v1
Aux config: provider URLs all point to the local bridge
Secrets: remain in Hermes config/env; do not copy values
```

For providers with protocol differences, the bridge must route correctly. In the PilotDeck session, GPT/Claude used Responses API while chat-compatible models used chat completions; the bridge normalized this for the auxiliary agent.

## Formula-gate absorption pattern

Do not claim the auxiliary agent became a full AGI. Use bounded language and evidence gates:

```text
SECOND_AGI_CANDIDATE_ACTIVE_LEARNING
SECOND_AGI_CANDIDATE_FORMULA_GATE_RUN
SECOND_AGI_LEARNING_GATE_PASSED_BOUNDED
```

Minimum evidence before reporting success:

- Auxiliary agent has its own `EVOLUTION_MANIFEST.json` under its hidden root.
- Auxiliary agent has its own core Markdown describing identity, boundaries, formula mapping, and non-claims.
- Formula gate script runs and writes evidence under the auxiliary root.
- All configured LLM auditors are actually called through the bridge.
- Post-gate multi-LLM review is read back.
- UI/Gateway/LLM bridge health checks pass.

## User-preference pitfall

This user strongly dislikes avoidable low-level file-placement mistakes because they waste token and time. For this class of task, treat file-system boundary preflight as a mandatory first step, not a cleanup step after deployment.
