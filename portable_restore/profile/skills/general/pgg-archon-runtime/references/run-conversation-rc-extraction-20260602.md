# run_conversation RC-S01 最小抽取与契约窗口治理（2026-06-02）

## 适用场景

当 `agent/conversation_loop.py::run_conversation()` 仍处于超长核心函数、CodeGenesis 为 WATCH，且需要降低重复/复杂度时，先走只读契约门禁，再做小粒度、可逆、行为等价的 RC-S01 helper extraction（辅助函数抽取）。

## 已验证的推进顺序

1. 先建立 RC-S01~RC-S09 read-only characterization contracts（只读特征契约），锁定核心行为信号。
2. 再生成 extraction readiness matrix（抽取就绪矩阵）。只有矩阵允许时，才进入最小抽取。
3. 每轮只抽一个 RC-S01 小片段，禁止跨到 RC-S02+。
4. 抽取必须是 mechanical helper extraction（机械辅助函数抽取），不改变 provider/tool/scheduler/security boundary 行为。
5. 每轮补 characterization tests（特征保持测试）。
6. 每轮运行 targeted pytest、`py_compile`、`git diff --check`、APEX-GOD health、EVOLUTION_MANIFEST update。
7. 提交只 stage 本轮文件。

## 已验证的安全 helper 形态

### `_reset_turn_runtime_state(agent)`

可抽取内容：
- retry counters（重试计数器）清零
- post-tool 标记复位
- guardrail（护栏）turn reset
- vision support（视觉支持）初始化

测试要点：构造 `SimpleNamespace` agent + fake guardrails，断言所有字段恢复原始 bootstrap 值。

### `_bind_turn_task_id(agent, task_id)`

可抽取内容：
- 传入 task_id 时原样使用
- 未传入时生成 UUID
- 写入 `agent._current_task_id`
- 返回 effective task id

测试要点：分别覆盖 provided task_id 与 missing task_id 两条路径。

## 关键坑：契约窗口不能用绝对行号

抽取 helper 后，`run_conversation` 起始行号会下移；如果 slicer（切片器）使用绝对行号切 RC-S01~RC-S09，后续 contracts 会漂移并误报 WATCH。

稳定做法：

```python
rc_s01_start = fn.lineno
rc_s01 = _window_facts(fn, rc_s01_start, rc_s01_start + 499)
rc_s02 = _window_facts(fn, rc_s01_start + 500, rc_s01_start + 999)
# ...后续窗口全部相对 run_conversation 起始行定位
```

## 漂移敏感信号的兼容原则

抽取或小规模移动后，某些特征信号可能跨窗口或变量名变化。允许扩大 read-only signal（只读信号）匹配，但不能降低行为门禁：

- RC-S04 cost/usage：除 `estimate_usage_cost` 外，可兼容 `cost_result`、`canonical_usage`。
- RC-S08 stream delta：除 `agent.stream_delta_callback` 外，可兼容 `_current_streamed_assistant_text`、`_partial_streamed`。

## Readiness matrix 风险口径

当所有 RC-S01~RC-S09 contracts PASS、函数仍大于 4000 行、CodeGenesis 仍 WATCH 时，允许 RC-S01 在 LOW 或 MEDIUM 风险下继续最小机械抽取；禁止批量抽取、RC-S02+ 抽取、provider/tool 行为变更、scheduler/security boundary mutation（调度/安全边界突变）。

## 汇报口径

必须明确：
- `run_conversation` 只是完成小粒度 helper extraction，不是整体重构完成。
- CodeGenesis 仍 WATCH 时，不得宣称质量问题已解决。
- 报告要给出测试结果、health、Manifest 时间与 sha256、commit hash。
