# SE20 continuous evolution hardening notes

## Trigger

Use during PGG Archon / SE20 / 全量进化 continuation runs where the working tree may already contain generated or sibling-agent changes.

## Durable lessons

1. Start by reading `git status --porcelain` and inspecting uncommitted diffs before choosing the next increment. Do not assume the previous turn left a clean tree.
2. If a file contains an unverified audit score or model-audit claim, either verify by a real provider trace or remove/hold the claim. A manifest line that says GPT/Claude audited is not evidence by itself.
3. For health/CLI readback that can emit stderr/log noise, persist stdout/stderr separately and parse from the first JSON object rather than using a fragile pipe.
4. Network side effects in health/alert cycles must be opt-in. Default alert managers should log locally unless the caller explicitly enables a provider or environment flag.
5. Commit discipline for continuation runs: stage only verified files for the current increment, run `git diff --cached --check`, commit locally, then verify `git status --porcelain` is clean or explicitly explain any remaining intentional local change.

## Verification pattern

- Targeted tests for new/changed modules.
- Import smoke for new SE20 modules.
- Runtime readback for `se20.health` or `se20.evolution_manifest` when those surfaces are changed.
- Local commit only; no push/PR unless explicitly authorized.
