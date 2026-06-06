# Profile bootstrap scripts — verified 2026-06-04

## When to use

A multi-profile Hermes deployment is missing or thin on per-profile lifecycle files. Typical audit signals:

- `profile_memory_md5_all_null` in the audit state card (every pgg-* profile's `MEMORY.md` hash is null because the file does not exist).
- `AGENTS.md` count is 0 or 1 (only `~/.hermes/hermes-agent/AGENTS.md`, no `~/.hermes/profiles/<each>/AGENTS.md`).
- One pgg-* profile's skill count is far below its siblings (e.g. 29 vs 88–95).

The fix is three small, idempotent scripts under `agent/scripts/`. They are designed to be run once per deployment, then re-runnable any time a new profile is added.

## Scripts and templates

`agent/scripts/seed_profile_agents_md.py`
- Writes `AGENTS.md` for each named profile from a bounded template.
- The template is a 1-page, 4–5 section document: identity + boundary, mandatory gate, behavior constraints, output discipline.
- Idempotent: skip if file already exists unless `--force`.

`agent/scripts/init_profile_memory.py`
- Initializes `MEMORY.md` from `SOUL.md` first non-blank line + skill count + `config.yaml` provider list.
- Idempotent: skip if file already exists unless `--force`. User edits take precedence over the bootstrap.

`agent/scripts/sync_profile_skills.py`
- Copies skill directories from a source profile to a target profile.
- Excludes by name substring (`--exclude`).
- Source must be a high-skill sibling (88–95), NOT `default` (typically ~5 in this deployment).
- Copy-only; never deletes the target's own skills.

`agent/scripts/templates/agents_md_template.md` and `memory_template.md`
- Both are short. Long templates become a context tax on every profile request.

## Run order

```bash
cd ~/.hermes/hermes-agent
python3 -m agent.scripts.seed_profile_agents_md \
  --profiles default pgg-zhixing pgg-xingshi pgg-minshi pgg-zhengju pgg-zhinao \
               pgg-anguan pgg-feisu pgg-guwen pgg-shenji pgg-tuiyan pgg-xunshi \
  --template agent/scripts/templates/agents_md_template.md

python3 -m agent.scripts.init_profile_memory \
  --profiles pgg-zhixing pgg-xingshi pgg-minshi pgg-zhengju pgg-zhinao \
               pgg-anguan pgg-feisu pgg-guwen pgg-shenji pgg-tuiyan pgg-xunshi \
  --template agent/scripts/templates/memory_template.md

python3 -m agent.scripts.sync_profile_skills --target pgg-zhixing --source pgg-xingshi
```

The order matters only loosely: AGENTS.md and MEMORY.md are independent; skills sync may be skipped entirely if the audit is satisfied with the existing profile specialization.

## Verification

```bash
echo "AGENTS.md count: $(ls -1 $HOME/.hermes/profiles/*/AGENTS.md 2>/dev/null | wc -l)"
echo "MEMORY.md count: $(ls -1 $HOME/.hermes/profiles/*/MEMORY.md 2>/dev/null | wc -l)"
for p in $HOME/.hermes/profiles/pgg-*/MEMORY.md; do md5sum "$p"; done | wc -l
```

The expected count is the live profile list, not a hardcoded constant. `ls ~/.hermes/profiles/ | wc -l` should match the AGENTS.md count exactly.

## Pitfalls observed in this deployment

- **`default` is intentionally small (~5 skills).** Reading `default` skill count as the "expected" baseline for pgg-* is a mis-anchor. Compare pgg-* against pgg-*; compare `default` separately. The audit state card should report both numbers; the verdict on whether to sync depends on the pgg-* baseline.
- **pgg-zhixing is a knowledge-center profile (Apple 智脑).** Its 29-skill baseline is closer to a specialist than the cross-department profiles. The audit decision on whether to sync depends on whether the user wants all 12 pgg-* profiles to share a common skill floor or preserve their specialization. The 2026-06-04 round synced it from pgg-xingshi (88), bringing it to 90, on the user's instruction.
- **Idempotency tests must be re-runnable.** Re-running `init_profile_memory.py` on an existing file must report `SKIP` and not overwrite. If your script overwrites silently, user edits are lost.
- **A verbose AGENTS.md is a tax.** Keep it under 1 KB. Identity + boundary + one gate section + one behavior section + one output section.
- **Don't put secrets in any of these files.** AGENTS.md and MEMORY.md are read on every profile request; if the template includes a placeholder for an API key, the key will eventually leak into the file.
- **The `comm -23` check (which skills are in source but not in target) is the right smoke test** before re-running sync; it shows you what *would* be added.

## Verified evidence (2026-06-04)

- AGENTS.md: 12/12 pgg-* profiles + default = 13/13.
- MEMORY.md: 12/12 pgg-* profiles + default = 13/13.
- pgg-zhixing skills: 29 → 90 (synced from pgg-xingshi, 88 → 90 after copy).
- pgg-law (an audit-discovered profile not in the original list): AGENTS.md and MEMORY.md generated with `--force`; skills left untouched (88, already at parity).
- Re-running `init_profile_memory` on an existing file produced `SKIP`, not overwrite. Idempotency confirmed.
- One follow-up commit: `8dfb83cc2 P1: profile bootstrap scripts and templates (AGENTS, MEMORY, skills sync)`.

## Commit hygiene

Add the three scripts and the two templates in one commit. Do not mix the AGENTS.md / MEMORY.md / skills changes themselves with the script code in the same commit — that way the scripts are reviewable independently from the per-profile mutations they produced.

## Related

- `hermes-config-runtime-diagnosis` SKILL.md — main "Profile bootstrap pattern" section.
- `references/launchd-plist-env-injection-2026-06-04.md` — sibling pattern for env injection.
- `pgg-archon-truthful-agent-system-audit` — audit state card structure that surfaces these gaps.
