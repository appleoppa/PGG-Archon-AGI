# PilotDeck-style External Agent Repo Absorption Pattern

Use this note when absorbing an external agent platform into PGG Archon / Hermes as a second node or auxiliary AGI-like workspace.

## Durable lesson

When an upstream agent repo has its own provider runtime and it does not match Hermes model-protocol discipline, do **not** force all Hermes providers into the upstream native config. Keep the upstream app deployable with only protocol-compatible providers, then add a PGG overlay that calls Hermes providers through their correct protocol and writes evidence.

Example from PilotDeck absorption:

- Upstream native runtime supported OpenAI-compatible `chat/completions` and Anthropic `messages` style paths.
- Local Hermes GPT/Claude discipline required Responses API (`/v1/responses`), so GPT/Claude were kept out of native PilotDeck provider config.
- Native PilotDeck was configured only with chat-compatible providers.
- A PGG overlay script performed full multi-LLM audit by calling GPT/Claude through Responses API and DeepSeek/MIMO/other compatible channels through chat completions.
- Shared core state was synchronized as read-only snapshots rather than copied into upstream core files.

## Recommended sequence

1. Clone source under the workspace external-repo area; keep third-party code isolated.
2. Build and smoke-test upstream unchanged before modification.
3. Identify upstream provider protocols and compare against Hermes provider discipline.
4. If protocols conflict, use an additive overlay instead of patching the upstream runtime first.
5. Create a shared-context snapshot from:
   - `EVOLUTION_MANIFEST.json`
   - workspace `AGENTS.md`
   - runtime/core PGG skills
   - absorption/governance skills
6. Run all configured LLMs through the correct endpoints and save HTTP status, latency, endpoint, provider, hash, and sample.
7. Run a formula/evidence gate with explicit score and verdict.
8. Report honest blockers and defect deductions; do not inflate node status into full AGI.

## Implementation shape

- `shared_md/`: read-only Markdown/JSON snapshots of core PGG context.
- `audits/`: multi-LLM audit outputs and formula gate evidence.
- `bin/`: deterministic overlay scripts and start/health probes.
- `reports/`: user-facing status report with file hashes and caveats.

## Pitfalls

- Do not call GPT/Claude via `chat/completions` just because the upstream project expects OpenAI-compatible chat.
- Do not edit Hermes core scheduler/security boundary for an external repo absorption.
- Do not call a server health check an AGI completion; health only proves the service is alive.
- Treat contradictory model audits as evidence signals; if one LLM mischaracterizes the repo, record it as a defect/caveat rather than adopting it as fact.
- For Git LFS repos, a source-only audit may use LFS-smudge-disabled clone to inspect/build code, but report that media/demo assets may be pointer files and install/use Git LFS when those assets matter.
