# 超级进化9验证方法论

生成时间：2026-05-25
验证者：Claude-opus-4-7

---

## 核心目标

**EvoMaster 适配 CLAW 原生进化核心公式**：轨迹级自进化 + 知识永久沉淀 + 策略自更新

---

## 六维度验证标准

| 维度 | 验证内容 | 通过标准 |
|---|---|---|
| **1. 公式吸收** | 三大核心公式是否转化为可执行规则 | 迭代进化总目标、策略自更新、知识缓存压缩三个公式均有 Hermes 可执行解释 |
| **2. 模块创建** | Python/Rust 模块是否存在且可导入 | `evo_master.py` 可导入，包含 `KnowledgeCache`、`EvoMaster`、`Trajectory`、`Strategy` 类 |
| **3. Sidecar 实现** | 旁路脚本是否可执行且有工作区 | `hermes_trace_hashpool.py` 可执行，工作区包含 `hashpool.jsonl`、`skill_candidates/`、`failure_examples/`、`reports/` |
| **4. 主链路集成** | 是否集成到 Hermes 核心 | 检查 `run_agent.py`、`model_tools.py`、`tools/` 是否引用；是否注册为 Hermes 工具 |
| **5. 自动化** | 是否有 cron 或后台任务 | 检查 `hermes cronjob list` 是否有相关任务 |
| **6. 真实数据积累** | 是否有真实轨迹池 | 检查 `hashpool.jsonl` 行数、有效轨迹数、技能候选数 |

---

## 验证命令模板

### 1. 公式吸收验证

```bash
# 读取原文
cat /Users/appleoppa/Desktop/进化文件/超级进化/超级进化9-原生进化核心公式释义.md

# 读取吸收报告
cat ~/.hermes/workspace/开智/超级进化9-原生进化核心公式吸收报告.md
```

**通过标准**：吸收报告包含三大公式的 Hermes 可执行解释，且明确落地边界。

---

### 2. 模块创建验证

```bash
# 检查 evo_master.py
cd ~/.hermes/hermes-agent
python3 -c "import evo_master; print('✅ 可导入'); print(f'KnowledgeCache: {hasattr(evo_master, \"KnowledgeCache\")}'); print(f'EvoMaster: {hasattr(evo_master, \"EvoMaster\")}')"

# 检查 trace_hashpool.py
cd ~/.hermes/scripts
python3 hermes_trace_hashpool.py --help
```

**通过标准**：
- `evo_master.py` 可导入，包含 `KnowledgeCache`、`EvoMaster`、`Trajectory`、`Strategy` 类
- `hermes_trace_hashpool.py` 可执行，显示帮助信息

---

### 3. Sidecar 工作区验证

```bash
# 检查工作区结构
ls -lh ~/.hermes/workspace/trace_hashpool/

# 检查 hashpool 内容
wc -l ~/.hermes/workspace/trace_hashpool/hashpool.jsonl
head -1 ~/.hermes/workspace/trace_hashpool/hashpool.jsonl | python3 -m json.tool

# 检查技能候选
ls ~/.hermes/workspace/trace_hashpool/skill_candidates/

# 检查失败反例
ls ~/.hermes/workspace/trace_hashpool/failure_examples/

# 检查报告
ls ~/.hermes/workspace/trace_hashpool/reports/
```

**通过标准**：
- 工作区包含 `hashpool.jsonl`、`skill_candidates/`、`failure_examples/`、`reports/` 四个目录
- `hashpool.jsonl` 至少有1条有效记录
- 记录包含 `hash`、`task_goal`、`actions_taken`、`verification`、`pass` 字段

---

### 4. 主链路集成验证

```bash
# 检查 Hermes 核心引用
cd ~/.hermes/hermes-agent
grep -r "from evo_master import\|import evo_master" . 2>/dev/null

# 检查工具注册
grep -r "evo_master\|trace_hashpool\|EvoMaster" tools/ 2>/dev/null

# 检查数据库初始化
ls -lh ~/.hermes/workspace/evo_master_db/ 2>/dev/null || echo "数据库目录不存在"
```

**通过标准**：
- `run_agent.py`、`model_tools.py` 或 `tools/` 中有引用
- 或在 `tools/` 中注册为 Hermes 工具
- 或有数据库目录且包含 SQLite 文件

**当前状态（2026-05-25）**：❌ 未集成

---

### 5. 自动化验证

```bash
# 检查 cron 任务
hermes cronjob list | grep -i "evo\|trace\|hashpool"
```

**通过标准**：至少有一个 cron 任务调用 `evo_master` 或 `trace_hashpool`

**当前状态（2026-05-25）**：❌ 未配置

---

### 6. 真实数据积累验证

```bash
# 统计轨迹池
wc -l ~/.hermes/workspace/trace_hashpool/hashpool.jsonl

# 统计有效轨迹
grep '"valid": true' ~/.hermes/workspace/trace_hashpool/hashpool.jsonl | wc -l

# 统计技能候选
ls ~/.hermes/workspace/trace_hashpool/skill_candidates/ | wc -l

# 统计失败反例
ls ~/.hermes/workspace/trace_hashpool/failure_examples/ | wc -l
```

**通过标准**：
- `hashpool.jsonl` 至少 10 条记录
- 有效轨迹至少 5 条
- 技能候选至少 3 个
- 失败反例至少 2 个

**当前状态（2026-05-25）**：仅 1 条样例，未达标

---

## 完成度计算公式

```text
完成度 = (公式吸收 × 15% + 模块创建 × 15% + Sidecar实现 × 15% + 主链路集成 × 30% + 自动化 × 15% + 真实数据积累 × 10%) × 100%
```

---

## 2026-05-25 验证记录

| 维度 | 状态 | 完成度 | 证据 |
|---|---|---|---|
| 公式吸收 | ✅ 已完成 | 100% | 吸收报告包含三大公式的 Hermes 可执行解释 |
| 模块创建 | ✅ 已完成 | 100% | `evo_master.py` 可导入，`trace_hashpool.py` 可执行 |
| Sidecar 实现 | ✅ 已完成 | 100% | 工作区完整，包含 1 条有效轨迹 |
| 主链路集成 | ❌ 未完成 | 0% | 未被 Hermes 核心引用，未注册为工具 |
| 自动化 | ❌ 未完成 | 0% | 无 cron 任务 |
| 真实数据积累 | ⚠️ 部分完成 | 10% | 仅 1 条样例，未达 10 条基准 |

**总完成度**：15% + 15% + 15% + 0% + 0% + 1% = **46%**

---

## 未完成项（明确挂起）

| 未完成项 | 当前状态 | 下一步门槛 |
|---|---|---|
| CLAW/Hermes 核心源码级原生改造 | 明确不做/挂起 | 需单独授权、备份、回滚、安全审计、测试 |
| Rust/Go 生产级原生模块 | 未完成 | Python sidecar 稳定、有性能瓶颈、有明确接口和测试后再考虑 |
| 多 LLM 后台实时策略自更新服务 | 未完成 | 需要真实服务、日志、调度策略、失败恢复和权限门禁 |
| 自动将策略更新写入核心配置 | 未完成/不建议 | 需要人工或高安全门禁，防止误写 config/凭证 |
| 大规模真实轨迹池 | 未完成 | 当前仅 1 条有效样例；需长期真实任务积累 |
| 轨迹质量评分与评估中心深度联动 | 未完成 | 接入评估中心 score/train/predict 并读回验证 |
| 跨会话自动复用最优路径 | 部分完成 | 有技能/基因/HashPool，但未建自动策略选择器 |

---

## 关键陷阱

### 1. 不能把模块存在等同于集成完成

- ❌ 错误："`evo_master.py` 存在 → 超级进化9已落地"
- ✅ 正确："`evo_master.py` 存在但未被 Hermes 核心引用 → 仅完成模块创建，未完成集成"

### 2. 不能把 Sidecar 脚本等同于原生进化

- ❌ 错误："有 `trace_hashpool.py` → CLAW 原生进化完成"
- ✅ 正确："有 `trace_hashpool.py` → 旁路实现完成，核心改造未完成"

### 3. 不能把样例数据等同于真实数据积累

- ❌ 错误："`hashpool.jsonl` 有 1 条记录 → 真实数据积累完成"
- ✅ 正确："`hashpool.jsonl` 有 1 条记录 → 仅完成演示，未达 10 条基准"

### 4. 不能把公式吸收等同于公式落地

- ❌ 错误："吸收报告写了公式解释 → 公式已落地"
- ✅ 正确："吸收报告写了公式解释 → 方法论吸收完成，但主链路集成、自动化、真实数据积累未完成"

---

## 可复用验证模式

### 模式1：Sidecar 验证三步法

1. **脚本可执行性**：`python3 script.py --help` 显示帮助
2. **工作区完整性**：检查输出目录、数据文件、报告
3. **数据有效性**：读取数据文件，验证字段完整性和内容有效性

### 模式2：主链路集成验证三步法

1. **引用检查**：`grep -r "import module" hermes-agent/`
2. **工具注册检查**：`grep -r "module" tools/`
3. **运行时验证**：启动 Hermes，检查工具列表或实际调用

### 模式3：真实数据积累验证三步法

1. **数量检查**：`wc -l data.jsonl`
2. **质量检查**：`grep '"valid": true' data.jsonl | wc -l`
3. **多样性检查**：检查不同任务类型、不同时间段的记录

---

## 汇报格式

```markdown
## 超级进化9验证结果

| 维度 | 状态 | 完成度 | 证据 |
|---|---|---|---|
| 公式吸收 | ✅/⚠️/❌ | X% | 具体证据 |
| 模块创建 | ✅/⚠️/❌ | X% | 具体证据 |
| Sidecar 实现 | ✅/⚠️/❌ | X% | 具体证据 |
| 主链路集成 | ✅/⚠️/❌ | X% | 具体证据 |
| 自动化 | ✅/⚠️/❌ | X% | 具体证据 |
| 真实数据积累 | ✅/⚠️/❌ | X% | 具体证据 |

**总完成度**：X%

**真实性结论**：
- 已完成：[列出已完成项]
- 未完成：[列出未完成项]
- 明确挂起：[列出挂起项]
```
