# 33-card final ACTIVE sync lesson — 2026-06-04

## Scope

Class-level lesson for PGG Archon / Apple Didi super-evolution 33-card closure:

真实代入 → 短板暴露 → 吸收补齐 → lane 集成 → 5-LLM 复核 → manifest final key。

This is not a one-off narrative; it is a reusable pattern for any future status-card / surface-card closure task.

## Reusable pattern

1. Read the latest aggregated card JSON and list all non-ACTIVE rows.
2. Distinguish real capability gaps from mapping/sync gaps:
   - real gap: no surface module, no state/log file, no test;
   - sync gap: surface exists but card id does not match the patch key.
3. For each real gap, add a 4-probe surface module:
   - module importable;
   - state/log file present;
   - env/version gate present;
   - domain-specific evidence exists.
4. Add a deterministic bootstrap script only for state/log evidence that is safe, local, and reversible.
5. Add/patch `se_sync` to aggregate surfaces into the 33-card view.
6. Normalize ids in sync logic before comparing:
   - `str(raw_id)`;
   - if string starts with `file_`, also compare `raw_id.removeprefix("file_")`;
   - handle ids such as `2.5a`, `2.5b`, `16.5` as strings.
7. Run tests for both surface and sync.
8. Run lane (`super_evolution_lane`) so the sync is not a separate manual afterthought.
9. Run 5-LLM audit excluding Claude when instructed.
10. Read back final JSON before reporting completion:
    - `status_distribution`;
    - `provider_success`;
    - `not_active` list;
    - commit hash;
    - manifest final key.

## Critical pitfall: id mismatch can masquerade as capability gap

In the final 33-card closure, multiple surfaces were already real, but the card stayed SKELETON/ABSENT because IDs did not match:

- integer ids in report: `17`, `22`, `4`, `8`;
- prefixed id: `file_1`;
- split ids: `2.5a`, `2.5b`;
- decimal ids: `16.5`.

A future agent must inspect the actual aggregated JSON shape before creating more modules. Otherwise it may duplicate already-working surfaces.

## Final verification shape used

Final readback shape:

```text
status_distribution {'SKELETON': 0, 'ABSENT': 0, 'PARTIAL': 0, 'ACTIVE': 33}
provider_success {'deepseek': 33, 'gpt55': 33, 'agnes': 32, 'mimo': 33, 'minimax': 33}
not_active []
```

Provider verdicts are not automatically homogeneous. A final state can be complete for status-surface closure while still preserving provider-specific WATCH/ERROR details.

## Boundary language

When reporting this class of completion, say:

- “33-card status surface full ACTIVE”;
- “not full AGI”;
- “Claude excluded by instruction”;
- “MiniMax parse failure/ERROR is preserved if present, not upgraded to PASS.”

Do not say “full AGI”, “zero risk”, or “all providers PASS” unless the readback says exactly that.
