# Route-Chain 硬门禁可靠性修复与入库烟测报告

生成时间：2026-05-28 13:30

## 1. 结论

状态：完成。

本轮修复了 route-chain 硬门禁可靠性问题，并完成一次通过门禁的真实烟测：五段链 5/5 均取得 response_id，候选基因 candidate_ready，正式基因库写入 PASS，受控自动晋升 PROMOTED_CONTROLLED。

边界：仍不声明 AGI 完成，不自动 patch 核心文件，不对外发布。

## 2. 修复内容

1. 将 `route_chain_evidence_gate.py` 迁入仓库受控位置：
   - `agent/route_chain_evidence_gate.py`
2. `conversation_loop.py` 改为调用仓库受控脚本。
3. 新增阶段级进度落盘：
   - 每完成一个 stage 即写入 evidence JSON。
   - 外部模型卡住时，已完成阶段不丢失。
4. 缩短模型请求 timeout。
5. 修复 MiniMax 404：
   - 旁证压缩阶段 MiniMax 不可用时降级到 DeepSeek。
6. 修复空 content 但有 response_id 时 output_hash 缺失的问题。
7. 新增测试：
   - `tests/agent/test_route_chain_evidence_gate.py`

## 3. 测试

运行：

- `test_route_chain_evidence_gate.py`
- `test_route_chain_gene_autopromotion.py`
- `test_route_chain_hard_integration.py`

结果：8 passed。

## 4. 烟测证据

证据文件：

`/Users/appleoppa/.hermes/workspace/agi-routing/evidence/rceg_20260528_132908_6f251968.json`

候选基因：

`/Users/appleoppa/.hermes/workspace/agi-routing/gene-candidates/gene_candidate_rceg_20260528_132908_6f251968.json`

晋升审计：

`/Users/appleoppa/.hermes/workspace/agi-routing/auto-promotions/1779946188_gene_candidate_rceg_20260528_132908_6f251968.json`

## 5. 烟测结果

- task_class：evolution_agi
- selected_chain：dual_strong_review
- stage_count：5
- real_response_count：5
- final_decision：model_execution_completed
- gene_status：candidate_ready
- gene_gates：[]
- gene_db_write：PASS
- readback_count：1
- promotion_status：PROMOTED_CONTROLLED
- agi_completion_claim：false

## 6. 模型参与

- GPT：参与主脑统筹、修复落地、主脑收束。
- Claude：参与反证审错。
- DeepSeek：作为 MiniMax 旁证压缩降级模型参与。

说明：MiniMax 当前 endpoint 仍不可用，但已不再阻断全链；系统记录 fallback_used。

## 7. 当前状态

- 硬门禁：已接入。
- 候选基因生成：已通过。
- 正式基因库写入：已通过。
- 受控自动晋升：已通过。
- 自动核心 patch：未开启。
- AGI 完成声明：false。
