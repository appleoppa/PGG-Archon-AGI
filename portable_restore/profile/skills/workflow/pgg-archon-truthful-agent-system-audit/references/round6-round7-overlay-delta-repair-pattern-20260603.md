# Round6/Round7 overlay + fresh ΔE repair pattern (2026-06-03)

## Trigger

Use when a PGG Archon / APEX audit finds any of these:

- `agent.pgg_archon_*` or `agent.apex_*` modules import-fail while historical reports claim they existed.
- `apex_god/` or PGG overlay files are present but ignored by `.git/info/exclude`.
- A ledger/tool action reports a high readiness/ΔE while a fresh Rust `py_evaluate()` run reports a much lower score.
- `apex_god.auto_bootstrap` logs missing compatibility exports or missing dependencies.

## Core lessons

1. **Do not treat ignored overlay as ordinary untracked code.**
   - Check `git status --short --ignored=matching -- apex_god agent/pgg_archon_*.py agent/apex_*.py`.
   - Check `git check-ignore -v <path>`.
   - If `.git/info/exclude` excludes the overlay, do not bulk `git add` or delete it. First classify: runtime compatibility / archive / candidate tracking / delete candidate.

2. **Import fix must be honest compatibility, not fake restoration.**
   - If historical `pgg_archon_debate.py`, `pgg_archon_ecc.py`, `pgg_archon_module_status.py` source cannot be found, do not create empty stubs that pretend old 400-line modules are restored.
   - Create bounded read-only compatibility surfaces that say exactly what they do:
     - module status import probe;
     - supplied-position debate summary without LLM calls;
     - supplied-signal ECC defect deduction without auto-repair.
   - Add explicit boundary fields: not full AGI, not old full module, not external benchmark, no autonomous model participation unless provider evidence exists.

3. **Commit only minimal trackable fixes.**
   - Safe example: add only three new compatibility files if they are not ignored and tests pass.
   - Do not mix ledger/report/workspace artifacts into the code commit.
   - Do not half-commit files inside an ignored overlay directory such as `apex_god/` when the rest of that directory remains ignored and required by imports.

4. **Fresh Rust ΔE path mismatch diagnosis.**
   - Read the Rust evaluator source before guessing. In this session `src/eval.rs` expected:
     - `workspace/evolution/*.json` evidence count;
     - `workspace/evolution/super_evolution13/source_scout.json`;
     - `workspace/evolution/super_evolution13/evol_events.jsonl`.
   - Existing 6.3 artifacts under `artifacts/`, `github_scout/`, `round*_llm_calls/`, `*.stdout`, `*.md` were real but not under the evaluator’s expected path.
   - Fix by creating truthful index/pointer files under the expected path, derived from existing artifacts, with boundaries such as “index of existing artifacts; not a new web search” and “pointer to existing artifact; not fabricated evidence.”

5. **Do not fake β·Ω/Rust-native score.**
   - If `find venv/.../site-packages -name 'hermes_*.so'` shows one real Rust module, β·Ω should remain `0.25` under a 4-module evaluator formula.
   - Improve by building/installing real Rust modules or revising the evaluator’s scoring rubric, not by creating fake `.so` placeholders.

6. **Bootstrap overlay repair boundary.**
   - If `apex_god.__init__` is empty and `auto_bootstrap` expects `activate_force_inherit`, it is acceptable to add a compatibility export that delegates to `force_inherit.get_formula_preamble()` and `get_calculator()`.
   - If `apex_god.egress_guard` is missing, do not create a fake socket blocker. A compatibility module should return `watch_compat_no_enforcement`, `blocked_hosts: 0`, `side_effects: none`, and a clear boundary.

7. **Dependency-chain repair pattern.**
   - Health checks may reveal one missing package at a time (`numpy` → `networkx` → `rank_bm25`, etc.). Install real dependencies and rerun health until no import gap remains.
   - Capture the installed versions in evidence, but do not turn one machine’s missing packages into a permanent negative rule.

## Verification bundle

Minimum verification before claiming repair:

```bash
python -m py_compile <changed_files>
python - <<'PY'
import importlib, json
mods = ['agent.pgg_archon_module_status', 'agent.pgg_archon_debate', 'agent.pgg_archon_ecc']
print(json.dumps([{m: bool(importlib.import_module(m))} for m in mods]))
PY
python -m pytest tests/test_anti_hallucination_e2e.py -q
python - <<'PY'
import hermes_apex_evolution as m
m.py_evaluate('<workspace>', '<out.json>')
PY
```

Also read back:

- code commit or explicit “not committed because ignored runtime overlay” rationale;
- evidence JSON SHA256;
- ledger update;
- `EVOLUTION_MANIFEST.json` update.

## Reporting wording

Use `PASS_WITH_BOUNDARY` when import/path/bootstrap repair passes but capabilities are bounded.

Required boundary lines:

- “read-only compatibility surface; not restoration of old full module”;
- “fresh ΔE is internal process score, not external AGI benchmark”;
- “egress guard compatibility reports WATCH/no enforcement unless a real blocker is implemented”;
- “β·Ω remains low if only one real Rust `.so` exists.”
