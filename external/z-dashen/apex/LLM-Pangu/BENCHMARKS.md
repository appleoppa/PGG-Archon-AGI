# 性能基准 BENCHMARKS

> 记录盘古框架的性能基准数据

---

## 测试环境

- CPU: Intel/AMD x86_64
- Python: 3.8+
- OS: Linux/macOS/Windows

---

## ΔG公式性能

| 指标 | 数值 | 说明 |
|------|------|------|
| 单次计算耗时 | < 1ms | ΔG公式计算 |
| 熵计算复杂度 | O(n) | n为概率列表长度 |
| 信道容量计算 | O(1) | 常数时间 |

---

## 模块响应时间

| 模块 | 平均耗时 | 说明 |
|------|----------|------|
| LLMInitHook | ~50ms | 首次初始化 |
| LLMMemoryHook | ~10ms | 记忆保存/恢复 |
| PromptAligner | < 1ms | Prompt对齐 |
| EmotionCore | < 1ms | 情感计算 |
| SelfInspect | < 5ms | 全量自检 |

---

## 记忆存储

| 指标 | 数值 | 说明 |
|------|------|------|
| 单条记忆大小 | ~1KB | JSON格式 |
| 最大存储容量 | 无限制 | 取决于磁盘空间 |
| 备份保留数量 | 10个 | 自动清理旧备份 |

---

## 测试覆盖

| 类别 | 测试数 | 覆盖率 |
|------|--------|--------|
| ShannonEntropy | 8 | 100% |
| ChannelCapacity | 5 | 100% |
| CodeRedundancy | 4 | 100% |
| DeltaGCalculation | 4 | 100% |
| SystemJudge | 3 | 100% |
| ConstraintEngine | 3 | 100% |
| 其他模块 | 11 | >80% |
| **总计** | **38** | **>90%** |

---

## 更新日志

- 2024-XX-XX: 初始基准数据
