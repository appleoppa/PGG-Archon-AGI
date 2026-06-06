# Round6 Provider Audit + Compatibility Shim Pattern (2026-06-03)

## When to use

Use this pattern when a PGG Archon / Hermes audit reports missing historical modules, untracked/ignored overlays, or multi-model audit participation issues.

## Key lessons

### 1. Current chat model ≠ independent provider audit call

If the active session model is GPT/Claude, that only proves the host conversation channel is working. It does not prove an independent audit call through the local configured provider works.

For audit evidence, distinguish:

- Current session main model: the model serving the user conversation.
- Independent provider audit call: a separate HTTP/API call through configured provider, endpoint, model, and API mode.

Report failures precisely, e.g.:

> Current chat model GPT-5.5 is working, but the independent `gpt55_5yuantoken` Responses API audit call returned HTTP 502, so no independent GPT audit text was obtained.

Do not use the current conversation model's own answer as a substitute for independent multi-model audit evidence.

### 2. Do not restore missing historical modules blindly

If historical modules such as `agent.pgg_archon_module_status`, `agent.pgg_archon_debate`, or `agent.pgg_archon_ecc` are missing:

1. Search current tree, workspace, and backups for real source.
2. Check whether newer modules replaced them.
3. If no source exists, do not create empty stubs that pretend old capability was restored.
4. Prefer read-only compatibility surfaces with explicit boundaries:
   - module status/importability report;
   - supplied-position debate summary that does not call LLMs;
   - ECC defect-deduction evaluation over caller-supplied signals.
5. Name the boundary in code and reports: compatibility surface only, not restoration of historical full module, not autonomous multi-agent execution.

### 3. Ignored overlay governance

A clean `git status --short` can hide important PGG/APEX overlays if `.git/info/exclude` ignores them. Always check:

```bash
git status --short --ignored=matching -- apex_god agent/pgg_archon_*.py agent/apex_*.py
git check-ignore -v apex_god/health.py agent/apex_runtimeos_sequence.py 2>/dev/null || true
git ls-files apex_god agent/pgg_archon_*.py agent/apex_*.py | wc -l
```

Classify ignored overlays before acting:

- runtime/historical overlay to preserve;
- candidate for version control;
- archive candidate;
- delete candidate only after content review.

Never bulk-add or bulk-delete `apex_god/` or `agent/pgg_archon_*.py` just because an audit flagged them.

### 4. Minimal commit discipline

When adding compatibility surfaces, commit only the new narrow files. Do not mix in ledgers, reports, ignored overlays, generated artifacts, or unrelated changes.

Verification minimum:

```bash
python -m py_compile agent/pgg_archon_module_status.py agent/pgg_archon_debate.py agent/pgg_archon_ecc.py
python - <<'PY'
import importlib
for m in ['agent.pgg_archon_module_status','agent.pgg_archon_debate','agent.pgg_archon_ecc']:
    importlib.import_module(m)
    print(m, 'OK')
PY
python -m pytest tests/test_anti_hallucination_e2e.py -q
```

Then update the PGG core ledger and `EVOLUTION_MANIFEST.json` with:

- commit hash;
- fixed imports;
- verification outputs;
- evidence path + sha256;
- boundary statement.

## Reporting language

Use `PASS_WITH_BOUNDARY` when imports/tests pass but capability is intentionally limited. Do not say `restored full debate/ECC` unless the original functional module is recovered and tested.
