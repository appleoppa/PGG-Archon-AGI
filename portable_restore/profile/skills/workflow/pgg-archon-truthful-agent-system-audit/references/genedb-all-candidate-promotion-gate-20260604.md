# GeneDB 全候选 promotion gate 模式 — 2026-06-04

## 触发场景

用户指出 GeneDB candidate / promotion 未自动晋升，或要求“调用所有 LLM 逐一解决 promotion gate”。

## 核心教训

不要把单个 `gene_id` 的 promotion gate 等同于候选池审核完成。需要先有一个 all-candidate read-only gate：扫描全部 `gene_lifecycle.state='candidate'` 行，逐条输出 blockers，再接 LLM quorum gate；只有全候选审核和 quorum 都通过，才允许进入单 gene promotion transaction。

## 推荐顺序

1. 读回 `~/.hermes/data/pgg_archon.db`：`genes`、`gene_lifecycle`、`promotion_chain` schema 和状态分布。
2. 列出全部候选：`state='candidate' and promoted_at is null`，按 `quality_score desc` 排序。
3. 真实调用配置 LLM 通道，逐个保存 evidence JSON：HTTP status、visible_output_chars、raw hash、classified_verdict。
4. 用 `pgg_archon_llm_quorum_gate` 汇总 evidence；失败通道记 `ERROR`，不能降级成 PASS。
5. 用 all-candidate read-only gate 逐条判断：
   - state 必须是 candidate；
   - promoted_at 必须为 null；
   - quality_score 默认阈值 >= 0.80；
   - 重复候选要阻断；
   - core takeover / auto core mutation 类候选要额外阻断，除非有明确人工授权和回滚证明；
   - LLM quorum 未通过时，所有候选都不能 promotion-ready。
6. 只有 `READY_FOR_PROMOTION_TRANSACTION` 时，才进入 `pgg_archon_gene_promotion_transaction`；transaction 必须 backup DB、更新 exactly one lifecycle row、insert promotion_chain、读回验证。
7. 总账写入要区分 `BLOCKED_WITH_EVIDENCE`、`READY_FOR_PROMOTION_TRANSACTION`、`PROMOTED_VERIFIED`，不得把 BLOCKED 写成完成晋升。

## 证据口径

可说：
- “已补齐全候选只读 promotion gate”。
- “已调用多 LLM 并形成 quorum evidence”。
- “本轮 BLOCKED，未自动晋升”。

不可说：
- “GeneDB promotion 已完成”（除非 transaction 真实 PROMOTED_VERIFIED）。
- “Claude/DeepSeek/MIMO/Agnes 通过”（如果通道 HTTP/SSL/visible output 不满足门禁）。
- “candidate 存在 = promotion 完成”。

## 常见阻断

- GPT/MiniMax 可见输出但 verdict=BLOCKED。
- Claude HTTP 403 / account exhausted：记 ERROR。
- DeepSeek 只有 reasoning_content、content 为空：不计 visible PASS。
- MIMO/Agnes TLS/endpoint 失败：记 ERROR。
- phase3 ARS 重复候选：duplicate/staleness review 阻断。
- core takeover 候选：人工授权、回滚、安全证明不足时阻断。

## 复用产物形态

- `llm_promotion_summary.json`
- `llm_quorum_gate_result.json`
- `gene_candidate_promotion_audit_result.json`
- EVOLUTION_MANIFEST summary 键：`latest_genedb_candidate_promotion_gate`
