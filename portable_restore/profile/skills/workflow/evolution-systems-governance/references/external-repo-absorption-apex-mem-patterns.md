# APEX-MEM + nanoGPT-claw 全量吸收参考

吸收日期：2026-06-01
来源仓库：
- https://github.com/hernandez42/APEX-MEM (Rust 5D memory system)
- https://github.com/hernandez42/nanoGPT-claw (Rust closed-loop evolution)

## 吸收的模式清单

| # | 模式 | 来源 | 我方文件 | 状态 |
|---|------|------|----------|------|
| 1 | 5D Memory Tiers (Working/Episodic/Semantic/Procedural/Declarative) | APEX-MEM | agent/akashic_memory.py | ✅ 已部署 |
| 2 | 指数衰减 (Tier half-life: 1h/7d/6mo/1yr/5yr) | APEX-MEM | agent/akashic_memory.py | ✅ |
| 3 | Dreaming Consolidation (decay/merge/promote/discover relations) | APEX-MEM | agent/dreaming.py | ✅ |
| 4 | Memory Flush (heuristic + LLM extraction) | APEX-MEM | agent/memory_flush.py + ARS daemon | ✅ |
| 5 | 三重检索 (BM25 + TF-IDF Vector + NetworkX Graph → RRF fusion) | APEX-MEM | agent/akashic_memory.py | ✅ 原型 |
| 6 | Auto-Fix 闭合回路 (execute→score→fix→re-verify×3) | nanoGPT-claw | agent/auto_fix.py | ✅ |
| 7 | SequenceStateMachine.auto_fix_step() | nanoGPT-claw | agent/apex_runtimeos_sequence.py | ✅ |
| 8 | ARS daemon 自动修复 | nanoGPT-claw | se20/workers/ars_daemon.py | ✅ |

## 三重检索实现细节

```
BM25 (rank_bm25 BM25Okapi)      → fragment IDs by BM25 score
TF-IDF Vector (ngram 16384-dim)  → fragment IDs by cosine similarity
Graph (networkx DiGraph, BFS)    → fragment IDs by graph distance from vector seeds
         ↓
RRF fuse(k=60) → top N enriched results
```

- 每次 store() 后重建 BM25 索引 + Graph 自动连边（cosine>0.5）
- 搜索时三通道各取 n*3 候选 → RRF 融合
- 结果带 per-channel rank 调试字段（输出前剥离）

## 残留缺口（GPT-5.5 审计 58/100）

- P0: Dense vector embedding（sentence-transformers/ChromaDB 被代理网络阻断，ONNX 模型卡在 1.2MB/79MB）
- P0: 检索质量指标（recall@k、MRR、ablation study）
- P1: BM25 升级到 Tantivy/SQLite FTS5（支持增量索引）
- P1: MCP 服务层（axum server 暴露检索接口）

## 三模型调用方式

所有 LLM 通过统一 proxy `https://chuangagent.eu.cc/v1` 调用：
- GPT-5.5: POST /v1/responses, model=gpt-5.5, api_mode=codex_responses
- Claude Opus-4-7: POST /v1/responses, model=claude-opus-4-7, api_mode=codex_responses
- DeepSeek: POST /v1/chat/completions, model=deepseek-v4-flash
- MIMO v2.5 Pro: POST /v1/chat/completions, model=mimo-v2.5-pro
