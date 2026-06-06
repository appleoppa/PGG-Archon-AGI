# All-LLM + Open-Source Gap Closure Pattern（2026-06-06）

## 触发场景

当用户要求“调用所有 LLM”“去 GitHub/VX/开源网站学习”“代入公式逐一解决”“不造假最大范围闭环”时，必须把它当作 AGI/进化高强度任务，而不是普通总结任务。

## 执行骨架

```text
/goal 公式门禁
→ LDR(K)：读取公式面板、Manifest、git、当前 diff、unresolved gaps
→ GapDetect：区分 active gap / superseded gap / policy boundary / transient provider failure
→ OpenSourceLearn：抓官方 repo/docs，落盘摘要，不镜像大文档
→ All-LLM Review：GPT/Claude/DeepSeek/MiniMax/Agnes 处理；MiMo 仅 third-party judge
→ CodeSelfFix：只改低风险、可回滚、当前 diff 范围内的问题
→ Verify：聚焦 pytest + py_compile + diff check + formula panel readback
→ KnowledgeSettle：Manifest/skill/reference 读回，git clean
```

## 多 LLM 调用纪律

- 不要串行长时间卡在一个 provider。若串行超过约 5 分钟或单通道长时间无输出，应停止或改为短超时并发补调。
- 每个通道独立记录：`OK / ERROR / TimeoutExpired / returncode / stdout_chars / stderr_chars`。
- MiMo 固定为 third-party judge；超时或失败必须标 `ERROR`，不能冒充通过，也不能阻塞其他 LLM 的真实进展。
- Agnes 是普通/非关键通道；失败如实记录即可。

## 开源学习吸收纪律

- 优先官方仓库和官方文档 raw：OpenAI Responses、LiteLLM routing/fallback、promptfoo、OpenTelemetry status/trace 等。
- raw 路径 404 是检索失败，不是工具失效；换 README / OpenAPI / docs guide 路径继续查。
- 落盘为 `open_source_learning_summary.json`：记录 OK/ERROR、URL、摘要、吸收结论。

## Gap lifecycle 语义

不要改写旧 Manifest 历史来“清零”旧 PARTIAL。正确做法：

```text
旧阻断：保留原状态
新证据：新增 latest_* entry
关系：superseded_not_mutated + superseded_by
边界项：default-off / optional / manual-run 标为 policy boundary，不冒充 runtime takeover
```

典型字段：

```json
{
  "gap_lifecycle": {
    "superseded_not_mutated": ["latest_old_partial_key"],
    "superseded_by": ["latest_new_pass_key"],
    "default_off_items_are_policy_boundaries_not_runtime_takeover": ["latest_optional_gate_key"]
  }
}
```

## Canary / operator toggle Pitfalls

- 配置字段存在不等于能力可用；若新增 `operator_toggle_enabled`，必须测试 sanitizer 是否允许对应 mode，否则会出现“永远不可启用”的假能力。
- Operator/enforce 类能力必须 default-off、fail-open、hard-deny legal/audit/AGI，并且有 rollback/readback。
- `mode=operator` 只能在明确 scope（如 `exact_general_gpt55_same_class_only`）下允许；scope 不匹配应降回 `observe_only` 并关闭 operator toggle。
- Batch canary 只能证明 bounded exact/general canary，不得称 global route-enforce、生产接管或法律/审计/AGI 授权。

## 验证清单

```bash
PYTHONPATH=$PWD venv/bin/python -m pytest -q \
  tests/test_pgg_archon_quantum_channel_router_policy.py \
  tests/hermes_cli/test_web_server.py::test_omniroute_route_enforce_batch_canary_api_writes_snapshot \
  tests/hermes_cli/test_web_server.py::test_omniroute_endpoint_mimo_rejections_remain_http_400 \
  tests/test_pgg_archon_formula_gate_status.py

venv/bin/python -m py_compile \
  agent/pgg_archon_quantum_channel_router.py \
  hermes_cli/web_server.py \
  agent/pgg_archon_formula_gate_status.py

git diff --check
PYTHONPATH=$PWD venv/bin/python -m agent.pgg_archon_formula_gate_status 'AGI 进化 全LLM 开源学习 unresolved gaps 最大合规闭环'
```

## 汇报口径

完成可以说：

```text
五路/多路 LLM 成功，失败通道如实 ERROR；开源学习已落盘；测试通过；Manifest 已更新；git clean。
```

不能说：

```text
所有 LLM 都通过（若 MiMo/其他通道 ERROR）
T5/full AGI
生产级全局 enforce
官方外部评测通过
default-off gate 已生产接管
```
