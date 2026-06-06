# 终极进化公式 Phase11 — Gene Lifecycle & Promotion Chain

## 目的

在 PGG DB 中建立基因生命周期状态机（`gene_lifecycle`）和晋升链追踪（`promotion_chain`），解决基因无显式生命周期管理、晋升链无法溯源的问题。

## 解决的问题

- Phase3-10 基因已入库但无状态追踪
- 无法知道哪个基因处于 `candidate / active / promoted / archived / retired` 状态
- 晋升依赖人工判断，无链式记录
- 基因何时激活、何时晋升为 active、何时 archive，无审计轨迹

## Schema

### gene_lifecycle 表

| 列 | 类型 | 说明 |
|---|---|---|
| gene_id | INTEGER PRIMARY KEY | 关联 genes.id |
| state | TEXT | candidate / active / promoted / archived / retired |
| candidate_at | TEXT | 进入 candidate 时间 |
| activated_at | TEXT | 进入 active 时间 |
| promoted_at | TEXT | 进入 promoted 时间 |
| archived_at | TEXT | 进入 archived 时间 |
| retired_at | TEXT | 进入 retired 时间 |
| quality_score | REAL | 从 genes 表同步 |
| parent_gene_id | INTEGER | 父基因（用于谱系追踪）|

### promotion_chain 表

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PRIMARY KEY | 自增 ID |
| gene_id | INTEGER | 关联 genes.id |
| from_state | TEXT | 迁移前状态 |
| to_state | TEXT | 迁移后状态 |
| transitioned_at | TEXT | ISO 时间戳 |
| trigger_phase | TEXT | 触发阶段（如 phase5_promotion_gate）|
| decision | TEXT | 晋升决策（如 allow_candidate_promotion）|

## 迁移安全

`_ensure_lifecycle_schema()` 需处理旧 schema 已存在但列不完整的情况：

```python
# 旧表可能缺少 candidate_at 等列，需要 ALTER TABLE 增量迁移
for col in ["candidate_at", "activated_at", "promoted_at", "archived_at", "retired_at"]:
    try:
        conn.execute(f"ALTER TABLE gene_lifecycle ADD COLUMN {col} TEXT")
    except sqlite3.OperationalError:
        pass  # 列已存在，跳过
```

**教训**：Phase11 首次运行时 `gene_lifecycle` 表已存在（Phase10 遗留），但旧表缺少 `candidate_at` 列导致 INSERT 失败。解决方案是 `CREATE TABLE IF NOT EXISTS` + 增量 `ALTER TABLE ADD COLUMN` 迁移，而不是重建表。

## 状态转换规则

- 所有新基因首次入库时为 `candidate`
- Phase5 promotion_gate 触发 `candidate → active` 转换
- `active → promoted` 由更高阶晋升 gate 触发
- `archived` / `retired` 为终态

## 关键函数

- `_ensure_lifecycle_schema()` — 建表 + 增量迁移
- `_build_phase11_lifecycle_report()` — 采集当前状态
- `persist_phase11_to_pgg_db()` — 入库 + 晋升 Phase5 基因到 active
- `build_phase11_lifecycle_gate()` — 评估门禁决策
- `write_phase11_report()` — 写 workspace JSON 报告
- `run_phase11_cycle()` — 完整周期执行

## Phase11 Gate 门禁逻辑

```python
def build_phase11_lifecycle_gate(lifecycle_report):
    orphan_blockers = [o["name"] for o in orphans if "phase" in o["name"]]
    if orphan_blockers:
        decision = "block_orphan_genes_not_enrolled"
    else:
        decision = "allow_lifecycle_chain_active"
```

blockers=[] 时决策为 `allow_lifecycle_chain_active`。

## cron wrapper 接入

```bash
"$PYTHON" scripts/run_pgg_ultimate_evolution_ars_cycle.py \
  --persist --phase4 --phase5 --phase6 --phase7 --phase8 --phase9 --phase11
```

## 验证命令

```python
import sqlite3
conn = sqlite3.connect(os.path.expanduser("~/.hermes/data/pgg_archon.db"))
c = conn.cursor()
c.execute("SELECT gene_id, state, candidate_at, activated_at FROM gene_lifecycle ORDER BY gene_id")
print(c.fetchall())
c.execute("SELECT id, gene_id, from_state, to_state, transitioned_at FROM promotion_chain")
print(c.fetchall())
conn.close()
```

## 与 Phase5 的关系

Phase5 是 promotion gate（决策），Phase11 是 promotion chain（执行追踪）。Phase5 的 `allow_candidate_promotion` 决策写入 `promotion_chain`，由 Phase11 的 `persist_phase11_to_pgg_db()` 执行状态转换。

## 边界

- 不修改 `run_agent.py`
- 不读取或暴露 secret
- 不部署
- 不 git push
- 只操作 `~/.hermes/data/pgg_archon.db` 中的新建表
