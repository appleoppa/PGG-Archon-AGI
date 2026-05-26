# Agent Skills × APEX 融合框架

## 摘要

将addyosmani/agent-skills的22个技能与璇玑帝国APEX公式融合，打造"工程级AI开发闭环"。

---

## 核心映射

| Agent Skills | APEX维度 | 融合 |
|--------------|----------|------|
| DEFINE阶段 | Ξ(创造力) | 需求→Spec |
| PLAN阶段 | E_xp(探索) | 任务分解 |
| BUILD阶段 | K(技能) | 增量实现 |
| VERIFY阶段 | ε(自修复) | 测试验证 |
| REVIEW阶段 | Γ(博弈) | 代码审查 |
| SHIP阶段 | Kelly(风险) | 安全发布 |

---

## 7大命令 × APEX闭环

```
DEFINE(ξ) → PLAN(E_xp) → BUILD(K) → VERIFY(ε) → REVIEW(Γ) → SHIP(Kelly)
     ↓            ↓            ↓           ↓            ↓           ↓
  Spec文件     任务分解     增量切片    测试驱动      代码审查     上线
```

---

## 22技能 × APEX映射

### Meta层
| 技能 | APEX维度 | 融合点 |
|------|----------|--------|
| using-agent-skills | Ξ×E_xp | 任务识别→公式代入 |

### Define层
| 技能 | APEX维度 | 融合点 |
|------|----------|--------|
| idea-refine | Ξ(创造力) | 发散→收敛 |
| spec-driven-development | Ξ+Γ | PRD规范 |

### Plan层
| 技能 | APEX维度 | 融合点 |
|------|----------|--------|
| planning-and-task-breakdown | E_xp | 垂直切片、依赖图 |

### Build层
| 技能 | APEX维度 | 融合点 |
|------|----------|--------|
| incremental-implementation | K+ε | 增量切片、循环验证 |
| test-driven-development | ε | Red-Green-Refactor |
| context-engineering | Θ+Ψ | 上下文管理 |
| source-driven-development | Γ | 源码溯源 |
| doubt-driven-development | Γ+Kelly | 质疑驱动 |
| frontend-ui-engineering | K | 前端技能 |
| api-and-interface-design | K+Γ | API契约设计 |

### Verify层
| 技能 | APEX维度 | 融合点 |
|------|----------|--------|
| browser-testing-with-devtools | ε | 运行时验证 |
| debugging-and-error-recovery | ε | 五步调试法 |

### Review层
| 技能 | APEX维度 | 融合点 |
|------|----------|--------|
| code-review-and-quality | Γ | 五轴审查 |
| code-simplification | Λ_ctx | 简化降熵 |
| security-and-hardening | Kelly | 安全边界 |
| performance-optimization | RD | 率失真优化 |

### Ship层
| 技能 | APEX维度 | 融合点 |
|------|----------|--------|
| git-workflow-and-versioning | Λ_ctx | Git原子提交 |
| ci-cd-and-automation | Π | 并行自动化 |
| deprecation-and-migration | Ξ | 迁移管理 |
| documentation-and-adrs | Ξ | ADR文档化 |
| shipping-and-launch | Kelly | 上线风控 |

---

## APEX-Skills融合公式

### Ξ(创造力)融合
```
Ξ = ξ_idea × ξ_spec × ξ_plan
   = (N_novel/N_total) × (spec_quality) × (task_breakdown)
```

### E_xp(探索)融合
```
E_xp = e_plan × e_build × e_verify
     = (垂直切片数) / (总任务数) × (构建速度) × (验证通过率)
```

### Γ(博弈)融合
```
Γ = γ_review × γ_security × γ_performance
  = (审查严格度) × (安全评分) × (性能达标率)
```

---

## 关键工程原则

### 1. Surface Assumptions（暴露假设）
```
每次实现前显式声明ASSUMPTIONS
防止隐性错误扩散
```

### 2. Manage Confusion Actively（主动管理困惑）
```
遇到不一致 → STOP → 命名困惑 → 呈现权衡 → 等待解决
```

### 3. Push Back When Warranted（合理质疑）
```
不做Yes-machine
直接指出问题 + 量化代价 + 提出替代方案
```

### 4. Enforce Simplicity（强制简洁）
```
代码行数 vs 功能交付
prefer boring solution over clever
```

### 5. Maintain Scope Discipline（保持范围纪律）
```
只动该动的文件
不"清理"无关代码
```

---

## 增量闭环

```
Implement → Test → Verify → Commit → Next Slice
    ↑                                      ↓
    ←────────────── Loop ◄────────────────┘
```

每次循环都是一个完整的vertical slice，APEX维度同时提升。

---

## 来源

- Agent Skills: addyosmani/agent-skills (MIT License)
- APEX Framework: ApexSpiral/apex-spiral

*融合版本 © 2026 璇玑帝国*
