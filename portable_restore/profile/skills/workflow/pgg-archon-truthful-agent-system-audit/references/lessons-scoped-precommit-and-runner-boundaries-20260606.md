# Scoped pre-commit + runner boundary lessons (2026-06-06)

Use this when closing PGG Archon/Hermes engineering work that spans multiple feature groups, provider runners, Web endpoints, or evidence artifacts.

## Durable lessons

1. **Group commits by semantic boundary, not by current git status**
   - Split work into bounded groups such as P1 manifest gate, P2 smoke tooling, P3 Router/Web, P4 Rust surfaces, P5 legal runner, P6 cleanup.
   - For each group: inspect diff → fix risks → run focused tests → real LLM/judge review when required → stage only approved files → commit → update manifest.
   - Never stage `workspace/`, package-manager noise, Rust build targets, or unrelated leftovers just because they appear in `git status`.

2. **Third-party judge providers are not ordinary processors**
   - If a model is reserved as third-party judge/auditor, block it at every ordinary execution boundary:
     - default provider pool excludes it;
     - explicit provider request fails closed or records non-participation;
     - Web/API validators reject it;
     - tests cover default exclusion and explicit rejection.
   - Record failures as ERROR/blocked/non-participating; do not call the judge as daily processing to make a run look complete.

3. **PASS counts must be recomputed from eligible rows**
   - Do not trust top-level `pass_count` supplied by a runner or prompt.
   - Only count rows that meet all eligibility predicates, e.g. `http_status == 200` + parsed output + deterministic score/verdict PASS.
   - `LOCAL_PRECHECK_ONLY`, timeout, HTTP failure, empty visible text, unparsed JSON, or executor error must not inflate pass rate.
   - Use denominator `items_total`, and expose `http_ok_rate` separately from `pass_rate`.

4. **Legal runners must carry a strict truth boundary**
   - Legal smoke/taskset runners are process-safety checks only.
   - They must not claim official LegalBench/LexGLUE results, legal correctness, court-ready deliverability, external submission approval, or AGI level evidence.
   - Prompts should require evidence-first answers, missing-material abstention, jurisdiction factor checklist, and claim-amount calculation ledger.

5. **Route policy telemetry needs versioned windows**
   - When changing OmniRoute intent/classification policy, emit `route_policy_version` in both route decision and mirror ledger.
   - Web metrics should expose both a rolling window and a `post_policy_window` filtered by the current policy version so stale mixed-window data is not overread.
   - Intent classification should be tested for ordering, e.g. legal/audit keywords before generic AGI architecture keywords when ambiguity exists.

6. **Repo-local artifact cleanup is part of completion**
   - If `workspace/` or similar evidence directories appear inside the source checkout, move them to `~/.hermes/workspace/.../held_untracked/` and write a small manifest instead of deleting blindly.
   - Add or update `.gitignore` for durable artifact patterns such as `workspace/` when appropriate.
   - Package-manager lock/workspace files that are untracked and unsupported by `package.json`/project policy should be held out and archived pending explicit need.

## Verification checklist

- `git diff --cached --name-only` contains only the scoped group files.
- Focused pytest/compile/build checks pass for the staged group.
- Explicit judge-provider rejection/default-exclusion smoke passes if provider policy changed.
- LLM review outputs are real; failed/time-out channels are marked ERROR or UNKNOWN, not converted to PASS.
- Manifest entry includes commit(s), tests, review results, evidence paths, and truthful boundary.
- Final `git status --short` is empty or every remaining line has an explicit hold/cleanup decision.
