---
name: memory-retrieval-architecture
description: 多通道记忆检索架构 — 5D memory tiers + 5-channel RRF fusion + dense/BM25/FTS5/graph retrieval. 涵盖 akashic_memory、dreaming consolidation、memory flush、benchmark 和 embedding。
version: 1.0.0
author: 苹果中枢
license: MIT
metadata:
  hermes:
    tags: [retrieval, memory, embedding, vector, FTS5, graph, RRF, benchmark]
    related_skills: [super-evolution-20, evolution-systems-governance, legal-knowledge-base-governance]
---

# memory-retrieval-architecture

## 概述

本技能涵盖多通道记忆检索的完整架构，从 fragment 存储到多路融合检索到质量基准测试。

## 5D Memory Tiers

每个 fragment 有5个记忆层级，按半衰期衰减：

| Tier | 名称 | 半衰期 | 适用场景 |
|------|------|--------|----------|
| 0 | Working | 1 小时 | 当前会话上下文 |
| 1 | Episodic | 7 天 | 近期交互记录 |
| 2 | Semantic | 6 个月 | 通用知识 |
| 3 | Procedural | 1 年 | 操作流程/技巧 |
| 4 | Declarative | 5 年 | 公式/原理/事实 |

`fragment_strength()` 按 `2^(-t/half_life)` 指数衰减。

## 5-Channel Retrieval (RRF Fusion)

5条独立检索通道通过 RRF (Reciprocal Rank Fusion) 融合：

```
Query ─┬→ Vector (TF-IDF n-gram, 16384d, cosine)
        ├→ Dense (fastembed, 512d, cosine)
        ├→ BM25 (rank_bm25, keyword)
        ├→ FTS5 (SQLite, incremental, phrase+prefix)
        └→ Graph (networkx BFS, weighted by kind+strength)
        ↓
    RRF(k=60) → RankedResults
```

### 通道选择指南

| 场景 | 推荐通道 | 理由 |
|------|----------|------|
| 精确关键词 | BM25 / FTS5 | 词频匹配精确 |
| 语义相似 | Dense / TF-IDF | 向量cosine捕获语义 |
| 关系链 | Graph BFS | 沿关系边传播 |
| 短语/前缀 | FTS5 | MATCH语法 |
| 全量融合 | 5-channel RRF | 最佳综合效果 |

### Dense 嵌入 (fastembed)

```python
from agent.akashic_memory import DenseEmbedder
de = DenseEmbedder(model_name='BAAI/bge-small-zh-v1.5')
vectors = list(de.embed_batch(texts))  # → List[np.ndarray[512, float32]]
```

模型: BAAI/bge-small-zh-v1.5 (512-dim, ONNX, ~33MB)
适合中文场景。英文场景可换 `BAAI/bge-small-en-v1.5`。

### FTS5 增量索引

```python
# 自动增量写入（不需要每次rebuild）
conn.execute('INSERT INTO akashic_fts_content(id,content,title,tags) VALUES(?,?,?,?)')
# 全量重建（仅在初始化时）
conn.executescript("INSERT INTO akashic_fts(akashic_fts) VALUES('rebuild')")
```

外部内容表: `akashic_fts_content(id, content, title, tags)`
FTS5虚拟表: `akashic_fts(content, title, tags, content='akashic_fts_content')`

### Graph 关系检索

```python
# 自动建立关系（基于共享metadata值）
ak._hybrid._graph._rebuild_relations()
# BFS 搜索
graph_results = ak._hybrid._graph.search(query_embedding, top_k=5)
```

关系建立规则: 同 `source` / 同 `type` / 同 `lang` 值的 fragment 之间连边。
边权重 = 0.5 + 0.5 * similarity_of_metadata。

## Retrieval Benchmark

```python
from se20.benchmark import RetrievalBenchmark
bm = RetrievalBenchmark()
r = bm.run_all()  # recall@[1,3,5,10] + MRR + ablation
```

输出指标：
- **Recall@k**: 前k结果中包含正确匹配的比例
- **MRR**: 第一个正确匹配的倒数排名均值
- **Ablation**: 逐个关闭通道，看每个通道的贡献

预期基线（95 fragments）：
- All fused: Recall@1=1.0, MRR=1.0
- Dense alone: ~1.0
- BM25 alone: ~1.0
- Graph alone: ~0.9
- TF-IDF alone: ~0.9

## Curated Memory Saturation Governance

Prompt-injected `MEMORY.md` / `USER.md` are a compact high-signal index, not a store for task logs, status dashboards, runbooks, provider matrices, or old session narratives. When they approach their configured limit, do not blindly raise `memory_char_limit` or append more text.

Use the five-tier routing rule:

1. **Working** — current turn/session context; do not persist.
2. **Episodic** — historical tasks, phase records, old provider states; keep in `session_search`, archive, or manifest.
3. **Semantic** — stable technical/domain knowledge; store in skill references or retrieval stores.
4. **Procedural** — workflows, fixes, debugging paths; store in `SKILL.md` and `references/`.
5. **Declarative** — durable red lines, stable preferences, core indexes; only this belongs in prompt-injected `MEMORY.md` / `USER.md`.

Safe compaction gate: back up `MEMORY.md` and `USER.md` → create a full tiered archive under `~/.hermes/workspace/治理/` → rewrite MEMORY/USER as short declarative indexes → verify with `MemoryStore` char counts and drift checks → record in `EVOLUTION_MANIFEST.json` → if important enough, fuse the governance rule into SOUL.

2026-06-05 default-profile outcome: `MEMORY.md` 9951 chars / 36 entries → 2054 chars / 13 entries; `USER.md` 3785 chars / 32 entries → 1024 chars / 13 entries; MemoryStore drift checks returned None. See `references/curated-memory-saturation-governance-2026-06-02.md` for the full governance pattern and latest outcome.

## Memory Fragmentation

### Dreaming Consolidation (`agent/dreaming.py`)

| 步骤 | 功能 | 参数 |
|------|------|------|
| decay | 衰减旧fragment强度 | threshold=0.1 → 淘汰 |
| merge | 合并相似fragments | cosim > 0.95, key metadata匹配 |
| promote | 高访问fragments晋升tier | access_count / time_window |
| discover | 发现新关系 | 共享metadata值自动连边 |

### Memory Flush (`agent/memory_flush.py`)

| 模式 | 方法 | 效果 |
|------|------|------|
| heuristic | retain=N fragments, prune tier=0 | 快，无外部依赖 |
| LLM | 提取摘要后作为semantic存储 | 保留信息完整性 |

## 性能注意事项

- Dense vector search: 95 fragments 内用暴力 cosim (O(n))，>10K 需 HNSW
- FTS5: 增量写入无需全量重建
- Graph rebuild: 每次新fragment后增量连边，O(m) m=新fragment相似metadata数
- RRF: k=60 对95 fragments 最优，大数据集需调参

## 已知不足

- 无 HNSW/IVF 近似最近邻索引（大数据集必须）
- 无 query-adaptive 融合权重（当前 RRF 静态 k=60）
- 三条 lexical 通道 (TF-IDF / BM25 / FTS5) 功能重叠
- 无 cross-encoder reranking
- Graph 贡献较小（当前 ablation 显示 +0.1）

## Setup & Troubleshooting

### fastembed 安装

```bash
pip install fastembed  # 轻量 ONNX，无 pytorch 依赖
```

- 模型自动下载到 `~/.cache/huggingface/hub/`
- 首次 embedding 会下载模型文件（~33MB for BAAI/bge-small-zh-v1.5）
- 若 pip 因代理超时失败：`pip install fastembed --no-deps` 再逐一安装 `onnxruntime` 等
- 模型可选列表：`TextEmbedding.list_supported_models()`

### FTS5 表结构

FTS5 虚拟表必须在 `state.db` 中预先创建：

```sql
CREATE TABLE IF NOT EXISTS akashic_fts_content (
    id TEXT PRIMARY KEY,
    content TEXT,
    title TEXT DEFAULT '',
    tags TEXT DEFAULT ''
);
CREATE VIRTUAL TABLE IF NOT EXISTS akashic_fts USING fts5(
    content, title, tags,
    content='akashic_fts_content',
    content_rowid='rowid'
);
```

列名必须与 FTS5 表列名一致（`content` 不是 `body`），否则 rebuild 时报 "no such column" 错误。

### 完整 FTS5 重建

```python
conn.executescript("DELETE FROM akashic_fts_content;")
conn.executescript("INSERT INTO akashic_fts(akashic_fts) VALUES('rebuild');")
```

## 本地 Rust 记忆服务部署与吸收

当用户要求读取/部署 APEX-MEM 或类似 Rust memory retrieval service（记忆检索服务）时，不要停在 clone 或 build。按 `references/apex-mem-local-rust-service-deploy.md` 执行：clone/update → `cargo build --release` → `cargo test` → CLI ingest/search/dream/apex smoke → REST/MCP live probes → LaunchAgent（如需本地常驻）→ 部署报告与 hash 读回。

当用户给出外部上游仓库并要求“查看是否有更新/调用所有 LLM 解决/最大范围合规吸收”时，按 `references/apex-mem-upstream-absorption-pattern.md` 执行：先记录本地 dirty worktree 和 upstream diff，真实调用可用 LLM（GPT/Claude 走 Responses API），再人工吸收 P0/P1/P2 修复并保留本地 loopback/body-limit/Hermes bridge，最后跑 Rust gates、REST/MCP/Hermes bridge 和供应链复扫；不要在未授权或工作树混杂时直接 merge/commit/push。

当用户追问“是否已同步到我的远程私有仓库 / 其他电脑是否只需下载部署”时，按 `references/apex-mem-private-remote-deployment.md` 执行：先区分本地未提交能力、远程 origin/main、Hermes-Agent bridge 和 LaunchAgent/runtime 资产；若需要可复现部署，仓库化 deploy/smoke/bridge 脚本，commit/push 后必须 fresh clone build + 独立端口 smoke test + 远程 HEAD 读回，才可说“可从私有仓库下载部署”。

2026-06-02 状态更新：APEX-MEM 当前能力已同步到远程私有仓库 `appleoppa/APEX-MEM`（commit `65193ef`），并完成 fresh clone build/smoke 验证；随后用户曾要求清理本地，已移除本机 sidecar、LaunchAgent、runtime、本地 clone/tmp clone 和 Hermes bridge 本地接入。之后同日 CLI 会话又从本地 bare mirror 恢复 APEX-MEM：重新 clone、release build、安装 `/Users/appleoppa/.hermes/workspace/bin/apex-mem`、重建 `com.appleoppa.apex-mem.plist` 并启动 loopback 服务。以后必须先查实时进程/launchd/端口/路径，不得仅凭旧状态说“已删除”或“仍运行”。

- 远程可复现部署入口：`git clone https://github.com/appleoppa/APEX-MEM.git && cd APEX-MEM && ./scripts/deploy_macos.sh`。
- Hermes bridge（桥接）远程模板仍在 APEX-MEM 仓库：`scripts/install_hermes_bridge.sh` + `hermes_bridge/`。
- 当前 default Hermes 本机是否存在 `apex_mem` tool 或 `http://127.0.0.1:8765` 服务必须实时查证；2026-06-02 12:44 实测 launchd 进程存在且 127.0.0.1:8765 返回 ok，但该状态可能被用户后续清理改变。
- 安全边界：不自动开放外网、不替代既有 `memory` curated memory（人工精选记忆），只作为可安装/可恢复的 PGG/APEX-GOD 记忆检索 sidecar。

吸收口径：可以说“APEX-MEM 能力已推送到私有仓库并验证可 fresh clone 部署”；当前是否本机运行必须以实时 `ps/launchd/lsof/curl` 证据为准；不能说“已替换 Hermes 核心 memory/provider/scheduler”。

## 相关文件

- `agent/akashic_memory.py` — 主实现: 5D tiers + 5-channel RRF + DenseEmbedder
- `agent/dreaming.py` — Dreaming 凝固管线
- `agent/memory_flush.py` — 上下文压缩前提取
- `se20/benchmark.py` — 检索质量基准测试
- `references/apex-mem-local-rust-service-deploy.md` — APEX-MEM/Rust 记忆服务本地部署证据链
- `references/apex-mem-full-audit-absorption-pattern.md` — APEX-MEM/类似 Rust memory sidecar 的全文件审计、真实多模型审计、开源文档吸收、Hermes/PGG loopback bridge 接入、安全最小加固、供应链扫描、最终验证与边界声明模式
