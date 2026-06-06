---
name: continuous-auto-iteration-limit
description: 用户授权的连续自动迭代规则：评分>75%且低风险可回滚时，单次最多连续推进10轮，超过10轮启动执行部/专门流程。
version: 1.0.0
created: 2026-06-01
---

# Continuous Auto Iteration Limit — Compact

## Trigger

Use when user authorizes continuing automatically and next low-risk step has score >75.

## Rule

Proceed without asking for each step when reversible, safe and verifiable. Single continuous run is capped at 10 rounds; beyond that start/coordinate execution department or ask for explicit renewal.

## Workflow

After each round: verify, score next step, continue if >75, otherwise report blocker/decision point.

### Activation Sequence Discipline (2026-06-02)

When activating new components/modules, follow this strict sequence — **never** activate multiple at once:

1. **One at a time**: Activate exactly one component per round
2. **Debug smooth**: Run tests → verify system load/health → confirm no regression
3. **Compatibility check**: After activation, verify existing tests still pass and system load is stable
4. **Commit close**: Code + tests + integration + commit — fully close the component
5. **Then next**: Only proceed to the next component after the current one is fully closed

**Don't stop mid-activation.** If the current component is not fully wrapped (code written but tests not run, or tests pass but not integrated), do not stop and ask. Complete it. Only stop when the component is fully closed OR a genuine blocker is hit.

### System Impact Verification

After each activation, verify all of these before proceeding:

```
✓ Unit tests pass (new + existing regression)
✓ Health check runs clean (count should increase by 1)
✓ System load stable (< 3.0 load average typical)
✓ Daemons running (ARS, AutoLoop, gateway)
✓ Git clean (committed)
```

### What NOT to do

```
✗ Activate 3 modules at once without debugging
✗ Leave incomplete code + tests uncommitted
✗ Skip compatibility/regression check
✗ Stop mid-task to ask "should I continue" when >75
✗ Move to next component before current is fully closed
```

## References

- `references/activation-sequence-example-20260602.md` — full session transcript covering all 8 modules of successful sequential activation (DeltaG→CodeGenesis→MemoryTrace→V10.3→SkillHealth→DoubtGamma→PlanningRunner→SchemaValidator)
- Full policy archived at `references/full-skill-archive-20260601.md`
