# AGI Runtime Repair Cross-Model Audit

Use this reference when repairing local PGG/Hermes/AGI runtime overlays, provider interception, or multi-agent orchestration code and the user asks for GPT/Claude verification.

## Trigger

- Runtime audit or repair involves untracked overlay files (`apex_god/`, `agent/pgg_archon_*`, local profile IPC, etc.).
- GPT/Claude must independently review the fix.
- Provider monkeypatch / SDK interception / reversible patching is part of the repair.

## Procedure

1. **Reproduce with tests first**
   - Run targeted tests that expose the failure.
   - Capture exact failing assertions or import errors.

2. **Read the failing contract**
   - Read the test file and implementation around the missing symbol/import path.
   - For package import failures, distinguish `import agent.module` from legacy direct-script imports.

3. **Consult models with usable evidence**
   - If files are untracked, `git diff` may be empty. Do not treat empty diff as proof of no change.
   - Send GPT/Claude:
     - P1 problem statement;
     - extracted code snippets around changed symbols;
     - actual test output;
     - relevant smoke-test output.
   - If an LLM says "cannot judge because no diff/code", rerun with snippets.

4. **Provider monkeypatch repair contract**
   - Preserve original callable references before wrapping.
   - Make `patch_all()` idempotent.
   - Make `unpatch_all()` restore the exact original callables.
   - If constructor patching is used, preserve and restore original constructors in a separate full reset path.
   - Align public state probes such as `is_patched()` with all patch modes.
   - Test both replacement and restoration, not just importability.
   - Warn on SDK version mismatch; do not fail closed solely because a version is outside the preferred range.

5. **Import-path repair contract**
   - Prefer package-relative imports inside packages, e.g. `from .profile_messenger import ...`.
   - Keep legacy fallback only if there is a real direct-script/test path.
   - Guard broad `ImportError` fallbacks so they do not mask missing dependencies inside the imported module.

6. **Verification gates**
   - `py_compile` on changed files.
   - Targeted pytest for the failed contract.
   - Import smoke for the repaired modules.
   - Runtime health/readback if the repair affects an active gateway or watcher.
   - State/manifest update only after tests pass.

## Reporting

Report scores as bounded runtime/process scores unless an external AGI benchmark actually ran. Separate:

- process/service availability;
- component import/structure;
- targeted regression tests;
- provider stability;
- multi-agent/legal orchestration;
- governance/version-control hygiene.

Do not call untracked-file repair fully governed until version-control status is resolved or explicitly accepted as an overlay boundary.
