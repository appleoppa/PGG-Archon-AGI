# PGG Archon 上游吸收隔离分支模式

## 适用场景

当本地 Hermes/PGG Archon 分支相对官方 `origin/main` 同时存在：

- 本地私有提交领先；
- 官方上游提交落后/未吸收；
- 用户要求“吸收官方落后提交”“审查、吸收”；
- 私有增强不能污染官方仓库。

## 核心原则

1. **origin/main 只作为上游底座**：只 fetch/merge/rebase 审查，不默认 push 到官方。
2. **私有 PGG 改动走 private 远程独立分支**：不要强推或混入官方 main。
3. **隔离分支优先**：diverged 状态不要直接在 main 上 pull；先新建吸收分支。
4. **测试失败必须修复**：不能把 merge 成功等同于吸收完成。
5. **报告和 gene DB 入库要读回验证**：不能只生成 Markdown。

## 推荐执行顺序

1. **确认仓库态**
   - 查 `git status --short --branch`，确认 ahead/behind 数量。
   - `git fetch origin main`，不要先 pull。
   - 记录当前 HEAD、origin/main、private remote 状态。

2. **创建隔离吸收分支**
   - 命名建议：`pgg-archon-upstream-absorb-YYYYMMDD-HHMM`。
   - 从当前私有工作点创建，不直接污染 main。

3. **分类审查上游提交**
   - 对 `HEAD..origin/main` 做提交分类：fix/security、feat、test、docs、ci/chore、refactor、perf、other。
   - 统计热点目录，重点看 `agent/`、`tools/`、`hermes_cli/`、`tests/`、`gateway/`、`plugins/`。
   - 找出与 PGG 文件同路径重叠的风险面。

4. **合并并保留 PGG 改动**
   - 用 `git merge --no-ff origin/main`。
   - 若无冲突也要跑测试，因为语义冲突可能只在测试暴露。
   - 若出现修复，单独 commit，不要混在 merge commit 中。

5. **门禁验证**
   - PGG Archon 核心测试。
   - 上游相关新增测试/热点测试。
   - `py_compile` 或等价语法检查。
   - PGG 模块状态检查。
   - 必要时跑 ARS/Phase 闭环，确认 gene DB 可写、可读回。
   - `hermes doctor` 或对应 runtime 健康检查。

6. **入库与报告**
   - 生成 JSON + Markdown 报告到 `workspace/upstream_absorption/`。
   - 关键字段：上游范围、分类统计、风险文件、合并 commit、补丁 commit、测试结果、剩余风险、远端分支。
   - 写入 PGG gene DB，并执行读回验证。

7. **推送策略**
   - 只推 private 独立分支。
   - 不推 origin/main；除非用户明确要求向官方提交 PR。
   - 推送后读回远端 commit hash，确认分支存在。

## 常见坑

- **把 ahead/behind 误解成错误**：ahead/behind 是分叉状态，不等于本地坏了；正确动作是隔离吸收。
- **直接 pull main**：容易把私有 PGG 改动和官方历史混在 main，回滚困难。
- **merge 无冲突就停止**：语义冲突常通过测试暴露，例如安全路径规则误拦 macOS 临时目录。
- **安全规则粗化过度**：上游安全保护不能简单删除；应细化保护范围，保留安全意图同时解除误伤。
- **报告未入库**：Markdown 报告不是 PGG 进化完成态；必须 gene DB 入库并读回。
- **混入 workspace 或运行副产物**：提交前核对 `git status`，只 add 本轮源码/测试/必要报告。

## 完成态证据

完成汇报至少包含：

- 吸收分支名；
- 上游提交数量和分类；
- merge/fix commit；
- 测试门禁结果；
- PGG gene id/name；
- private 远端分支和读回 hash；
- 明确说明未推送到官方 origin/main。
