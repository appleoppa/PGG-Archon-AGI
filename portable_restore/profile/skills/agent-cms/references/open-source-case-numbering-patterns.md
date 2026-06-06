# 开源案件/任务编号模式借鉴

## 触发场景

当苹果中枢评估或升级办案编号规则、案卷目录规则、Kanban task（任务）绑定规则、并发开案防重规则时，参考本文件。

## 已核验开源模式

### 1. AnikaLegal/clerk：内部主键与人类可读案号分离

核验点：`app/core/models/issue.py`。

关键模式：

- `id` 使用 UUID，作为不可变数据库主键；
- `fileref` 作为内部沟通用 file reference number（案卷引用号）；
- `fileref` 按案件 topic（主题）取前缀；
- 生成时查同前缀最后一个编号并 +1；
- 数字部分至少 4 位，不够时动态扩展；
- 示例形态：`R0023`、`C0001`。

可吸收点：

- 苹果中枢应保留 `case_uid`（UUID/ULID）作为不可变机器 ID；
- `case_no` 作为律师和用户可读编号；
- 不应把可读编号当成唯一持久主键。

### 2. makeplane/plane：项目标识 + 项目内 sequence_id + 并发锁

核验点：

- `ProjectIdentifier`：项目短标识；
- `Issue.sequence_id`：项目内递增序号；
- `IssueSequence`：记录序列；
- 创建时用 PostgreSQL advisory lock（数据库咨询锁）按 project 加锁，避免并发重复。

关键模式：

- 展示编号类似 `{project_identifier}-{sequence_id}`；
- 序号在 project 范围内递增；
- 生成编号时不是扫描文件夹，而是从持久化 sequence 表读写；
- 并发创建必须原子化。

可吸收点：

- 苹果中枢应维护独立编号账本，例如 SQLite `case_sequences` 或 JSON ledger（账本）；
- 并发开案时必须有文件锁/SQLite transaction（事务）/数据库锁；
- Kanban task graph（任务图）必须同时绑定 `case_no` 与 `case_uid`。

## 建议吸收为 V7.3 编号方向

### 主案编号

```text
PGG-{案件代码}-{YYYYMMDD}-{四位全局序号}
```

示例：

```text
PGG-MS-20260531-0001
```

### 内部不可变 ID

```text
case_uid = UUID / ULID
```

用于：

- `meta.json`；
- Kanban `handoff_metadata`；
- SQLite 台账；
- 归档索引；
- 未来目录重命名后的跨文件追踪。

### 子编号

```text
{主案编号}-MAT-{三位序号}      # 材料
{主案编号}-EV-{三位序号}       # 证据
{主案编号}-DOC-{三位序号}      # 文书
{主案编号}-TASK-{三位序号}     # Kanban任务
{主案编号}-AUDIT-{三位序号}    # 巡视/审计
```

### 隐私目录

敏感案件不应把当事人实名、身份证号、手机号、商业秘密直接写入稳定目录名。可用匿名目录：

```text
0001-PGGXS-20260531-匿名刑事辩护
0002-PGGMS-20260531-匿名-民间借贷纠纷
```

## 门禁规则

1. 编号权仍归案件管理中心 `pgg-anguan`，苹果中枢不得直接分配正式编号；
2. 展示编号可以重命名或升级格式，但 `case_uid` 不得改变；
3. 序号发放必须写入编号账本并读回验证；
4. 作废、重开、并案、拆案必须保留审计记录，不能静默复用旧号；
5. 未实现锁/账本前，不得宣称支持安全并发开案。
