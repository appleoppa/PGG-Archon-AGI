# 进化基因数据库化落地参考（当前版）

## 用途

服务当前唯一“开智进化循环”闭环：

```text
真实代入 → 短板自然暴露 → 外部开源/文档学习 → 吸收补齐 → 进化基因入库 → 验证
```

## 默认位置

- SQLite：`~/.hermes/workspace/开智/02-进化基因/apex_evolution_genes.sqlite3`
- Markdown 导出：`~/.hermes/workspace/开智/02-进化基因/apex_evolution_genes_<日期>.md`

## 写入原则

1. 每个自然暴露短板至少形成一条进化基因。
2. 外部学习必须发生在短板暴露之后。
3. 外部来源必须真实读取，不能只看标题或搜索结果。
4. 吸收点必须改变补齐动作。
5. 不覆盖未知历史 `.db`；先验证是否为 SQLite，若是文本台账则只追加索引。

## 推荐表

- `evolution_cycles`：周期元数据。
- `evolution_genes`：基因主体。
- `source_references`：外部来源。
- `gene_source_map`：基因-来源映射。
- `verification_log`：写入后验证。
- `v_active_genes`：活跃基因视图。

## 每条基因最少字段

- `gene_id`
- `cycle_id`
- `defect_no`
- `defect_name`
- `gene_name`
- `absorbed_knowledge`
- `source_refs_json`
- `repair_mechanism`
- `gate_type`
- `reusable_rule`
- `status`
- `evidence_grade`
- `verification_status`
- `boundary`
- `gene_hash`

## 验证清单

必须验证：SQLite 文件存在、表结构存在、周期记录数、基因记录数、来源记录数、映射记录数、活跃视图或等效查询、Markdown 导出存在、旧文本台账索引存在。

## 边界表述

数据库写入成功只证明“本轮补齐机制已固化”；不证明长期能力永久提升。长期能力须在后续真实任务中复验。
