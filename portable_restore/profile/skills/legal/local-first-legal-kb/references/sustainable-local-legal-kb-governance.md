# 本地优先法律知识库可持续治理参考

## 适用场景

用于继续治理苹果中枢本地法律知识库时，快速恢复已经验证过的持续机制：统一 CLI、增量 watcher、nightly regression、指导案例/条文/文档回归。

## 核心入口

统一 CLI：

```bash
/Users/appleoppa/.hermes/bin/legal-kb doc --summary --collection 法律法规库 "劳动争议司法解释"
/Users/appleoppa/.hermes/bin/legal-kb doc --summary --collection 指导案例库 "指导案例184号 肖像权"
/Users/appleoppa/.hermes/bin/legal-kb article --summary --law-title "中华人民共和国民法典" --article-no "第五百七十七条" "违约责任"
```

兼容入口：

```bash
/Users/appleoppa/.hermes/bin/legal-kb-search --summary --collection 法律法规库 "法释〔2026〕10号 非法占用耕地"
/Users/appleoppa/.hermes/bin/legal-kb-article-search --summary --law-title "中华人民共和国民法典" --article-no "第五百七十七条" "违约责任"
```

## 增量 watcher

脚本：

```bash
python3 /Users/appleoppa/.hermes/workspace/法律知识向量库/04_ingestion/pipelines/local_kb_incremental_watcher.py
```

初始化 manifest：

```bash
python3 /Users/appleoppa/.hermes/workspace/法律知识向量库/04_ingestion/pipelines/local_kb_incremental_watcher.py --init
```

输出：

- `LOCAL_LEGAL_KB_FILE_MANIFEST.json`
- `ROUND19_INCREMENTAL_WATCHER_CHECK.json`

门槛：`added_count=0`、`deleted_count=0`、`modified_count=0` 代表本地官方库相对 manifest 无变化。

## Nightly regression

脚本：

```bash
python3 /Users/appleoppa/.hermes/workspace/法律知识向量库/05_quality/nightly_legal_kb_regression.py
```

cron wrapper：

```bash
/Users/appleoppa/.hermes/scripts/nightly_legal_kb_regression.sh
```

已验证的 cron 形态：

```bash
hermes cron create '30 2 * * *' \
  --name '本地法律知识库夜间回归(02:30)' \
  --deliver local \
  --script nightly_legal_kb_regression.sh \
  --no-agent \
  --workdir /Users/appleoppa/.hermes \
  --profile default
```

手动验证：

```bash
hermes cron run <job_id>
hermes cron tick
hermes cron list | grep -A14 '本地法律知识库夜间回归'
```

## 回归脚本与门槛

文档级 30 题：

```bash
python3 /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/round10_regression.py
```

文档级 100 题：

```bash
python3 /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/round11_expand_regression.py
```

条文级 100 题：

```bash
python3 /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/round15_article_100_regression.py
```

指导案例 100 题：

```bash
python3 /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/round18_guiding_case_100_regression.py
```

统一 CLI 烟测：

```bash
python3 /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/round16_unified_cli_regression.py
```

夜间总回归要求：6/6 PASS。

## 条文表清理模式

`law_articles_local` 可能从 `索引清单.json`、`目录索引.md` 误抽“第X条”片段。清理模式：

1. 统计条件：`title like '%索引%' or title like '%目录%' or source_path like '%.json' or source_path like '%目录索引.md'`。
2. 清理前创建备份表：`law_articles_local_indexlike_backup_时间戳`。
3. 删除对应误抽行。
4. 验证清理后误抽为 0，备份数量等于删除数量。
5. 报告写明可回滚备份表名。

## 汇报要求

报告必须写：

- 本地官方库规模；
- 回归总数、通过数、通过率；
- watcher 变化数；
- cron job ID/计划/最近验证；
- 边界：不能替代律师人工复核，外部公开源不覆盖本地主库。
