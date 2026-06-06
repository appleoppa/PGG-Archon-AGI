# Triple Retrieval Absorption (Phase 4)

吸收来源：APEX-MEM (hernandez42/APEX-MEM) + nanoGPT-claw (hernandez42/nanoGPT-claw)
吸收日期：2026-06-01
交叉审计：GPT-5.5 (63/100), Claude Opus-4-7

## 架构对比

| 维度 | APEX-MEM (Rust) | 我方 (Python) | 差距 |
|------|-----------------|---------------|------|
| BM25 | Tantivy (Rust, mmap directory, incremental) | rank_bm25 + SQLite FTS5 | FTS5已实现增量，Tantivy mmap性能更优 |
| Vector | hnsw_rs (HNSW) | TF-IDF n-gram + fastembed Dense 512d | fastembed已落地，缺HNSW索引结构 |
| Graph | petgraph (加权BFS) | networkx (BFS, 505 edges) | 功能对等，petgraph更轻量 |
| Fusion | RRF | RRF k=60 | 对等 |
| 嵌入 | PooledEmbedder + HashingEmbedder | DenseEmbedder(fastembed) + TF-IDF | 更简单，但互补性足够 |
| 服务 | MCP (JSON-RPC 2.0 via axum) | 无 | 未实现，用户已取消 |
| 调参 | Genetic algorithm (16pop, 12gen) | 无 | 未实现 |
| 诊断 | MemoryDoctor | ECC audit | ECC更全面 |

## 5-channel RRF 架构

```
Query ─┬→ TF-IDF Vector (cosine, 16384d)
        ├→ Dense Vector (cosine, 512d, fastembed bge-small-zh-v1.5)
        ├→ BM25 (rank_bm25, keyword)
        ├→ FTS5 (SQLite, incremental, keyword+phrase)
        └→ Graph (networkx, BFS with kind+weight filter)
        ↓
    RRF(k=60) → Ranked Results
```

## 基准测试结果

| 通道 | Recall@5 |
|------|----------|
| TF-IDF Vector | 0.90 |
| Dense Vector | 1.00 |
| BM25 | 1.00 |
| FTS5 | 0.95 |
| Graph | 0.90 |
| All Fused | 1.00 |

MRR: 1.0 | Recall@1: 1.0 | Fragments: 95 | Graph edges: 505

## 关键路径

```python
from agent.akashic_memory import get_akashic
ak = get_akashic()
ak.store(text, metadata={...}, tier=2)  # auto-index: FTS5 + dense + BM25 + graph
results = ak.search(query, top_k=5)     # 5-channel RRF fusion
```

## 残留缺口 (GPT-5.5 审计)

- P0: APEX公式追溯工具（检索结果→5D得分的可审计推导链）
- P0: hard-negative / adversarial 评测
- P1: 三条 lexical 通道功能重叠 (BM25/FTS5/TF-IDF)
- P1: Graph 贡献隔离量化（当前 ablation 显示 +0.1 recall）
- P1: 静态 RRF → learning-based fusion weights
