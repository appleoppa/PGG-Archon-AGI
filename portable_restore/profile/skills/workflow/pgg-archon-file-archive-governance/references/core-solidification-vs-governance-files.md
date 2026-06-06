# Core solidification vs governance files

Use when a user asks whether file/storage rules are truly "固化进系统核心".

## Durable lesson

Do not equate "rule file exists" or "skill updated" with core solidification. For Hermes/PGG Archon file governance, distinguish four levels:

1. Governance artifacts only
   - `workspace/治理/*.md`, INDEX, manifest, audit report.
   - Useful, but not automatically loaded into the active agent prompt.

2. Skill-level reuse
   - Umbrella skill and `references/` detail.
   - Reusable when the skill is loaded, but still not guaranteed to affect every new session unless matching skill is selected.

3. Prompt/context core layer
   - Default-profile `~/.hermes/SOUL.md` for identity/stable prompt.
   - Relevant project/workspace `AGENTS.md` for context rules when that cwd is active.
   - This is the minimum needed before saying rules are embedded into the current agent's operational core.

4. Tool-level hard guard
   - Code-level pre-write/pre-patch path validation or policy enforcement.
   - Only this level can automatically block wrong-path writes by tools. Do not claim it exists unless implemented and tested.

## Required answer discipline

If the user challenges "是否已经固化进系统核心？":

- First admit the exact level already reached.
- If only governance files/skills exist, say "not yet core" and immediately patch the prompt/context layer when low risk.
- After patching, verify via actual prompt/context loading, not by inspecting files alone.
- Still state the boundary: prompt/context solidification is not the same as tool-level write interception.

## Verification pattern

Use Hermes prompt builder or equivalent to verify:

- `load_soul_md()` contains the governance rule phrase and rule-file links.
- `build_context_files_prompt(<relevant cwd>, skip_soul=True)` contains `AGENTS.md` governance contract.
- Clean generated `__pycache__`/`.pyc` afterward if the file-governance task requires a noise-free final state.

## Good wording

"已进入 prompt/context 核心层，但还不是 tool-level guard（工具级写入拦截器）。"

Avoid:

"已经固化进核心" when only reports, INDEX files, or skills were written.
