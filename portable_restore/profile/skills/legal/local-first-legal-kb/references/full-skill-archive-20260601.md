---
name: local-first-legal-kb
description: 本地优先法律知识库检索：调用苹果中枢本地官方指导案例库、法律法规库与条文级检索 CLI，避免外部公开源覆盖本地主库。
version: 1.0.0
created: 2026-06-01
---

# 本地优先法律知识库检索

## 触发条件

当任务需要检索：

- 最高人民法院指导案例；
- 本地法律法规库；
- 法释号、案例号、条文号；
- 民法典/公司法/破产法等条文；
- 办案流程中的法律依据初检。

优先使用本技能，不要直接用外部网页样例替代本地官方库。

## 数据边界

主库：

- `/Users/appleoppa/.hermes/workspace/智库/案例库`
- `/Users/appleoppa/.hermes/workspace/智库/法律法规库`
- `/Users/appleoppa/.hermes/workspace/法律知识向量库/catalog.sqlite3`

外部公开源只能作为 supplemental（补充来源）。

禁止采集或使用：

- 非公开内部通讯录；
- 绕过登录/验证码/权限的数据；
- 政务内网/专网数据；
- 未公开个人手机号或私人联系方式。

## Hermes 原生工具

当前已注册 Hermes native tool（原生工具）：

- toolset（工具集）：`legal_kb`
- tool（工具）：`local_legal_kb`
- alias（别名工具集）：`local_legal_kb`

支持 action：

1. `doc_search`：本地官方法规/指导案例文档级检索。
2. `article_search`：本地法律条文级检索。
3. `case_research_pack`：组合文档命中、条文命中、来源路径和边界说明，形成办案初检材料包。
4. `quality_status`：读取 catalog 计数、SQLite integrity、nightly regression 和 watcher 状态。

验证入口：

```bash
cd /Users/appleoppa/.hermes/hermes-agent
venv/bin/python -m pytest tests/tools/test_local_legal_kb_tool.py -q
venv/bin/python /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/native_legal_kb_toolchain_smoke.py
```

边界：该工具是办案初检和内部检索工具，不替代正式法律依据复核、现行有效性核验和律师判断。

## 统一 CLI

文档级检索：

```bash
/Users/appleoppa/.hermes/bin/legal-kb doc --summary --collection 法律法规库 "劳动争议司法解释"
/Users/appleoppa/.hermes/bin/legal-kb doc --summary --collection 指导案例库 "指导案例184号 肖像权"
```

条文级检索：

```bash
/Users/appleoppa/.hermes/bin/legal-kb article --summary --law-title "中华人民共和国民法典" --article-no "第五百七十七条" "违约责任"
/Users/appleoppa/.hermes/bin/legal-kb article --summary --law-title "中华人民共和国公司法" --article-no "第一条" "公司法"
```

兼容入口：

```bash
/Users/appleoppa/.hermes/bin/legal-kb-search --summary --collection 法律法规库 "法释〔2026〕10号 非法占用耕地"
/Users/appleoppa/.hermes/bin/legal-kb-article-search --summary --law-title "中华人民共和国民法典" --article-no "第五百七十七条" "违约责任"
```

## 当前规模

截至 2026-06-01：

- 本地官方资产：1257
- 指导案例：529
- 法律法规：728
- 本地条文：20404
- 指导案例字段：547
- 文档级100题回归：100/100
- 条文级100题回归：100/100

## 使用流程

1. 优先用 `legal-kb doc` 找法律/案例文件。
2. 涉及具体条文时，用 `legal-kb article` 精确到条。
3. 对外法律意见前，仍需人工/正式法律检索复核，不能把 CLI 命中直接当最终法律依据。
4. 报告中引用时写明来源路径和命中标题。

## 常见坑

1. `目录索引.md`、`索引清单.json` 会造成误抽或误命中；当前已降权并清理条文误抽。
2. 同一法律不同日期版本会抢位；查询中带日期时优先精确版本。
3. “司法解释”在标题中常写作“解释”；检索器已做兼容，但输出仍需核对。
4. 指导案例号优先于正文关键词。

## 验证命令

```bash
python3 /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/round16_unified_cli_regression.py
python3 /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/round15_article_100_regression.py
python3 /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/round18_guiding_case_100_regression.py
python3 /Users/appleoppa/.hermes/workspace/法律知识向量库/04_ingestion/pipelines/local_kb_incremental_watcher.py
python3 /Users/appleoppa/.hermes/workspace/法律知识向量库/05_quality/nightly_legal_kb_regression.py
```

通过门槛：

- unified CLI：4/4；
- article 100：100/100；
- guiding case 100：100/100；
- 文档级100：100/100；
- watcher：新增0、删除0、修改0；
- nightly regression：6/6 PASS。

## 持续治理

详见 `references/sustainable-local-legal-kb-governance.md`。该参考记录统一 CLI、增量 watcher、nightly regression、指导案例/条文/文档回归和条文表误抽清理模式。
