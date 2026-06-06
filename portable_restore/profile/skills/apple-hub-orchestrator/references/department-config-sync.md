# 部门配置同步与旧配置清理工作流

适用场景：用户要求汇报、调整、同步、删除或核验苹果中枢部门配置、办案工作流、部门技能映射时。

## 核心教训

不能把“当前残留目录”或“旧技能映射”直接当成现行部门配置。部门调整后，旧目录、旧案卷、旧开智记录、旧知识沉淀可能继续包含旧部门名称；这些只能说明历史流程背景，不能证明当前仍有效。

## 正确顺序

1. 先查唯一现行入口或最新版本记录。
   - 优先读取 `workspace/治理/部门配置/现行部门配置.md`。
   - 同步核对 `workspace/AGENTS.md` 的版本变更记录。
   - 必要时核对运行配置，如 `openclaw.json`。
2. 再查当前运行配置。
   - 部门列表、允许调用列表、工作区路径、技能映射是否一致。
3. 再查残留目录和历史文件。
   - 残留目录只能作为“待清理/待归档”证据。
   - 历史案卷和历史知识沉淀应加“历史流程产物”说明，而不是改写原文。
4. 同步修复。
   - 下架部门：从运行配置、部门目录、技能映射、工作流节点中移除或归档。
   - 新增部门：补齐部门目录、行为准则、身份、记忆、技能映射、主流程节点。
   - 弱化/并入部门：把职责写入现行入口，避免继续作为独立部门派发。
5. 连通性验证。
   - 新增部门必须做最小职责输出测试，验证不是“配置存在”。
   - 主链路必须做最小演练，覆盖编号、预检、业务分析、证据、推演、复核、巡视、归档、审计。
6. 输出报告。
   - 报告必须说明引用来源。
   - 报告必须区分“现行配置”“历史流程产物”“残留待清理”。

## 质量门禁

- 如果报告引用来源只是目录扫描，必须降级为“目录现状”，不能称为“当前部门配置”。
- 如果发现旧配置仍参与运行，应按75%规则自行归档、修复、重跑验证。
- 如果历史记录含旧部门名称，不应直接删除或改写历史；应在目录层添加历史说明。

## Current V7.0 Case-System Rebuild Rule

When the user approves a rebuilt Apple case-system architecture, do not leave it as a draft. Apply it globally in this order: backup → profile remap → formal `治理/部门配置/现行部门配置.md` → workflows/templates/standards → skills → clear authorized old case records → verify active files. See `references/case-system-rebuild-reset.md`.

Key V7.0 example:

- `default` profile is 苹果中枢/main.
- `pgg-*` profiles are departments.
- 文书机要部 is not an independent department; document drafting/format/polish belongs to the relevant business department's internal self-check.
- The former document profile can be remapped to `pgg-zhixing` 强制执行部 when the user instructs so.
- Strong execution department handles execution filing, asset clues,查控,保全/查封/冻结/拍卖路径, execution objections/reconsideration, terminal-case review, and execution settlement.

## 当前部门配置案例规则

V6.1口径下（历史案例，仅用于识别旧口径，不作为现行事实）：

- 文书机要部已下架，职能转为业务部门内部格式自检。
- 旧运维部门口径已失效，系统运维由苹果中枢按 Hermes 运行状态处理。
- 证据管理部是正式流程部门，需进入证据链核验、证据目录、举证质证策略节点。
- 强制执行部现行 profile 为 `pgg-zhixing`。

此处案例用于提醒“先找最新调整记录”，未来如现行入口更新，应以新的入口文件为准。
