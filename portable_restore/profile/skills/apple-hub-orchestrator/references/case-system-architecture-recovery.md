# 苹果中枢办案系统架构恢复与核验

## 适用场景

- 用户说“丢话了”“消息丢了”“查看苹果中枢办案系统架构”“系统架构已经建立起来”。
- 需要确认当前办案系统是否仍可用，而不是重建或凭记忆汇报。
- `workspace/治理/部门配置/现行部门配置.md` 缺失、滞后或与实际 profiles/办案库不一致时。

## 核验顺序

1. **先确认现行入口是否存在**
   - `~/.hermes/workspace/治理/部门配置/现行部门配置.md`
   - 若缺失，不要直接断言系统未建立；进入架构恢复核验。

2. **核验核心规则与流程文件**
   - `~/.hermes/workspace/AGENTS.md`
   - `~/.hermes/workspace/workflows/办案流程详解.md`
   - `~/.hermes/workspace/workflows/法律办案_Hermes-Kanban链路.md`
   - `~/.hermes/workspace/templates/苹果中枢办案系统_指令模板.md`
   - `~/.hermes/workspace/standards/core/12_案件类型流程配置表.md`

3. **核验办案库与台账**
   - 办案库：`~/.hermes/workspace/苹果中枢办案库/`
   - 最新台账：`~/.hermes/workspace/苹果中枢办案库/台账/案件台账_最新.md`
   - 对比：实际案件目录 vs 台账有效案件。目录存在但台账未写入时，标记“台账可能滞后”，不要说台账完整。

4. **核验部门 profile**
   - `~/.hermes/profiles/pgg-*`
   - 当前常见部门 profile：`pgg-anguan`, `pgg-minshi`, `pgg-feisu`, `pgg-guwen`, `pgg-law`, `pgg-tuiyan`, `pgg-zhixing`, `pgg-xingshi`, `pgg-xunshi`, `pgg-shenji`, `pgg-zhengju`, `pgg-zhinao`。
   - 注意：profile 存在不等于流程文件已正式列入该部门。

5. **核对技能层**
   - 中枢：`apple-hub-orchestrator`
   - 案管：`agent-cms`
   - 相关部门技能：`dept-*` 或 `apple-*-1.0.0`

## 典型判断口径

- 核心流程、profiles、办案库、台账均存在，但 `治理/部门配置/现行部门配置.md` 缺失：
  - 状态：架构主体已建立；统一入口文件缺失；可恢复。
  - 下一步：从 workflow + template + profiles + skills + 台账重建 `治理/部门配置/现行部门配置.md`。

- 办案库目录比台账更新：
  - 状态：台账滞后。
  - 不要将旧台账日期作为当前案件状态最终事实。

- 文书机要部在模板/profile 中存在，但主流程部门清单未列入：
  - 状态：部门定位待统一。
  - 不要擅自下架或正式化，应作为“待定版项”汇报。

## 汇报模板

```text
当前状态：架构主体已建立 / 入口缺失 / 台账滞后 / 证据不足
已核验资产：规则、流程、Kanban、模板、办案库、台账、profiles
主要缺口：列出缺失入口、部门定义冲突、台账滞后
建议下一步：重建现行部门配置 → 同步台账 → 最小办案链路演练
```

## 禁止事项

- 禁止因 `治理/部门配置/现行部门配置.md` 缺失就判断系统不存在。
- 禁止只读历史存档目录作为当前架构事实。
- 禁止把 profile 存在等同于部门已进入正式流程。
- 禁止在未比对目录与台账前说“台账已同步”。
