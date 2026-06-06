---
name: skill-law-database
description: |
  九章法律AI帝国 - 法律法规库底座

  核心基础设施，为全部36个法律技能提供统一、权威、实时更新的法律法规数据。
  采用「底座+引用」架构，确保法规版本一致性，避免重复建设。

  功能：
  1. 统一管理所有现行有效法律法规
  2. 自动更新法规版本（废止/修订/新法）
  3. 提供API供其他技能引用
  4. 法规与案例自动关联

  使用方式：
  - 案例引用：applicable_laws: ["LAW-CIVIL-2020-001:第103条"]
  - 全文调取：jiuzhang-cli law get LAW-CIVIL-2020-001
  - 版本检查：jiuzhang-cli law check --date 2024-01-01
---

# 法律法规库底座

九章法律AI帝国的「法典基石」，36技能共享的权威法规数据源。

## 核心定位

**不是技能，是基础设施**
- 类似操作系统内核，为上层应用（法律技能）提供基础服务
- 所有案例的`applicable_laws`字段必须引用此底座
- 一处更新，全技能同步

## 法规分类体系

### 1. 宪法及根本法
- 宪法
- 立法法
- 监察法

### 2. 民法商法
- 民法典（7编+附则）
- 公司法
- 合伙企业法
- 破产法
- 证券法
- 保险法
- 票据法
- 海商法

### 3. 行政法
- 行政处罚法
- 行政许可法
- 行政强制法
- 行政复议法
- 行政诉讼法
- 国家赔偿法

### 4. 经济法
- 反垄断法
- 反不正当竞争法
- 消费者权益保护法
- 产品质量法
- 价格法
- 广告法
- 税法体系（增值税/企业所得税/个人所得税等）
- 银行法
- 外汇管理条例

### 5. 社会法
- 劳动法
- 劳动合同法
- 社会保险法
- 安全生产法
- 环境保护法
- 可再生能源法
- 节约能源法
- 职业病防治法

### 6. 刑法
- 刑法（2020修正）
- 刑事诉讼法

### 7. 诉讼与非诉讼程序法
- 民事诉讼法
- 仲裁法
- 人民调解法
- 劳动争议调解仲裁法
- 农村土地承包经营纠纷调解仲裁法

### 8. 专门领域法规

#### AI与数据
- 网络安全法
- 数据安全法
- 个人信息保护法
- 算法推荐管理规定
- 深度合成管理规定
- 生成式AI服务管理暂行办法

#### 芯片与出口管制
- 出口管制法
- 对外贸易法
- 技术进出口管理条例
- 集成电路布图设计保护条例

#### 新能源
- 可再生能源法
- 电力法
- 节约能源法
- 碳排放权交易管理办法
- 新能源汽车产业发展规划

## 法规数据格式

```json
{
  "id": "LAW-CIVIL-2020-001",
  "code": "民法典",
  "full_name": "中华人民共和国民法典",
  "category": "民法商法",
  "sub_category": "民法典",
  "level": "法律",
  "issuer": "全国人民代表大会",
  "issue_date": "2020-05-28",
  "effective_date": "2021-01-01",
  "status": "现行有效",
  "version": "2020",
  "articles": [
    {
      "number": "第103条",
      "title": "隐私权",
      "content": "自然人享有隐私权...",
      "keywords": ["隐私权", "个人信息", "保护"],
      "related_cases": ["ALG-001", "ALG-002"]
    }
  ],
  "amendments": [
    {
      "date": "2020-05-28",
      "content": "通过",
      "previous_version": null
    }
  ],
  "abolished_articles": [],
  "related_laws": ["LAW-CIVIL-1986-001", "LAW-PERSONAL-INFO-2021-001"],
  "tags": ["民事", "权利", "基础法"],
  "source_url": "http://www.npc.gov.cn/...",
  "last_updated": "2024-03-24",
  "update_frequency": "实时"
}
```

## API接口

### 查询法规
```bash
# 按ID获取
jiuzhang-cli law get LAW-CIVIL-2020-001

# 按名称搜索
jiuzhang-cli law search "算法推荐"

# 按类别查询
jiuzhang-cli law list --category "AI与数据"

# 获取特定条款
jiuzhang-cli law article LAW-CIVIL-2020-001 --number "第103条"

# 检查法规时效性
jiuzhang-cli law check LAW-CIVIL-2020-001 --date 2024-01-01
```

### 引用法规（在案例中使用）
```json
{
  "applicable_laws": [
    "LAW-CIVIL-2020-001:第103条",
    "LAW-PERSONAL-INFO-2021-001:第13条",
    "LAW-ALGORITHM-2022-001:全文"
  ]
}
```

### 自动关联
```bash
# 将法规与案例关联
jiuzhang-cli law link LAW-CIVIL-2020-001 --case ALG-001

# 查看某法规被哪些案例引用
jiuzhang-cli law cases LAW-CIVIL-2020-001
```

## 与其他底座的关系

```
┌─────────────────────────────────────┐
│      法律法规库底座 (skill-law-db)    │
│      36技能共享的权威法规源           │
└─────────────────────────────────────┘
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
┌──────────┐      ┌──────────┐
│ validator │      │ transfer │
│ 校验法条 │      │ 迁移知识 │
│ 有效性   │      │ 通用规则 │
└──────────┘      └──────────┘
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
┌──────────┐      ┌──────────┐
│  技能A   │      │  技能B   │
│案例引用  │      │案例引用  │
│法规条款  │      │法规条款  │
└──────────┘      └──────────┘
```

## 数据来源

- **国家法律法规数据库**: https://npc.gov.cn
- **北大法宝**: https://www.pkulaw.com
- **国家知识产权局**: https://www.cnipa.gov.cn
- **各部门官网**: 司法部、工信部、生态环境部等

## 更新机制

### 自动更新
- 每日凌晨同步最新法规
- 监测法规废止/修订公告
- 自动标记失效条款
- 推送更新通知到36技能

### 版本管理
- 保留历史版本
- 支持时点查询（某日期适用的法规版本）
- 案例引用锁定版本（确保可追溯性）

## 使用方法

### 在案例中引用
```json
{
  "id": "ALG-001",
  "title": "算法推荐违规案",
  "applicable_laws": [
    "LAW-ALGORITHM-2022-001:第7条",
    "LAW-ALGORITHM-2022-001:第15条"
  ],
  "compliance_insights": "违反《算法推荐管理规定》第7条..."
}
```

### 在技能中调用
```python
# 获取法规全文
law = jiuzhang.law.get("LAW-CIVIL-2020-001")

# 检查法条是否现行有效
is_valid = jiuzhang.law.check("LAW-CIVIL-2020-001", date="2024-01-01")

# 搜索相关法规
laws = jiuzhang.law.search("个人信息", category="AI与数据")
```

## 目录结构

```
skill-law-database/
├── SKILL.md                    # 本文件
├── law-database.json           # 法规主库（精简版）
├── laws/                       # 法规全文目录
│   ├── constitutional/         # 宪法
│   ├── civil/                  # 民法
│   ├── criminal/               # 刑法
│   ├── administrative/         # 行政法
│   ├── economic/               # 经济法
│   ├── social/                 # 社会法
│   ├── procedure/              # 程序法
│   ├── ai-data/                # AI与数据
│   ├── chip-export/            # 芯片与出口管制
│   └── new-energy/             # 新能源
├── scripts/
│   ├── sync.py                 # 法规同步脚本
│   ├── validate.py             # 法规有效性校验
│   ├── search.py               # 法规搜索
│   └── api.py                  # API服务
└── references/
    ├── data-sources.md         # 数据源清单
    ├── update-log.md           # 更新日志
    └── api-docs.md             # API文档
```

## 关键指标

- **法规总数**: 目标1000+部
- **条款总数**: 目标10万+条
- **更新频率**: 实时/每日
- **API响应**: <100ms
- **覆盖率**: 100%（36技能全部引用）

## 飞轮效应

```
法规底座更新 → 36技能同步更新 → 案例引用更准确
    ↑                                      ↓
用户反馈法规问题 → 底座修正 → 全技能受益
```

---
**版本**: 1.0.0
**作者**: 九章法律AI团队
**分类**: infrastructure
**地位**: 帝国36技能的「法典基石」
