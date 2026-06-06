# GitHub 镜像保存与 Push Protection 处理

## 触发场景

- 用户要求“拉取/复刻/保存到我的 GitHub”。
- 源仓库在第三方账号下，本机 GitHub 登录账号无写权限。
- 直接推送被 GitHub Push Protection 拦截，提示历史提交或文件中包含 token/secret。

## 推荐流程

1. **先只读核验源端**
   - `git ls-remote --heads <source-url> <branch>` 确认远程分支存在和 commit。
   - 本地已有同名项目时，不覆盖现有工作区；优先 `git fetch` + `git worktree add` 到独立目录。

2. **保留原始拉取目录**
   - 原始目录用于证明“已经拉取”。
   - 验证字段：分支名、本地 HEAD、源端远程 HEAD、tracked file count、`git status --short --branch`。

3. **推送权限失败时切换到用户账号仓库**
   - 用 `gh auth status` / `gh api user --jq .login` 识别当前 GitHub 账号。
   - 若 `owner/repo` 不存在且用户明确要求保存到其 GitHub，可创建同名仓库。
   - 不要把第三方源仓库的 403 误报成推送成功。

4. **Push Protection 拦截时不要绕过**
   - 不使用 unblock URL，也不强行允许 secret 进入新仓库。
   - 扫描 token-like 字符串时只输出文件名、pattern 类型和数量，避免打印 secret 原文。
   - 对外保存优先做 sanitized mirror（脱敏镜像）：复制当前树、替换 token-like literal、重新初始化为单提交，再推送。
   - 保留原始拉取目录 + sanitized 发布目录，分别说明用途。

5. **脱敏镜像验证**
   - 推送前复扫：`REMAINING_SECRET_LIKE_FILES 0`。
   - 推送后核验：`git ls-remote` 的远程分支 commit 与本地 sanitized commit 一致。
   - 汇报中明确：历史未完整保留；保存的是脱敏后的当前代码树。

## 典型 token-like 正则

```text
github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}
```

## 汇报字段

- 原始拉取路径、分支、源端 commit、本地 commit 是否一致。
- 用户 GitHub 仓库 URL、分支、默认分支、可见性。
- 是否触发 403 或 Push Protection。
- 脱敏文件数量，不展示 secret 原文。
- 最终远程 commit 与本地 commit 是否一致。
