# Route-Chain 硬门禁烟测报告

生成时间：2026-05-28 12:59

## 1. 结论

状态：门禁生效，自动入库与自动晋升被正确阻断。

本轮执行了真实五段链烟测，但外部模型调用未全部完成：5 个阶段中只有 2 个阶段拿到真实 response_id。系统没有把失败冒充成功，候选基因状态为 candidate_blocked，正式基因库写入为 BLOCK，受控自动晋升为 BLOCK。

## 2. 证据

- evidence：`/Users/appleoppa/.hermes/workspace/agi-routing/evidence/rceg_20260528_125408_41f9a7ae.json`
- candidate：`/Users/appleoppa/.hermes/workspace/agi-routing/gene-candidates/gene_candidate_rceg_20260528_125408_41f9a7ae.json`
- promotion audit：`/Users/appleoppa/.hermes/workspace/agi-routing/auto-promotions/1779944322_blocked.json`

## 3. 烟测结果

- task_class：evolution_agi
- selected_chain：dual_strong_review
- execute_stages：true
- stage_count：5
- real_response_count：2
- final_decision：partial_model_execution
- record_hash：40a425529a557c8f3728947e06ce2f2d061aaa5a250d334f3a1edb8fddfd80bc

失败阶段：

1. GPT主脑统筹：timeout
2. 旁证压缩：MiniMax endpoint 404
3. GPT主脑收束：timeout

成功含义：

- Claude/GPT 至少部分真实参与，但不足以通过候选基因门禁。
- 门禁没有放行不完整证据。

## 4. 候选基因门禁

候选状态：candidate_blocked

阻断原因：

- missing_stage_response_or_hash
- final_decision_not_eligible
- final_delta_too_short

## 5. 基因库写入

结果：BLOCK

正式基因库读回：0 条。

说明：自动写入已经开启，但门禁没有通过，所以没有污染正式基因库。

## 6. 自动晋升

结果：BLOCK

promotion_hash：6ebbd45d80f4c2c1b29ae63112fd57a8038842c9422a8d108b55767a1311d43b

说明：自动晋升已经开启为受控模式，但候选基因未通过，因此晋升审计记录为 BLOCK。

## 7. 验证

- `test_route_chain_gene_autopromotion.py`：通过
- `test_route_chain_hard_integration.py`：通过
- 合计：5 passed
- py_compile：通过

## 8. 下一步

硬接入本身有效；下一步应修复 route-chain 执行可靠性：

1. GPT 阶段 timeout 需要更细的阶段级落盘和可恢复重试。
2. MiniMax endpoint 404 说明当前 MiniMax 兼容路径不正确，需要改为已验证 provider 调用方式或在旁证压缩阶段降级到可用模型。
3. `route_chain_evidence_gate.py` 当前仍位于 `~/.hermes/workspace`，应迁入仓库受控位置并加完整测试。
