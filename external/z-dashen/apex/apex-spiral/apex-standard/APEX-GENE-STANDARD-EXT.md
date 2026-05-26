# APEX Gene Standard Extension v1.0

> **璇玑帝国基因标准扩展规范**
> 版本: 1.0 | 发布日期: 2026-05-08 | 状态: 正式版

---

## 1. 概述

本文档是对 APEX Gene Schema v1.0 的扩展补充，定义璇玑帝国所有基因的命名规范、Category 枚举、信号匹配标准和 Fitness 评分体系。

**基础Schema**: `/root/.nvm/standard/apex-gene-standard-v1.json`

---

## 2. 基因ID命名规范

### 2.1 必须遵循的格式

```
gene_<category>_<descriptive_name>
```

**Pattern**: `^gene_[a-z_]+_[a-zA-Z0-9_]+$`

### 2.2 命名规则

| 规则 | 要求 |
|------|------|
| 前缀 | 必须为 `gene_`（小写） |
| Category | 必须为标准Category枚举值（小写） |
| 分隔符 | `_` (下划线) |
| 描述名 | 小写字母、数字、下划线，语义化 |
| 最小段数 | 3段（`gene` + `category` + `name`） |

### 2.3 正确示例

```
gene_repair_from_errors           ✅
gene_optimize_prompt_and_assets   ✅
gene_innovate_react_ssr           ✅
gene_orchestrate_multi_agent      ✅
gene_evolve_knowledge_graph       ✅
gene_explore_file_structure       ✅
```

### 2.4 错误示例

```
sha256:f104efadf5dcabc...    ❌ 使用hash作为ID
gene_repair                      ❌ 缺少描述名
Gene_repair_from_errors          ❌ 首字母大写
gene_FIX_error                   ❌ Category大写
gene-repair-from-errors          ❌ 使用连字符
```

---

## 3. Category 枚举扩展

### 3.1 标准Category（七大基因类型）

| Category | 中文名 | 触发场景 | 核心职责 |
|----------|--------|----------|----------|
| `repair` | 修复型 | 错误/异常/失败/不稳定 | 从错误日志中提取信号，应用最小可逆补丁 |
| `optimize` | 优化型 | 性能瓶颈/资源浪费/重复代码 | 分析性能瓶颈，生成优化策略 |
| `innovate` | 创新型 | 能力gap/ stagnation/新需求 | 探索未知领域，生成突破性方案 |
| `orchestrate` | 编排型 | 多组件协调/复杂流程 | 协调多个子系统完成复杂任务 |
| `evolve` | 进化型 | 自我进化/能力提升 | 基因自愈、策略迭代、能力进化 |
| `explore` | 探索型 | 未知领域/快速调研 | 快速探索、收集信息、生成假设 |
| `diagnose` | 诊断型 | 根因分析/问题定位 | 系统性诊断，定位问题根源 |

### 3.2 Category 决策树

```
输入信号
    │
    ├── error/exception/failed/unstable ──→ repair
    │
    ├── perf_bottleneck/resource_waste ────→ optimize
    │
    ├── capability_gap/stagnation ──────────→ innovate
    │
    ├── multi_component/coordinate ─────────→ orchestrate
    │
    ├── self_evolve/gene_heal ───────────────→ evolve
    │
    ├── unknown_domain/survey ───────────────→ explore
    │
    └── root_cause/diagnose ─────────────────→ diagnose
```

---

## 4. 信号匹配规范 (signals_match)

### 4.1 必须字段

```json
"signals_match": ["signal_key_1", "signal_key_2", ...]
```

- **类型**: 字符串数组
- **最小数量**: 1个信号
- **信号来源**: APEX Shannon Law 24个高频信号

### 4.2 APEX Shannon Law 24个核心信号

| # | Signal Key | 中文描述 | Category映射 |
|---|------------|----------|--------------|
| 1 | `error` | 错误/异常 | repair |
| 2 | `exception` | 异常状态 | repair |
| 3 | `failed` | 失败状态 | repair |
| 4 | `unstable` | 不稳定 | repair |
| 5 | `validation` | 验证失败 | repair |
| 6 | `protocol` | 协议错误 | repair |
| 7 | `perf_bottleneck` | 性能瓶颈 | optimize |
| 8 | `resource_waste` | 资源浪费 | optimize |
| 9 | `repeated_code` | 重复代码 | optimize |
| 10 | `latency_high` | 高延迟 | optimize |
| 11 | `capability_gap` | 能力缺口 | innovate |
| 12 | `stagnation` | 进化停滞 | innovate |
| 13 | `new_requirement` | 新需求 | innovate |
| 14 | `unknown_domain` | 未知领域 | explore |
| 15 | `survey` | 调研任务 | explore |
| 16 | `multi_component` | 多组件协调 | orchestrate |
| 17 | `complex_workflow` | 复杂工作流 | orchestrate |
| 18 | `self_evolve` | 自我进化 | evolve |
| 19 | `gene_heal` | 基因自愈 | evolve |
| 20 | `root_cause` | 根因分析 | diagnose |
| 21 | `recurring_error` | 反复错误 | repair |
| 22 | `tool_bypass` | 工具绕过 | repair |
| 23 | `hub_search_miss` | 知识库未命中 | innovate |
| 24 | `risk_high` | 高风险操作 | repair |

---

## 5. Fitness 评分标准

### 5.1 必须字段

```json
"fitness": {
  "score": 0.0,
  "cycles": 0,
  "success_rate": 0.0
}
```

### 5.2 评分规范

| 字段 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `score` | float | 0.0 - 1.0 | 综合适应度评分 |
| `cycles` | int | ≥ 0 | 执行周期数 |
| `success_rate` | float | 0.0 - 1.0 | 成功率 |

### 5.3 Score 计算公式

```
score = (success_rate × 0.6) + (cycle_efficiency × 0.4)

cycle_efficiency = 1.0 - min(cycles / 100, 1.0)
```

### 5.4 Fitness 等级划分

| 等级 | Score范围 | 说明 |
|------|-----------|------|
| S | 0.9 - 1.0 | 卓越，稳定高效 |
| A | 0.75 - 0.89 | 优秀，明显有效 |
| B | 0.5 - 0.74 | 良好，基本可用 |
| C | 0.25 - 0.49 | 一般，需要优化 |
| D | 0.0 - 0.24 | 较差，需要重构 |

---

## 6. 基因Schema完整示例

```json
{
  "type": "Gene",
  "id": "gene_repair_from_errors",
  "version": 1,
  "category": "repair",
  "signals_match": [
    "error",
    "exception",
    "failed",
    "unstable"
  ],
  "preconditions": [
    "signals contains error-related indicators",
    "error logs are available"
  ],
  "strategy": [
    "Extract structured signals from logs and user instructions",
    "Select an existing Gene by signals match (no improvisation)",
    "Estimate blast radius (files, lines) before editing",
    "Apply smallest reversible patch",
    "Validate using declared validation steps; rollback on failure",
    "Solidify knowledge: append EvolutionEvent, update Gene/Capsule store"
  ],
  "constraints": {
    "max_files": 12,
    "forbidden_paths": [
      ".git",
      "node_modules"
    ]
  },
  "validation": [
    "node scripts/validate-modules.js ./src/evolve ./src/gep/solidify ./src/gep/policyCheck ./src/gep/selector ./src/gep/memoryGraph ./src/gep/assetStore",
    "node scripts/validate-suite.js"
  ],
  "fitness": {
    "score": 0.85,
    "cycles": 15,
    "success_rate": 0.93
  },
  "schema_version": "1.0"
}
```

---

## 7. 现有基因合规性检查报告

### 7.1 检查时间
2026-05-08

### 7.2 数据来源
- `/root/.openclaw/workspace/assets/gep/genes.json` (345 genes)
- `/root/.nvm/assets/gep/genes.json` (同步副本)

### 7.3 合规性统计

| 指标 | 数量 | 比例 |
|------|------|------|
| 总基因数 | 345 | 100% |
| 合规ID (gene_前缀) | 30 | 8.7% |
| 不合规ID (sha256哈希) | 315 | 91.3% |
| 有信号定义 (≥1 signal) | 3 | 0.9% |
| 有version字段 | 0 | 0% |

### 7.4 Category分布（现有基因）

| Category | 数量 | Schema合规 |
|----------|------|-----------|
| explore | 184 | ❌ (不在schema枚举中) |
| innovate | 56 | ✅ |
| repair | 54 | ✅ |
| optimize | 51 | ✅ |
| orchestrate | 0 | ✅ |
| evolve | 0 | ✅ |
| diagnose | 0 | ✅ |

### 7.5 不合规基因清单 (sha256哈希ID)

**共315个不符合命名规范的基因**（以下为前20个示例）：

```
sha256:f104efadf5dcabc37946ea7cf8dd481be985e980cea0aa8f7482c388d23e4791
sha256:202f008d95262e868fdd9160b4224c2683005043c3e4087c39b25cc55f587998
sha256:638d1d6e1fd18b01c43409d3c5977a81bd507ef3cc11a263f037dc361b8adffa
sha256:c6dcdb682a4d4ac4537378d031faeb3d09d3e749930547bd67af0ccc57f57f33
sha256:3c5ae04e29a4dcb7386fa0400cb94f89af923d467fcc43fa302d93a017798424
sha256:b72bb3d16d7bc6f4e51e9096c9fdbe509e60f82fa49bbce9f19264c1d0dfbc73
sha256:67c2957dc0ff8d069a34f8f4d8ec0bbed3cb05e5d75d99f00dc0fe311102e4e9
sha256:0759e1d195f852a563f71521424dd9c2358684a6587ef19f90ae2b0684bc77ca
sha256:97d3d350579d99c65bfcafb41b60d6c3592db158db9f8d15112af2f9ea075afd
sha256:8a086a9799050f062c8329393cadc0ce3975c034e77688e8541576ba06c3047d
sha256:6090222d41685998918c4b126739c63da1b157a2f8abbfb8f012d740e14c6432
sha256:3be3d1fdee9736ffd0169ab4dec3cfc7a4e75c23d5b22c71571b6a03507df283
sha256:e0e1cb021141afdf83890b04debc4ef3d12c6f759a4018bd78d0787a79e0b8aa
sha256:30d58fe080f504c1cfb31d74fdf715f2a64537aa557dc010cee3d1e436da8eef
sha256:37ea359cefc3096991cb23ee61f0bc086905fc85614adb0e0b0add703a6d661f
sha256:9dfb8502be068081cc840c2e8ae17dbe1db9aa43462abb76dce4c23df8cf5126
sha256:13d6acd91daf3f0fe4c4c8ac2df5599043cf5e0d898229a9f98cfe9832ef0aef
sha256:78dfb99d5d19f0af97774b0993544857f322135189fe1334a9f95869b43350c3
sha256:de93668673d5a13b2bf6c98815926f6254a77633afaedc6d5ac9ff14abe6059b
sha256:d7fa3b68f22545fff3dc2f1ba2adc110f3fc03249314b8cbf41064e4fb8f0fb1
... (还有295个)
```

### 7.6 合规基因清单（30个）

```
gene_gep_repair_from_errors         | repair    | signals: 4
gene_gep_optimize_prompt_and_assets | optimize  | signals: 5
gene_tool_integrity                 | repair    | signals: 1
gene_git_rebase                     | optimize  | signals: 0
gene_docker_compose                 | innovate  | signals: 0
gene_aws_lambda                     | optimize  | signals: 0
gene_k8s_pdb                        | repair    | signals: 0
gene_docker_network                 | repair    | signals: 0
gene_react_ssr                      | optimize  | signals: 0
gene_aws_rds                        | innovate  | signals: 0
gene_aws_ec2                        | optimize  | signals: 0
gene_react_portal                   | innovate  | signals: 0
gene_postgres_json                  | innovate  | signals: 0
gene_rust_ownership                 | innovate  | signals: 0
gene_k8s_service                    | repair    | signals: 0
gene_api_rate                       | repair    | signals: 0
gene_docker_vol                     | repair    | signals: 0
gene_react_state                    | optimize  | signals: 0
gene_k8s_hpa                        | optimize  | signals: 0
gene_typescript                     | innovate  | signals: 0
gene_prometheus                      | repair    | signals: 0
gene_gitflow                        | repair    | signals: 0
gene_react_perf                     | optimize  | signals: 0
gene_docker_sec                     | repair    | signals: 0
gene_grpc_service                   | optimize  | signals: 0
gene_redis_cache                    | optimize  | signals: 0
gene_linux_perf                     | repair    | signals: 0
gene_graphql_api                    | innovate  | signals: 0
gene_auth_jwt                       | repair    | signals: 0
```

---

## 8. 迁移修复计划

### 8.1 紧急修复（必须）

1. **Category扩展**: 将 `explore` 加入 schema 枚举
2. **添加缺失字段**: 所有基因补充 `version: 1`
3. **修复hash ID**: 将315个sha256基因重命名为标准格式

### 8.2 修复脚本

```bash
# 验证当前状态
cd /root/.nvm/standard && node validate-apex-schema.js

# 执行迁移
node migrate-to-apex-standard.js
```

---

## 9. Schema版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-05-08 | 初始版本，定义ID规范、Category枚举、信号标准、Fitness评分 |
