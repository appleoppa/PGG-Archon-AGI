# 2026-05-29 PGG Archon runtime落地细节

## 本次形成的稳定做法

用户纠正点：**“学到就要落地使用”**。对 PGG Archon / AGI / 开智吸收类任务，不能止步于分析报告、代码文件或 Git 提交，必须进入本地可运行链路。

## 本地落地形态

- 运行入口：`~/.hermes/agent/pgg_archon_runtime_loop.py`
- 状态检查：`~/.hermes/agent/pgg_archon_module_status.py`
- Debate：`~/.hermes/agent/pgg_archon_debate.py`
- ECC：`~/.hermes/agent/pgg_archon_ecc.py`
- SQLite：`~/.hermes/agent/pgg_archon_sqlite_persistence.py`
- 数据库：`~/.hermes/data/pgg_archon.db`
- Skill入口：`~/.hermes/skills/pgg-archon-runtime/SKILL.md`

## 验证闭环

运行：

```bash
python3 ~/.hermes/agent/pgg_archon_runtime_loop.py "是否应将DSPy/AgentVerse吸收模式接入PGG Archon默认运行链路？"
```

应形成：

- 模块状态：6/6 Activated，0 Partial，0 Inactive；
- ECC 执行：`status=done`；
- Governance 审计记录：至少 2 条；
- SQLite 入库：`experiments` 增加一条 runtime loop 记录；
- `top_genes` 可返回 `ecc_separation`、`dspy_teleprompter`、`agentverse_critic_loop`。

## 关键坑

1. `pgg_archon_module_status.py` 不能用随机数模拟状态；必须用外部证据（文件、数据库、skill存在）判断。
2. 用户说“本地应用就行”时，不要提交/推送；如果误 commit，要撤销 commit 并清理仓库未跟踪复制件。
3. 联网状态要实际 `curl` 检查 GitHub/目标 API，不能凭上一轮结果或记忆判断。
4. SQLite seed 数据写入时，以模块函数为准：`add_skill(..., performance_score=...)` 后再 `update_skill(success_count=...)`；不是 `PGArchonDB` 类接口。
