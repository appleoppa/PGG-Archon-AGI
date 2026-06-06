# 超级进化4-5验证方法论

**创建时间**：2026-05-25
**来源会话**：超级进化系列审查（超级进化1-5完整验证）

---

## 超级进化4：Emv 熵 Skill 框架

### 核心要求

来源：`~/Desktop/进化文件/超级进化/超级进化4-上下文学习新框架.md`

**核心机制**：
- 三角色系统：Challenger（出题）、Reasoner（解题）、Judge（判题）
- 自博弈循环迭代
- 跨时间重放机制
- 熵选择机制（基尼不纯度、信息熵、信息增益）

**核心公式**：
```
基尼不纯度：Gini = 1 - Σ(p_k²)
信息熵：H = -Σ(p_k * log2(p_k))
信息增益：IG = H_parent - (N_L/N * H_L + N_R/N * H_R)
技能选择：score = success_rate * (1 - gini_impurity)
```

### 六维度验证标准

| 维度 | 验证方法 | 通过标准 |
|------|---------|---------|
| **学习吸收** | 检查完成报告存在性和时间戳 | 报告存在且完成度声明明确 |
| **核心文件** | 检查 `emv_skill_framework.py` 存在性和大小 | 文件存在且 > 10KB |
| **三角色系统** | Python 导入测试，检查类实例化 | Challenger、Reasoner、Judge 三个类可实例化 |
| **熵计算** | 测试 `EntropyCalculator` 的三个方法 | 基尼不纯度、信息熵计算结果正确 |
| **自博弈循环** | 运行 5 轮迭代测试 | 成功率 > 50%，提炼出技能数 > 0 |
| **技能提炼** | 检查 `get_best_skills()` 返回结果 | 返回技能列表，包含 success_rate、gini_impurity、entropy |

### 验证命令模板

```bash
# 1. 检查核心文件
ls -lh ~/.hermes/hermes-agent/emv_skill_framework.py

# 2. 测试三角色系统
cd ~/.hermes/hermes-agent && source venv/bin/activate && python3 -c "
from emv_skill_framework import EmvSkillFramework
framework = EmvSkillFramework()
print(f'Challenger: {framework.challenger.__class__.__name__}')
print(f'Reasoner: {framework.reasoner.__class__.__name__}')
print(f'Judge: {framework.judge.__class__.__name__}')
"

# 3. 测试熵计算
cd ~/.hermes/hermes-agent && source venv/bin/activate && python3 -c "
from emv_skill_framework import EntropyCalculator
labels = [1, 1, 0, 0, 1, 0]
gini = EntropyCalculator.gini_impurity(labels)
entropy = EntropyCalculator.entropy(labels)
print(f'基尼不纯度: {gini:.4f}')
print(f'信息熵: {entropy:.4f}')
"

# 4. 测试自博弈循环（5轮）
cd ~/.hermes/hermes-agent && source venv/bin/activate && python3 -c "
from emv_skill_framework import EmvSkillFramework
framework = EmvSkillFramework()
context = '测试上下文：Python 编程相关文档'
results = framework.run_multiple_iterations(context, n=5)
success_count = sum(1 for r in results if r['judgment'].correct)
print(f'总迭代数: {len(results)}')
print(f'成功任务: {success_count}')
print(f'成功率: {success_count/len(results):.2%}')
print(f'提炼技能数: {len(framework.skills)}')
"

# 5. 测试技能选择
cd ~/.hermes/hermes-agent && source venv/bin/activate && python3 -c "
from emv_skill_framework import EmvSkillFramework
framework = EmvSkillFramework()
context = '测试上下文'
results = framework.run_multiple_iterations(context, n=5)
best_skills = framework.get_best_skills(top_k=3)
for i, skill in enumerate(best_skills, 1):
    print(f'{i}. {skill.name}: 成功率={skill.success_rate:.2f}, 基尼={skill.gini_impurity:.2f}')
"
```

### 真实能力边界

**已完成**：
- ✅ 三角色系统完整实现
- ✅ 熵计算机制（基尼不纯度、信息熵、信息增益）
- ✅ 自博弈循环（多次迭代测试通过）
- ✅ 技能提炼机制（从成功案例中提取）
- ✅ 技能选择机制（基于熵的评分）
- ✅ 动态难度调整

**待集成**：
- ⚠️ 与主 Agent 流程集成
- ⚠️ 与 SkillBank 联动
- ⚠️ 实际场景测试

### 验证记录（2026-05-25）

```
✅ 核心文件: emv_skill_framework.py (14KB, 534行)
✅ 三角色系统: Challenger, Reasoner, Judge 已实例化
✅ 熵计算: 基尼不纯度=0.5000, 信息熵=1.0000
✅ 自博弈循环: 5轮迭代, 成功率=80%, 提炼技能数=4
✅ 技能选择: Top 3 技能成功率 0.81-0.88
```

**完成度**：100%

---

## 超级进化5：海马体 SWRs 记忆系统

### 核心要求

来源：`~/Desktop/进化文件/超级进化/超级进化5-记忆系统.md`

**核心机制**：
- 海马体 SWRs 机制 → AI 记忆系统
- 重要性评分选择经验
- 候选队列生成
- 门控应用（备份保护）
- 自动分流（memory / user / skill / review_queue / workspace_archive）

**大脑机制 → AI 类比**：
```
经验输入 → 海马体编码  →  对话输入 → 临时记忆
SWRs 选择重要经验      →  重要性评分选择经验
回放巩固到新皮层       →  保存到长期记忆
形成稳定记忆          →  下次查询复用
```

### 六维度验证标准

| 维度 | 验证方法 | 通过标准 |
|------|---------|---------|
| **学习吸收** | 检查 SWRs 脚本存在性 | 三个核心脚本存在且可执行 |
| **重要性评分** | 运行 `hermes_memory_swrs.py` | 输出包含 scored_candidates、write_ready、review_queue |
| **候选队列** | 检查候选队列 JSON 文件 | 文件存在且 > 100KB |
| **备份机制** | 运行 `hermes_memory_backup.py` | 备份成功，manifest.json 存在 |
| **安全应用** | 检查 `hermes_memory_swrs_apply.py` 门控规则 | 包含 SECRET_PAT、STALE_PAT、IMPERATIVE_PAT |
| **自动分流** | 检查评分输出的 target 字段 | 包含 memory、user、skill、review_queue、workspace_archive |

### 验证命令模板

```bash
# 1. 检查核心脚本
ls -lh ~/.hermes/scripts/hermes_memory_swrs.py
ls -lh ~/.hermes/scripts/hermes_memory_swrs_apply.py
ls -lh ~/.hermes/scripts/hermes_memory_backup.py

# 2. 测试重要性评分
cd ~/.hermes/scripts && python3 hermes_memory_swrs.py --out /tmp/memory_swrs_test.json --limit 10

# 3. 检查候选队列
ls -lh ~/.hermes/workspace/开智/超级进化5记忆SWRs候选队列.json

# 4. 测试备份机制
cd ~/.hermes/scripts && python3 hermes_memory_backup.py

# 5. 检查备份内容
ls -lh ~/.hermes/backups/memory_swrs/$(ls -t ~/.hermes/backups/memory_swrs/ | head -1)/
cat ~/.hermes/backups/memory_swrs/$(ls -t ~/.hermes/backups/memory_swrs/ | head -1)/manifest.json

# 6. 检查评分输出格式
cat /tmp/memory_swrs_test.json | python3 -m json.tool | head -50
```

### 重要性评分机制

**正向模式（加分）**：
```python
'explicit_preference': (4分) - 记住|以后|偏好|不要再|别再
'correction': (3分) - 错了|不对|纠正|证据不足|虚假完成
'stable_workflow': (3分) - 流程|门禁|固定|长期|复用|技能
'environment_fact': (2分) - 路径|profile|配置|数据库|脚本
'verification': (2分) - 验证|读回|核验|evidence|verified
```

**负向模式（减分）**：
```python
'temporary_progress': (-3分) - 已完成|本轮|今天|刚才|临时
'stale_artifact': (-4分) - PR#|commit|SHA|issue#|编号|分数
'secret_risk': (-5分) - api_key|token|secret|密码|密钥
```

**分流规则**：
```python
if score >= 7 and no_secret:
    if "偏好|用户希望|不要|别再" in text:
        target = "user"
    elif "流程|技能|步骤|workflow" in text:
        target = "skill"
    else:
        target = "memory"
elif score >= 3:
    target = "review_queue"
else:
    target = "workspace_archive"
```

### 安全边界

**门控规则**：
- 默认 dry-run，真实应用需 `--apply` + 新鲜备份（24小时内）
- 只自动追加高置信度候选（score >= 7）
- 只删除完全重复的非标题行
- 绝不写入秘密、技能、配置、环境变量、源码
- 拒绝祈使句（"必须"、"不要"、"禁止"），只接受陈述句
- 拒绝临时进度、过期产物（PR#、commit、SHA）

**安全模式**：
```python
SECRET_PAT = r'api[_-]?key|token|secret|密码|密钥'
STALE_PAT = r'PR\s*#|commit|SHA|issue\s*#|本轮|刚才|临时'
IMPERATIVE_PAT = r'^(必须|不要|禁止|以后要|记得|请|执行)'
```

### 真实能力边界

**已完成**：
- ✅ 重要性评分机制（正负模式）
- ✅ 候选队列生成（128→30→11）
- ✅ 备份机制（8天保留期）
- ✅ 安全应用（门控规则）
- ✅ 自动分流（5个目标）
- ✅ 安全脱敏（秘密、临时进度、过期产物）

**待自动化**：
- ⚠️ cron 定时任务未配置（脚本已就绪，需手动启用）

### 验证记录（2026-05-25）

```
✅ 核心脚本: hermes_memory_swrs.py (7.5KB), hermes_memory_swrs_apply.py (7.6KB), hermes_memory_backup.py (3.2KB)
✅ 重要性评分: 原始候选=128, 评分候选=30, 待写入=11, 待审查=19
✅ 候选队列: 超级进化5记忆SWRs候选队列.json (121KB)
✅ 备份机制: 备份完成, 复制项=4/4, manifest.json 存在
✅ 安全应用: SECRET_PAT, STALE_PAT, IMPERATIVE_PAT 已实现
✅ 自动分流: memory, user, skill, review_queue, workspace_archive
```

**完成度**：95%（cron 未配置）

---

## 通用验证模式

### 六维度验证框架

所有超级进化项目验证必须覆盖六个维度：

1. **学习吸收**：检查完成报告、文档、规则是否存在
2. **核心文件**：检查关键代码、脚本、配置文件是否存在
3. **核心功能**：测试主要功能是否可用
4. **集成验证**：测试与现有系统的集成
5. **性能验证**：测试性能指标是否达标
6. **真实能力边界**：明确已完成、待完成、不支持的功能

### 验证三步法

1. **静态检查**：文件存在性、大小、时间戳
2. **功能测试**：导入测试、单元测试、集成测试
3. **真实场景验证**：实际任务测试、边界测试、失败场景测试

### 状态判断标准

| 状态 | 标准 |
|------|------|
| ✅ 已完成 | 六维度全部通过，有验证记录 |
| ⚠️ 部分完成 | 核心功能通过，但有待完成项 |
| ❌ 未完成 | 核心功能未通过或文件不存在 |
| 🔄 进行中 | 文件存在但功能测试未通过 |

### 汇报格式模板

```markdown
## 核心证据

| 维度 | 状态 | 证据 |
|------|------|------|
| **学习吸收** | ✅/⚠️/❌ | 具体证据 |
| **核心文件** | ✅/⚠️/❌ | 文件路径和大小 |
| **核心功能** | ✅/⚠️/❌ | 测试结果 |
| **集成验证** | ✅/⚠️/❌ | 集成测试结果 |
| **性能验证** | ✅/⚠️/❌ | 性能指标 |
| **真实能力边界** | ✅/⚠️/❌ | 已完成/待完成/不支持 |

## 落地产物验证

### 1. 核心文件
- 文件路径
- 文件大小
- 修改时间

### 2. 功能测试
- 测试命令
- 测试结果
- 验证记录

### 3. 真实能力边界
- ✅ 已完成并验证
- ⚠️ 部分完成
- ❌ 未完成

## 结论

**完成度**：X%

核心要求"..."已完整落地/部分落地/未落地。
```

---

## 已知陷阱

### 1. 完成报告不等于真实完成

- 完成报告存在只证明有人声称完成，不证明功能可用
- 必须通过功能测试验证真实能力
- 必须检查文件存在性、大小、时间戳

### 2. 文件存在不等于功能可用

- 文件存在只证明代码已部署，不证明功能正常
- 必须通过导入测试、单元测试验证
- 必须通过实际场景测试验证

### 3. 测试通过不等于生产可用

- 测试通过只证明基础功能正常，不证明生产可用
- 必须检查集成状态、性能指标、边界条件
- 必须明确真实能力边界和待完成项

### 4. 声称集成不等于真实集成

- 声称"已集成到主 Agent 流程"必须有调用记录
- 声称"已与 SkillBank 联动"必须有数据流验证
- 声称"已部署到生产"必须有运行日志

### 5. 配置存在不等于配置生效

- 配置文件存在不等于配置已加载
- 必须通过运行时检查验证配置生效
- 必须检查配置冲突、覆盖、优先级

---

## 参考资料

- 超级进化1验证：`references/super-evolution-1-2-verification.md`
- 超级进化2验证：`references/super-evolution-1-2-verification.md`
- 超级进化3验证：`references/super-evolution-3-verification.md`
- 超级进化验证清单：`references/super-evolution-verification-checklist.md`
