# APEX-MEM / Rust memory sidecar 全量审计吸收模式

适用：用户要求读取、部署、审计、全量吸收 APEX-MEM 或同类 Rust memory retrieval sidecar（记忆检索侧车服务）时。

## 目标口径

可声明：
- Rust sidecar 已本地部署并以 loopback（本机回环）方式接入 Hermes/PGG bridge（桥接）。
- REST/MCP、CLI、graph seed retrieval（图种子检索）、build/test/clippy/bench gates 均有真实输出验证。

不可声明：
- 已替换 Hermes core memory/provider/scheduler。
- 生产级外网可开放。
- 零漏洞、零风险、全依赖安全。
- 未真实调用的 LLM 参与了审计。

## 推荐流程

1. 仓库与基线
   - clone/update 到 `~/.hermes/workspace/github/<owner>/<repo>`。
   - 记录 HEAD、branch、tracked file manifest、sha256、tree summary。
   - 先跑 `cargo fmt --check`、`cargo test`、`cargo check --benches --locked`、`cargo clippy --all-targets --all-features -- -D warnings`。

2. 全文件审计
   - 读 README/Cargo.toml/CLI/API/storage/retrieval/MCP/pipeline 入口。
   - 对比“设计声明”和“真实代码路径”。重点查：embedding 是否真实入库、graph 是否共享同一实例、pagination offset 是否有效、REST/MCP 是否暴露全部必要字段。
   - 静态扫 unwrap/expect/panic/todo/unimplemented/unsafe/secret words，但不要把文本里的安全词误判为真实 secret。

3. 多模型审计
   - AGI/PGG/进化类任务必须真实调用 GPT/Claude/MIMO/DeepSeek 等已配置 provider；GPT/Claude 使用 Responses API。
   - 缺 key 的模型不得冒称调用。
   - 输出保存到治理/audits 目录，并在最终报告中区分 PASS/WATCH/BLOCKED。

4. 开源学习
   - GitHub code search 若 401/不可用，可改用 docs.rs、RustSec、cargo-deny 官方文档直读。
   - 吸收点优先落成代码或门禁，不只写学习报告。

5. 常见必须验证的修复点
   - `HybridRetriever` 应共享 `Arc<RwLock<GraphStore>>`，避免检索器拿空 graph。
   - ingest 生命周期应保存配置 embedder（嵌入器）的输出，不能计算后丢弃再走 hashing fallback。
   - REST `/v1/search` 应支持 `graph_seeds` / `graph_hops`，并 clamp `top_k` 与 hops。
   - SQLite list 应支持真实 offset。
   - bench API drift 必须纳入 `cargo check --benches --locked`。
   - MCP graph link 参数以 tool schema 为准；实测 APEX-MEM 是 `src/dst/kind`，不是 `from_id/to_id/relation`。

6. 安全最小加固
   - sidecar 默认只允许 loopback bind；非 loopback 必须显式授权 env，例如 `APEX_MEM_ALLOW_NON_LOOPBACK=1`。
   - REST/MCP 添加 body limit，例如 axum `DefaultBodyLimit::max(1_048_576)`。
   - search `top_k` clamp，graph hops clamp。
   - 未做 auth/token、rate limit、tenant isolation 前，只能称为本机 sidecar，不得称生产外网安全。

7. 供应链扫描
   - 若未安装，优先安装并运行 `cargo-audit` / `cargo-deny`。
   - advisory 可通过低风险依赖升级先消除，例如 reqwest 0.11 → 0.12 可移除旧 rustls-webpki/rustls-pemfile 路径。
   - 对 bincode/lru/parquet/arrow/tantivy/hnsw_rs 等大迁移风险，若无法在同轮安全完成，标 WATCH，不冒称完成。

8. 最终验证
   - `cargo fmt --check`
   - `cargo clippy --all-targets --all-features -- -D warnings`
   - `cargo build --release`
   - `cargo test`
   - `cargo check --benches --locked`
   - redeploy binary + sha256
   - launchd state + `/health` + `/v1/stats`
   - REST/MCP graph smoke：创建 src/dst → MCP link → REST graph search → `graph_candidates >= 1` 且 dst 进入 hits
   - body limit smoke：>1MiB 请求应返回 413
   - non-loopback smoke：未授权 bind `0.0.0.0` 应失败
   - Hermes bridge smoke：py_compile、client health/search、tool registry handler

## 报告要求

最终报告必须包括：
- 完成态：PASS/WATCH/BLOCKED。
- LLM 调用证据和未调用模型原因。
- 开源文档证据。
- 命令验证摘要。
- binary/report sha256。
- 供应链剩余风险。
- 明确边界声明：本机 sidecar bridge 完成，不等于 Hermes core replacement。

## 典型最终口径

“APEX-MEM Rust sidecar 已本地部署，并通过 Hermes/PGG `apex_mem` bridge 接入；本机 loopback 链路、REST/MCP、graph seed 检索、clippy/test/build/bench gates 已验证通过。生产级 auth/rate-limit/multitenant 与依赖供应链治理仍为 WATCH。”
