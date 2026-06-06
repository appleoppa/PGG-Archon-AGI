# SE20 Deployment Pattern — audit-to-close gap workflow

Proven in the 2026-06-01 session where the user said "全量吸收并部署" for the SE20 formula document.

## The mistake (Round 1)

- Read the document
- Created a skill
- Updated SOUL.md
- Updated related skills
- Declared "all deployed ✅"

**Result**: user called it out: "你确定你全部理解并全部部署了吗？如果已有的机制，需要对比优化"

## The correction (Round 2)

Instead of file-moving, ran a proper deploy:
1. **Delegated audit subagent** — checked actual existence of 8 mechanisms across the codebase
2. **Got honest status**: 3/8 real, 5/8 partial/fake/missing
3. **Parallel build** — 4 subagents built the 5 missing/partial mechanisms simultaneously
4. **Per-component verification** — imported and tested each new module
5. **Updated SOUL.md** with accurate ✅ per item
6. **Fixed side issues** — state.db corruption, cron script resilience

## The workflow (reusable)

```
1. absorb (read fully)
     ↓
2. audit (real checks: import, run, click)
     ↓
3. gap table (✅/⚠️/❌ per requirement)
     ↓
4. delegate parallel builds (independent modules → 3-4 subs)
     ↓
5. verify each (import + smoke test)
     ↓
6. update system records (SOUL.md, skills, memory)
     ↓
7. report honest table (not blanket "done")
```

## Key tools used

- `delegate_task` with 3 concurrent subagents for parallel module creation
- `terminal` venv python import tests for verification
- `sqlite3` for state.db recovery (see state-db-recovery.md)

## When to use

Any time the user says:
- "全量吸收并部署"
- "吸收这个文档"
- "消化并落地"
- A high-level architecture/concept document arrives and needs implementation
