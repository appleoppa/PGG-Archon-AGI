# run_conversation stage extraction gate lessons

## Context
During PGG Archon / Hermes-Agent evolution work, `agent/conversation_loop.py::run_conversation` was reduced through RC-S01 mechanical helper extraction. The user explicitly asked to make the step size larger, then asked whether the work was complete and instructed continuation if not complete.

## Durable workflow lesson
When a larger stage-level helper extraction moves already-characterized statements out of a fixed line window, contract gates may produce false `WATCH` states even when behavior is unchanged. Do not treat this as completion or failure without diagnosis.

Required pattern:
1. Re-run the read-only slicer/contract gate after every extraction.
2. If RC windows flip from `PASS` to `WATCH`, inspect the missing booleans and the AST signals before changing production code.
3. Distinguish behavior drift from window drift:
   - Behavior drift: required signal no longer exists anywhere or call ordering/side effects changed.
   - Window drift: signal moved into a helper or adjacent stage but is still called by `run_conversation` and covered by characterization tests.
4. For window drift, update the gate to accept both local-window signals and full-function/helper-call signals, but only after adding/keeping characterization tests for the extracted helper.
5. Re-run: RC-S01~RC-S09 contract gates, extraction readiness matrix, targeted pytest, py_compile, git diff --check, APEX-GOD health, and EVOLUTION_MANIFEST update.
6. Commit only the scoped files for the current extraction.

## User-facing completion language
For this class of work, never say the overall `run_conversation` governance is complete if only RC-S01 or a single stage is done. Use two status fields:
- Current closed loop: completed / not completed.
- Overall governance: completed / not completed.

If the current loop is complete but RC-S02+ remains untouched, say: current loop completed; overall governance not complete; continue only if the next step is low-risk and covered by gates.

## Boundary
This pattern does not authorize extracting RC-S02+ by default. RC-S02+ needs stronger behavior-level characterization and post-extraction regression before mutation.
