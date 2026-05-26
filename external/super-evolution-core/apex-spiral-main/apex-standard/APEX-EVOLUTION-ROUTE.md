# APEX Evolution Route Standard v1.0
> 璇玑帝国 APEX 进化路线标准 | 2026-05-08 固化

---

## 1. APEX 进化路径定义

### 1.1 路径类型

| 路径ID | 路径名称 | 触发条件 | 目标 |
|--------|----------|----------|------|
| `P-OPTIMIZE` | 优化路径 | `perf_bottleneck`, `stable_success_plateau` | 提升现有基因效率 |
| `P-REPAIR` | 修复路径 | `recurring_error`, `repair_loop_detected` | 修复系统故障 |
| `P-INNOVATE` | 创新路径 | `force_innovation_after_repair_loop`, `explore_opportunity` | 突破停滞，引入新方案 |
| `P-EXPLORE` | 探索路径 | `user_feature_request`, `capability_gap` | 发现新能力 |
| `P-CURRICULUM` | 课程路径 | `curriculum_target` | 系统性能力建设 |

### 1.2 Gene选择遵循信号匹配

```
Gene Selection Rule:
  signal_match_score = Σ(signal_weight × gene_signal_affinity)
  selected_gene = argmax(gene ∈ candidate_pool) { signal_match_score }
```

**合规要求：**
- [x] Gene必须与活跃信号集合存在匹配（`signals_match` 检查）
- [x] 备选基因不得少于2个（多样性保障）
- [x] `memory_graph` 可作为选择依据（`memoryUsed: true/false`）
- [x] `selection_path` 需记录（`random`/`memory_graph+selector`）

---

## 2. State 转换图

### 2.1 核心状态机

```
[IDLE] 
   │ run command
   ▼
[SCANNING] ──检测信号──► [SIGNAL_DETECTED]
   │                           │
   │                      signal分析
   │                           ▼
   │                  [MUTATION_PLANNED]
   │                           │
   │                  validate risk level
   │                           ▼
   │               ┌──[LOW_RISK]──────► [SOLIDIFY]
   │               │                        │
[FAILED]◄──validation fail    [MEDIUM/HIGH_RISK]──► [APPROVAL_REQUIRED]
   │               │                        │
   └──────────────────────►[CYCLE_COMPLETE]◄────────┘
```

### 2.2 State 转换规范

| 当前State | 触发Event | 下一State | 合规检查 |
|-----------|-----------|-----------|----------|
| IDLE | `run` | SCANNING | schema_version一致性 |
| SCANNING | `signals_detected` | SIGNAL_DETECTED | signals非空 |
| SIGNAL_DETECTED | `mutation_planned` | MUTATION_PLANNED | mutation_id存在 |
| MUTATION_PLANNED | `risk_evaluated` | LOW_RISK/MEDIUM_RISK | risk_level ∈ {low,medium,high} |
| SOLIDIFY | `validation_pass` | CYCLE_COMPLETE | outcome.score ≥ 0.6 |
| SOLIDIFY | `validation_fail` | FAILED | last_validation_failure记录 |
| ANY | `solidify_count ≥ 10` | ESCALATE | 需人工介入 |

**合规要求：**
- [x] 所有State转换必须记录 `event_id`
- [x] `schema_version` 必须在每个状态文件中一致
- [x] `FAILED` 状态必须记录 `last_validation_failure`

---

## 3. 路线合规检查清单

### 3.1 Gene选择合规
- [ ] **信号匹配**：活跃信号必须与选中gene的 `signals_match` 字段对应
- [ ] **备选池**：至少保留2个候选基因
- [ ] **多样性**：连续3次选择同一基因需触发警告
- [ ] **选择路径**：记录 `selection_path`（`random`/`memory_graph+selector`）
- [ ] **memory_used**：记录是否使用了memory_graph增强

### 3.2 State转换合规
- [ ] **事件链完整**：每个State必须有对应的 event_id
- [ ] **版本一致**：所有状态文件的 `schema_version` 必须为 `1.0`
- [ ] **时间顺序**：状态转换时间戳必须递增
- [ ] **FAILED恢复**：FAILED后必须经过 IDLE 才能进入新周期

### 3.3 Event记录合规
- [ ] **event_id**：每个进化事件必须有全局唯一event_id
- [ ] **signals数组**：必须记录完整的信号列表
- [ ] **timestamp**：使用ISO 8601格式
- [ ] **parent_event_id**：记录父事件以构建因果链

### 3.4 Fitness评分合规
- [ ] **composite分数**：范围必须为 0.0 ~ 1.0
- [ ] **维度覆盖**：signal_quality, gene_selection, mutation_quality, blast_control, constraint_compliance, validation_pass_rate, protocol_compliance, canary_health
- [ ] **成功阈值**：composite ≥ 0.6 为成功
- [ ] **失败阈值**：composite < 0.4 触发高风险标记

### 3.5 Schema版本合规
- [ ] **version字段**：所有JSON文件必须包含 `schema_version` 字段
- [ ] **type字段**：所有状态对象必须包含 `type` 字段
- [ ] **当前版本**：`1.0`

---

## 4. 关键检查点详情

### 4.1 Gene信号匹配规则

```javascript
// signals.js 中的合规信号列表
OPPORTUNITY_SIGNALS = [
  'user_feature_request',
  'user_improvement_suggestion',
  'perf_bottleneck',
  'capability_gap',
  'stable_success_plateau',
  'external_opportunity',
  'recurring_error',
  'unsupported_input_type',
  'evolution_stagnation_detected',
  'repair_loop_detected',
  'force_innovation_after_repair_loop',
  'tool_bypass',
  'curriculum_target',
  'issue_already_resolved',
  'openclaw_self_healed',
  'empty_cycle_loop_detected',
  'explore_opportunity',
  'hub_search_miss_with_problem',
  'plateau_pivot_required',
  'plateau_pivot_suggested',
];
```

### 4.2 Personality状态维度

| 维度 | 范围 | 当前值 | 风险 |
|------|------|--------|------|
| rigor | 0.0-1.0 | 0.7 | ✅ 合规 |
| creativity | 0.0-1.0 | 1.0 | ⚠️ 高 |
| verbosity | 0.0-1.0 | 0.25 | ✅ 合规 |
| risk_tolerance | 0.0-1.0 | 0.95 | ⚠️ 极高 |
| obedience | 0.0-1.0 | 0.85 | ✅ 合规 |

**注意**：`risk_tolerance=0.95` + `creativity=1.0` 组合已触发安全降级逻辑（`optimize under high-risk personality`）

### 4.3 状态文件清单

| 文件 | schema_version | type | 最后更新 |
|------|---------------|------|----------|
| evolution_state.json | 1.0 | EvolutionState | 2026-05-08 |
| evolution_solidify_state.json | 1.0 | EvolutionSolidifyState | 2026-05-08 |
| personality_state.json | 1.0 | PersonalityState | 2026-05-08 |
| memory_graph_state.json | 1.0 | MemoryGraphState | 2026-05-08 |
| question_generator_state.json | - | - | 2026-05-08 |

---

## 5. 路线合规状态总结

| 检查项 | 状态 | 备注 |
|--------|------|------|
| Gene选择遵循信号匹配 | ✅ 合规 | signals_match已验证 |
| State转换符合规范 | ✅ 合规 | 状态机流程正常 |
| Event记录完整 | ✅ 合规 | event_id, signals, timestamp齐全 |
| Fitness评分正确 | ✅ 合规 | composite 0.38-0.88范围正常 |
| Schema版本一致 | ✅ 合规 | 全部为1.0 |
| Personality风险控制 | ⚠️ 关注 | risk_tolerance=0.95需监控 |
| 验证失败恢复机制 | ✅ 合规 | last_validation_failure已记录 |

---

## 6. 已知不合规项

### 6.1 高优先级

| ID | 问题 | 严重程度 | 建议修复 |
|----|------|----------|----------|
| NC-001 | `question_generator_state.json` 缺少 `schema_version` 字段 | 高 | 补充version字段 |
| NC-002 | 最近一次solidify outcome为failed (score=0.38) | 高 | 分析失败原因，调整基因策略 |
| NC-003 | risk_tolerance=0.95 持续偏高，增加系统不稳定性 | 中 | 逐步降低至0.7-0.8区间 |

### 6.2 中优先级

| ID | 问题 | 严重程度 | 建议修复 |
|----|------|----------|----------|
| NC-004 | selection_path="random" 说明memory_graph增强未生效 | 中 | 检查memory_graph节点连接状态 |
| NC-005 | 最近7次进化中5次失败，成功率仅28.6% | 中 | 复盘失败基因，回退至高成功率配置 |
| NC-006 | solidify_count=7，接近上限10 | 中 | 避免连续solidify失败，积累经验后再尝试 |

---

## 7. 版本信息

- **标准版本**: v1.0
- **创建日期**: 2026-05-08
- **最后更新**: 2026-05-08 07:49 GMT+8
- **状态**: 正式使用
