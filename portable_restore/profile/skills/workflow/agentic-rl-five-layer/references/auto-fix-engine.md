# AutoFixEngine — Layer 5 闭环自省实用实现

从 nanoGPT-claw (Rust) 项目吸收模式，在 Hermes Python 中实现的自动化修复闭合回路。

## 核心循环

```
execute → score → fix → re-verify（最多 3 次）
```

每次循环包含：
1. **execute**：运行命令（subprocess.run）
2. **score**：退出码 + stderr → 0.0–1.0 评分
3. **fix**：评分 < 0.8 → 触发启发式修复
4. **re-verify**：再次执行检查

## 8 种启发式修复

| 触发条件 | 修复动作 | 尝试次数 |
|----------|----------|----------|
| ModuleNotFoundError | pip install <module> | 1–3 |
| FileNotFoundError (路径) | mkdir -p \<dirname\> + touch | 1 |
| Permission denied | chmod +x | 1 |
| Address already in use / port | lsof -ti:<port> \| xargs kill -9 | 1 |
| SyntaxError | 不自动修复（需 LLM） | 0 |
| No space left on device | df -h 告警 | 1 |
| Network timeout/refused | 重试提示 | 1–3 |
| Rust error[E...] + cargo | cargo check → cargo clippy --fix | 2 |

## 文件位置

- 核心实现：`~/.hermes/hermes-agent/agent/auto_fix.py`
- 序列集成：`~/.hermes/hermes-agent/agent/apex_runtimeos_sequence.py`（`SequenceStateMachine.auto_fix_step()`）
- 守护进程集成：`~/.hermes/hermes-agent/se20/workers/ars_daemon.py`（`auto_repair()`）

## 集成方式

### 1. 独立调用

```python
from agent.auto_fix import AutoFixEngine

engine = AutoFixEngine(session_id="my_task")
result = engine.execute_and_fix(
    "python build_script.py",
    timeout=60,
    max_attempts=3,
)
# result["resolved"] → True/False
# result["attempts"] → 实际尝试次数
# result["score"] → 最终评分 0.0–1.0
# result["fix_log"] → [{"attempt": 1, "action": "...", "result": "..."}]
```

### 2. 序列步骤调用

```python
from agent.apex_runtimeos_sequence import SequenceStateMachine
sm = SequenceStateMachine("21354", "Repair build")
step_result = sm.auto_fix_step("cargo build")
# 同时完成：步骤推进 + 自动修复 + 证据记录
```

### 3. 守护进程自动修复

ARS daemon `se20/workers/ars_daemon.py` 中已有 `auto_repair()` 函数，ARS 循环失败时自动调用 AutoFixEngine 诊断修复。

## 审计追踪

每次修复尝试记录到 SQLite `auto_fix_log` 表：

| 字段 | 内容 |
|------|------|
| id | 自增主键 |
| session_id | 会话标识 |
| command | 执行的命令 |
| attempt | 第几次尝试 |
| exit_code | 退出码 |
| stderr | 错误输出（前1000字符） |
| fix_action | 修复动作 |
| fix_result | 修复结果（前500字符） |
| score | 评分 0.0–1.0 |
| resolved | 是否解决（0/1） |
| created_at | 创建时间 |

### 查看统计

```python
engine.get_stats()
# → {"total": 6, "resolved": 3, "avg_attempts": 1.0, "avg_score": 0.533}

engine.get_recent(limit=10)
# → [{"id": 1, "command": "...", "resolved": 0, ...}]
```

## 边界条件

- 启发式修复比 LLM 修复更可靠（确定性），但覆盖范围有限
- 复杂错误（SyntaxError、逻辑错误）需要 LLM 修复——可扩展 `_default_fixer()` 或传入自定义 fixer
- 网络错误是瞬态的——重试可能成功，但 auto-fix 不保证解决
- max_attempts=3 防无限循环
- 不修改核心文件：AutoFixEngine 是工具，不是 framework overlay

## 来源

- nanoGPT-claw (Rust)：8 real skills + auto-fix closed loop
- APEX-MEM：5D 记忆系统（通过另一条路径吸收）
- 吸收时间：2026-06-01
