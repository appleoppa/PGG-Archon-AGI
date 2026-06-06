# APEX-MEM 上游更新吸收模式（2026-06）

适用范围：APEX-MEM 或类似 Rust memory sidecar（记忆侧车服务）已经本地部署/审计过，但外部上游仓库出现新提交，需要在不覆盖本地 Hermes/PGG bridge（桥接）、安全加固和审计成果的前提下吸收更新。

## 触发信号

- 用户给出新的上游仓库 URL，询问“是否有更新”。
- 本地 repo 已有大量未提交审计/部署变更，不适合直接 merge。
- 上游新增 P0/P1/P2 correctness（正确性）修复，如 panic、N+1 query、O(n) writes、graph index、stable point id、dedup ordering。

## 证据优先顺序

1. 记录本地状态：`git status --short`、`git rev-parse HEAD`、branch、remote。
2. 添加/更新 `upstream` remote，`git fetch upstream --tags --prune`。
3. 记录：上游 main HEAD、merge-base、ahead/behind、上游新增 commits、diffstat。
4. 若本地有未提交变更，先保存 patch/status/diffstat 到治理目录；不要直接 merge 覆盖。
5. 对上游新增提交按文件/风险分组人工吸收，优先 P0/P1/P2，不机械 cherry-pick 整包。

## 多模型审计纪律

进化/PGG/APEX/AGI 类吸收必须真实调用已配置 provider（供应商）：

- GPT/Claude 必须走 Responses API（`/v1/responses`），不能走 chat completions。
- DeepSeek/MIMO/MiniMax 可按其配置走 chat completions。
- 记录 HTTP status、bytes、输出文件路径；缺 key 或失败不得宣称已调用。
- 让模型审查：哪些上游修复必须吸收、哪些本地修复必须保留、如何验证、哪些供应链风险不能冒称解决。

## 合并策略

- 不直接 `git merge upstream/main`，除非工作树干净且明确授权。
- 对有本地安全/部署改造的文件使用人工 patch：
  - 保留 loopback-only bind guard。
  - 保留 REST/MCP body limit。
  - 保留 Hermes `apex_mem` bridge。
  - 保留 reqwest 0.12 / rustls-tls 等依赖加固。
- 对上游 correctness 修复逐项吸收：
  - shared GraphStore，避免空 graph retriever。
  - consolidator 单 write lock，避免非重入 RwLock panic。
  - `get_many()` / `upsert_many()` 批处理，降低 N+1/O(n) writes。
  - stable vector point id，避免 delete 后 point id 复用。
  - graph candidates 按 id 取最大分后排序 dedup。
  - diagnosis 使用真实 BM25/vector/graph 指标。

## 必跑验证门禁

Rust gates：

```bash
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo build --release
cargo test
cargo check --benches --locked
```

部署与功能 smoke：

- 复制 release binary 到 workspace bin 并计算 SHA256。
- `launchctl kickstart -k gui/$(id -u)/com.appleoppa.apex-mem`。
- `/health`、`/v1/stats`。
- REST ingest/search。
- MCP graph link + REST graph_seeds search，确认 `graph_candidates >= 1` 且目标节点进入 hits。
- 大请求体应返回 HTTP 413。
- 非 loopback bind 未设置 `APEX_MEM_ALLOW_NON_LOOPBACK` 时应拒绝。
- Hermes bridge：py_compile、`ApexMemClient.health()`、registry entry、handler search。

## 供应链边界

- 运行 `cargo audit` 与 `cargo deny check` 并归档。
- 若仍有 bincode/hnsw_rs/tantivy/parquet/arrow/lru 等传递依赖 advisory，不要说“安全完成”。
- 如果迁移依赖链会引入大范围行为变化，应记录为 WATCH/后续专项，而不是为了报告好看强行替换。

## 交付口径

可以说：

> 已真实对比上游并吸收指定 P0/P1/P2 修复；Rust gates、REST/MCP、Hermes bridge 已验证通过。

不能说：

> 已生产级完成、已消除全部漏洞、已替换 Hermes core memory、已提交/推送到 GitHub。

## 报告材料

最终报告应包含：

- 上游 HEAD、merge-base、ahead/behind。
- LLM 调用状态与证据目录。
- 吸收的具体修复列表。
- 验证命令与结果。
- 部署 binary hash。
- 供应链 WATCH 列表。
- 未 commit/push 的原因（如有）。
