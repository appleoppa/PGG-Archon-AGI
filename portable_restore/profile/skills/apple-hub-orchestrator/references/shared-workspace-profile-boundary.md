# 苹果中枢办案系统：共享工作空间与部门私有资产边界

## 适用场景

当用户要求配置、重建、审计或解释苹果中枢办案系统的 profile / workspace / 部门资产关系时使用。

## 现行口径

- `default` profile 是苹果中枢/main，也是公共工作空间的承载入口。
- 各 `pgg-*` profile 是部门身份，不代表独立文件沙箱。
- 各部门共享 `default` 工作空间读写公共资产：办案库、流程、模板、标准、任务队列、审计队列、智库、公共配置、公共技能等。
- 各部门 profile 自行保存本部门私有身份资产：职能、专用技能、画像、偏好、身份提示、部门工作习惯等。
- 部门私有资产不能覆盖公共事实。公共事实以 `workspace/治理/部门配置/现行部门配置.md`、办案库、台账、流程文件为准。

## 执行规则

1. 正式办案文件统一写入共享工作空间，尤其是：
   - `/Users/appleoppa/.hermes/workspace/苹果中枢办案库/`
   - `/Users/appleoppa/.hermes/workspace/任务队列/`
   - `/Users/appleoppa/.hermes/workspace/审计队列/`
2. 部门个性化内容写入对应 profile：
   - `/Users/appleoppa/.hermes/profiles/pgg-*/SOUL.md`
   - 部门专用 skill、偏好、画像等 profile-local 资产。
3. 不要把 profile 隔离说成文件沙箱；profile 是身份/配置隔离，公共案件资产仍共享。
4. 修改全局流程或部门架构时，先更新 `治理/部门配置/现行部门配置.md`，再同步 workflow/template/standard/skill。
5. 修改单个部门职能或偏好时，优先更新该部门 profile 的身份文件或专用技能。

## 常见坑

- 误以为每个部门有独立办案库，导致文件散落。
- 把部门 profile 的私有提示当作全局流程事实。
- 在旧 `案件共享/` 或历史迁移路径写入新案件材料。
- 更新了 workflow 但忘记同步 `apple-hub-orchestrator` 和 `agent-cms`。

## 验证清单

- `workspace/治理/部门配置/现行部门配置.md` 是否写明共享工作空间规则。
- `pgg-*` profile 是否只保存部门身份/偏好/专用能力。
- 新案件是否只进入 `workspace/苹果中枢办案库/`。
- active workflow/template/standard/skill 中是否仍有旧“文书机要部独立派发”“案件共享路径”等口径。
