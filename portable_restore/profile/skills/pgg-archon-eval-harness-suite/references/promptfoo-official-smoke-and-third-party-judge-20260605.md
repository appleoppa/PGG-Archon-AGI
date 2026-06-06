# Promptfoo official smoke + third-party judge pattern (2026-06-05)

## Trigger

Use when PGG Archon needs to move from internal/adapted benchmark evidence toward an external-framework evidence gate without overstating capability.

## Core lesson

A tiny official-framework smoke is useful as a **harness/runtime evidence gate**, not as an official public benchmark score. Keep three labels separate:

- `official_harness_smoke`: a real framework CLI ran, but task set is tiny/toy or custom.
- `adapted_external`: public external data or framework adapted into a local runner.
- `internal_frozen_smoke`: local task suite only.

Never convert any of the above into “official MMLU/GSM8K/LegalBench score” unless the upstream harness, task config, split, metric, sample count, and raw artifacts support that claim.

## Promptfoo minimal path that worked

1. Use `npm exec --package promptfoo@<version> -- promptfoo eval ...` when `npm install` is affected by `omit=["dev"]` or local `.bin` is absent.
2. Prefer `file://prompt.txt` over inline YAML prompt strings if promptfoo reports “There are no prompts”.
3. For Python providers, promptfoo timeout config is effectively milliseconds for the worker. Use values like `120000`, and inside the Python provider convert ms to seconds for `subprocess.run(timeout=...)`.
4. Set `PROMPTFOO_PYTHON` to the intended Python executable and `PROMPTFOO_DISABLE_TELEMETRY=1` for deterministic local smoke runs.
5. Wrap shell pipelines with `set -o pipefail`; otherwise `tee` can hide promptfoo non-zero exits.

## Known-good smoke shape

- `promptfooconfig.yaml`:
  - `prompts: [file://prompt.txt]`
  - `providers: [{ id: file://hermes_provider.py, config: { provider: gpt55_5yuantoken, model: gpt-5.5, timeout: 120000 } }]`
  - 2–20 simple assertions depending on budget.
- Python provider:
  - implements `call_api(prompt, options, context)`
  - calls real `hermes -z ... --provider custom:<provider> --model <model>`
  - records `returncode`, `latencyMs`, and boundary metadata.

## Third-party judge rule

Agnes/agents is held out as `third_party_audit_only`:

- allowed: read artifact paths, hashes, boundary statements, and audit for overclaim.
- forbidden: coding, routing, ordinary task solving, benchmark answer generation, or candidate optimization.
- if long evidence packets timeout, retry with a short packet containing only claims, artifact paths, hashes, and boundary. If still unavailable, mark `UNAVAILABLE_TIMEOUT`; never fabricate a PASS.

## Evidence artifacts to save

- framework report JSON
- raw run log
- normalized `official_harness_smoke_report.json`
- closure summary with SHA256s
- third-party audit JSON and raw response/log
- `EVOLUTION_MANIFEST.json` entry with explicit `WATCH`/boundary if sample is tiny

## Boundary wording

Use language like:

> Real promptfoo official CLI smoke with a custom Hermes provider; tiny/toy tests only; not an official public benchmark score, not L2/full AGI proof.
