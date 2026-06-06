# APEX Repo Unlock Audit Pattern

## Trigger

Use when the user asks to inspect a local APEX / evolution resource repository and identify modules that are not yet unlocked, absorbed, or deployed in PGG Archon / APEX-GOD.

## Workflow

1. **Path correction first**
   - Check the exact user path and likely macOS aliases (`~/文稿` vs `~/Documents`).
   - If the given path is absent but a likely canonical path exists, state the correction clearly.

2. **Inventory the repo set**
   - List top-level repos, key files, language mix, git status when applicable.
   - For each repo, separate README claims from code and tests.

3. **Run bounded verification**
   - Prefer existing tests in temporary or read-only-safe execution.
   - Record real results, e.g. passed counts, import failures, compile errors.
   - Do not treat a script printing “全部就绪” as success if substeps failed.

4. **Compare against current APEX-GOD / PGG Archon**
   - Read the unified manifest / current capability surface.
   - Mark each candidate as:
     - `PASS`: implemented and verified by tests/readback.
     - `WATCH`: useful implementation exists but integration or boundary is incomplete.
     - `BLOCKED`: compile/import/path/dependency/security issue prevents truthful unlock.

5. **Classify unlock candidates**
   - `P0`: low-risk, high-value, test-backed modules that can become sidecar/scanner/measurement extensions.
   - `P1`: valuable chains needing path/package/validation fixes.
   - `P2/P3`: domain adapters, dashboards, experimental formulas, or provenance extras.

6. **Use real model audit only if claimed**
   - For AGI/APEX/PGG architecture judgments, call configured GPT/Claude providers through Responses API if stating multi-model audit.
   - Keep provider evidence brief; do not paste secrets.

## Common APEX unlock signals

- `Σ_memory`: existing memory may be strong, but a dedicated memory quality scoring module is separate.
- `τ_trace`: audit logs/receipts are not the same as explicit `(Decision + Reason + Result)/3` process scoring.
- Code quality formulas: passing formula tests do not mean project-wide scanner integration.
- Gene → Skill → SelfCheck: package naming and gene source paths often need parameterization.
- DeltaG / constraint engines: absorb formula and boundary gates, not false success wording.
- V10.3 self-loop: Python formulas can be candidates; Rust compile failures keep production unlock blocked.

## Pitfalls

- Do not restore intentionally uninstalled sidecars or mirrors while auditing missing modules.
- Do not conflate upstream repo passing tests with APEX-GOD integration.
- Do not call a domain-specific adapter (e.g. quant scoring) a core AGI module without a general-purpose interface and tests.
- Do not core-mutate Hermes scheduler/main loop/security boundary during unlock audit.

## Output contract

Return:

- corrected path;
- repo inventory;
- verification evidence;
- current APEX-GOD comparison;
- P0/P1/P2/P3 unlock list;
- PASS/WATCH/BLOCKED status;
- report path + hash if a report is written.
