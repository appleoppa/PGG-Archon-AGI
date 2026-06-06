# Hermes 第三轮清理与法律向量库重构模式

## 触发场景

用户明确要求对 Hermes/workspace 做进一步清理，并给出破坏性授权，例如：

- 删除 `workspace/存档`；
- 判断 `workspace/安全扫描` 是否无用，无用则删除；
- sessions 只保留近 N 天；
- 将旧向量库重构为面向法律业务的知识向量库。

## 执行纪律

1. **明确授权后可删除**：用户明确说“删除”的路径，可以删除，但仍要先记录大小、浅层清单和删除后存在性。
2. **先查内容再判无用**：例如 `workspace/安全扫描` 不能因名字直接删；需要抽样内容。如果主要是 `secret_scan_report_masked.json`、`remediation_*`、历史配置/auth 修复前备份、扫描 JSON/JSONL/log，可认定为历史扫描输出而非运行中安全引擎。
3. **sessions 按 mtime 保留窗口**：用户要求“保留 5 天内”，按文件 mtime 删除早于 cutoff 的 session 文件，记录 deleted/kept 数量和错误数。
4. **向量库重构不等于直接清空旧库**：旧 `workspace/向量库` 应迁入新库 `99_legacy_chroma_readonly/`，作为只读 legacy 数据，待迁移验证后再删。
5. **报告必须读回修正**：报告里的 deleted/kept 数量不能从错误字段名推断；写报告后读回，发现 `None` 这类占位必须立即修正。

## 推荐新法律知识向量库架构

路径建议：`~/.hermes/workspace/法律知识向量库/`

分层：

- `00_architecture/`：schema、设计说明。
- `01_raw/`：原始材料，不改写。
  - `指导案例库/`
  - `法律法规库/`
  - `本地办案沉淀知识/`
  - `司法机关与监管通讯录/`
  - `扩展公共法律数据/`
- `02_processed/`：clean_text、chunks、metadata、citations。
- `03_indexes/`：vector、bm25、graph、hybrid。
- `04_ingestion/`：pipelines、manifests、rejects。
- `05_eval/`：golden_questions、retrieval_tests。
- `99_legacy_chroma_readonly/`：旧 Chroma/历史向量库只读迁移区。

## 对标开源方案要点

- RAGFlow：文档解析、OCR、表格/版面感知 ingestion。
- LlamaIndex：Document/Node/Index 抽象、metadata filter。
- LangChain：retriever/agent 编排。
- Haystack：pipeline 与评估机制。
- Qdrant/Milvus/Weaviate/Chroma：向量存储与结构化过滤。
- GraphRAG/LightRAG：图谱 + 向量混合检索。

## 法律业务硬规则

- 法律法规：按法/编/章/节/条/款/项切分，保留效力状态、版本日期、发布机关和法域。
- 指导案例：按裁判要旨、争议焦点、事实、理由、裁判结果、案由、法院层级建 metadata。
- 本地办案沉淀：必须带案件号、阶段、保密级别、证据类型、争议焦点。
- 通讯录/机构位置：适合结构化实体库 + 地理字段，不宜只做普通向量。
- 回答必须可追溯到 source path / URL / doc_id；无来源不得入库。

## 验证字段

清理后至少验证：

- 被删目录存在性为 false；
- sessions 当前文件数与大小；
- 旧向量库顶层不存在，新 `法律知识向量库` 存在；
- catalog.sqlite3 至少包含 `documents`、`chunks`、`sources` 表；
- Gateway 状态仍 loaded；
- 报告路径和 JSON 证据文件存在。
