# Core-mode landing pattern for open-source legal learning

## When to use

Use when the user asks to not only create/update the `open-source-legal-learning` skill, but to “落地 / 融合进核心 / 固化到核心”. In this class of task, a SKILL.md alone is insufficient evidence.

## Required landing layers

1. **Skill layer** — `open-source-legal-learning` exists with trigger phrases and workflow.
2. **Rust manifest layer** — add a Rust-owned `CoreLearningMode` (or equivalent) in the Reasonix/APEX fusion crate so the trigger is visible in generated manifest, not only in prose.
3. **Test layer** — add a unit test proving:
   - mode id is present, e.g. `OPEN_SOURCE_LEGAL_LEARNING`;
   - trigger phrase includes `进行开源法律学习`;
   - execution sequence includes GitHub law/legal topic search;
   - Rust gates include `cargo test`;
   - manifest update target includes `EVOLUTION_MANIFEST.json`;
   - truth boundary remains additive/no scheduler-security mutation.
4. **Build layer** — run `cargo fmt`, `cargo test`, `cargo build --release`.
5. **Evidence layer** — create the evidence directory before redirecting generated manifest; otherwise shell redirection fails even when tests/build pass.
6. **Unified manifest layer** — update and read back `~/.hermes/data/EVOLUTION_MANIFEST.json` using a stable key such as `latest_open_source_legal_learning_core_mode`.
7. **Report layer** — write a compact report under `~/.hermes/workspace/` evidence/governance area.

## Proven Rust fields

A core-mode record should preserve at least:

- `id`
- `trigger_phrases`
- `skill_name`
- `skill_path`
- `execution_sequence`
- `core_formula_binding`
- `rust_gate`
- `manifest_update`
- `truth_boundary`

## Pitfalls

- “Skill created” is not enough when the user says “融合进核心”. It must be visible in Rust-generated manifest and unified manifest readback.
- If manifest generation redirects to a nested evidence path, create the directory first (`mkdir -p ...`) before running the binary.
- Treat `cargo test`/`cargo build` PASS plus redirection failure as partial: build succeeded, evidence write failed. Fix the directory and rerun manifest generation/readback before claiming DONE.
- Do not modify Hermes scheduler/security boundary for this landing. Keep it as additive Rust-owned governance mode unless explicitly authorized.

## Completion evidence contract

Final reply should include: Rust test count, release build status, generated manifest path/hash, EVOLUTION_MANIFEST readback status, report path, and boundary statement.
