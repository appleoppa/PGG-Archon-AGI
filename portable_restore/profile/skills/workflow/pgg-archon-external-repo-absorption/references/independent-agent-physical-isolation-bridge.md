# Independent Agent Physical Isolation + Bridge Pattern

Use when an external repo is not just being absorbed as a library/module, but is intended to become an independent agent that co-evolves with Hermes/PGG Archon.

## Core rule

Do **not** deploy the external agent inside `~/.hermes/workspace` or any Hermes runtime/config/state folder when the user frames it as an independent agent. Keep three physically separate roots:

```text
Hermes root:        ~/.hermes
External agent root: ~/PilotDeckAGI or another explicit non-Hermes root
Bridge root:        ~/AgentBridge or another explicit neutral exchange root
```

The bridge is the only shared exchange layer. It may write snapshots, inbox/outbox messages, learning proposals, and health reports under its own root, but it must not silently write back into either agent core.

## Migration/implementation checklist

1. Stop old processes running from mixed paths.
2. Move external repo/config/state out of `~/.hermes/workspace` into the external agent root.
3. Move user-level runtime dirs such as `~/.pilotdeck` into the external agent root if they belong to that agent.
4. Patch configs/scripts so runtime state, memory, logs, and launch commands point to the external agent root.
5. Create bridge directories, for example:
   - `hermes_to_<agent>/`
   - `<agent>_to_hermes/`
   - `mutual_learning/`
   - `logs/`
   - `reports/`
6. Bridge protocol:
   - Hermes exports read-only capability/evolution snapshots.
   - External agent exports observed gaps, skills, and proposals.
   - Bridge compares and writes learning proposals only.
   - No automatic write-back to either core without explicit gate.
7. Verify physical isolation:
   - no external repo remains under `~/.hermes/workspace`
   - no external overlay/state remains under `~/.hermes/workspace`
   - no stray runtime dir remains in home root if moved under the external root
8. Verify external agent independently: config load, gateway/backend health, UI health if applicable.
9. Update Hermes manifest only as Hermes' observation of the bridge; create a separate manifest for the external agent if it needs its own AGI evolution ledger.

## Pitfalls

- Do not treat “external repo absorption” and “independent agent evolution” as the same deployment shape. Absorption may live under Hermes workspace; independent agents need physical isolation.
- Do not make `~/.hermes/workspace` the external agent’s default root just because it is convenient.
- Do not claim co-evolution if there is no bridge evidence: snapshot, proposal, health report, or audit trail.
- Keep GPT/Claude protocol discipline in the bridge/overlay if the external agent’s native provider runtime cannot support Responses API.
