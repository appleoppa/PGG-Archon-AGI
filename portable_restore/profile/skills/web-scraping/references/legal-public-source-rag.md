# 法律/政务公开源采集 → 法律知识库/RAG 入库

适用：采集法院、检察院、公安、司法行政、法律法规、指导案例等**公开**网页，用于构建法律知识库、机构实体库、RAG 检索底座。

## 边界

允许：
- 官网公开页面、政府公开数据、公开地图 POI/机构地址。
- 用户合法持有资料的清洗、去重、分级、导入。

禁止：
- 非公开内部通讯录抓取。
- 绕过登录、验证码、权限、内网/政务专网/执法系统。
- 采集未公开个人手机号、私人联系方式。

## 推荐结构

不要把所有资料都“丢进向量库”。法律知识库应分层：

1. `sources`：来源登记，含 source_id、source_type、trust_level、update_policy。
2. `public_institution_entities`：机构实体库，含 name、entity_type、province/city/district、address、phone_public、official_url、lat/lon、source_url、confidence。
3. `legal_documents`：法规、案例、办案沉淀的统一元数据表。
4. `legal_relations`：法条—司法解释—案例—争议焦点—裁判规则关系图谱。
5. `kb_fts` / `kb_cjk_fts`：关键词检索与中文二/三元 CJK 检索。
6. vector index：向量检索只作为一层，需配合 metadata filter、BM25/FTS、rerank。

## 法律数据切分规则

- 法律法规：按“法 / 编 / 章 / 节 / 条 / 款 / 项”切分；必须保留版本、效力状态、发布机关、施行日期、来源 URL/path。
- 指导案例：提取案号/编号、案由、裁判要旨、关键词、争议焦点、裁判规则、法院层级、来源 URL。
- 本地办案沉淀：必须带 matter_id、案件阶段、证据类型、争议焦点、保密级别。
- 机构/通讯录/位置：优先实体库 + 地理字段；不要只做普通向量。

## 开源方案吸收点

- RAGFlow：文档解析、OCR、表格/版面感知 ingestion。
- LlamaIndex：Document → Node → Index 抽象，适合法规/案例分层。
- LangChain：retriever/agent 编排。
- Haystack：pipeline 和 evaluation。
- Qdrant/Milvus/Weaviate/Chroma：向量库与 metadata filter。
- GraphRAG/LightRAG：图谱 + 向量混合检索。

## 中文检索经验

SQLite FTS5 默认 `unicode61` 对中文多词查询容易过严或漏召回。实用补强：

1. 建 `kb_cjk_fts`，写入中文 bigram/trigram grams 字段。
2. 查询时先走集合过滤（collection metadata filter）。
3. 用 exact term bonus + CJK bigram overlap 做 fallback hybrid scorer。
4. 对法律结果必须输出 source_url/path/doc_id，不允许无来源回答。

## 执行顺序

1. 建公开源 registry，先写合法边界。
2. 抓首页/栏目页，保存可达性、title、final_url、clean_text。
3. 从公开链接发现法规、案例、机构入口，逐条验证。
4. 写 catalog：sources → entities/documents → FTS/CJK FTS → graph/vector 预留。
5. 做 smoke test：至少测试“法院/检察院/法律法规/指导案例/具体案例编号”。
6. 记录失败源的原因，但不要把临时 403/521/重定向写成永久不可用；下一轮换具体栏目、地方站点或 sitemap。
