# PGG Archon evolution pipeline execution surface

## 适用场景

用户要求“继续进化”“把 evolution pipeline 做成真正闭环执行面”“不要只写方案/报告”时，必须把进化链路做成可运行 pipeline，而不是总结文档。

## 闭环定义

最低闭环：

```text
目标 → 证据采集 → 诊断 → Debate → ECC执行 → 验证 → 评分 → 晋升门禁 → SQLite入库 → 读回
```

只有生成 Markdown 或只说下一步，不算完成。

## 当前落地文件

```text
/Users/appleoppa/.hermes/agent/pgg_archon_evolution_pipeline.py
/Users/appleoppa/.hermes/evolution_pipeline/state.json
/Users/appleoppa/.hermes/evolution_pipeline/runs/<run_id>.json
```

## 执行命令

```bash
python3 ~/.hermes/agent/pgg_archon_evolution_pipeline.py "把 evolution pipeline 做成真正的闭环执行面"
```

## 验证门禁

一次合格运行至少验证：

- PGG modules active；
- NanoGPT sidecar healthy；
- provider registry synced；
- Feishu WebSocket connected；
- Feishu receive/reply verified；
- pipeline py_compile；
- artifact written；
- PGG SQLite experiment/gene 入库并读回。

## 评分与晋升

- `score >= 0.75` 且关键门禁通过：`promotion_ready`；
- 否则：`held_for_repair`；
- artifact 必须带 `manifest_hash`；
- DB 中写入 experiment 与 gene，不能只写本地 JSON。

## 模型审查纪律

PGG/AGI/进化任务需要真实 GPT/Claude 审查证据。可用 Hermes 已配置 provider，但 GPT/Claude 必须走 Responses API：

```text
/v1/responses
```

不得退回 `/v1/chat/completions`，不得用角色扮演冒充模型审查。

## 本轮暴露的下一缺口

GPT 审查认为当前执行面是 `qualified_yes`，但仍未证明：

- 安全自主 mutation（变更执行）；
- regression tests（回归测试）；
- rollback receipt（回滚凭证）；
- quarantine gate（隔离门禁）；
- production impact check（生产影响验证）。

因此下一轮最高价值是：

```text
rollback/quarantine gate + mutation dry-run
```

## 用户体验纪律

当用户说“继续”或明确指出下一步最值得做时，如果风险低、可回滚且收益高，直接执行到验证、入库、读回，不要停在建议。
