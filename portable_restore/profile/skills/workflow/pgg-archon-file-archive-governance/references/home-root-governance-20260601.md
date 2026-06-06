# Home 根目录治理补充模式（2026-06-01 会话沉淀）

## 适用场景

用户要求扫描 `/Users/<user>` / `$HOME`，解释除系统文件外的文件夹来源，并将业务、实验、案件、外部 repo 等散落目录归入 PGG Archon workspace。

## 可复用流程

1. 只读盘点 Home 根目录：区分 macOS 标准目录、runtime/cache/session/tool state、业务/实验/案件散落目录。
2. 保留 runtime/cache/session/tool state，不当普通业务文件迁移：
   - `.hermes`、`.hermes-web-ui`
   - `.bash_sessions`、`.zsh_sessions`
   - `.cc-switch`、`.cua-driver`、`.openclaw` 等工具状态目录
3. 对业务/实验/案件散落目录生成迁移前 manifest：
   - 原路径、新目标路径、大小、文件数、目录数、Git remote、可 hash 的小文件 sha256。
4. 按 PGG Archon workspace 分区迁移：
   - 外部 GitHub repo → `workspace/github/`
   - 路由/模型对标材料 → `workspace/量子路由/外部对标/`
   - 开智实验/外部项目 → `workspace/开智/外部项目/`
   - 测试残留 → `workspace/开智/测试资产/`
   - 案件档案 → `workspace/苹果中枢办案库/外部案件档案_legacy_home/` 或正式案件目录
5. 修复活跃引用：只改活跃脚本、台账、规范、报告中的旧绝对路径；不要改迁移前 manifest / action log 这类证据文件。
6. 删除低风险噪音：空目录残留、`.DS_Store`、`*.pyc`、`__pycache__`。
7. 验证：
   - 旧 Home 业务目录不存在；新目标目录存在；
   - 核心 runtime 目录仍存在；
   - 活跃引用无旧绝对路径；
   - 法律 KB / 案件工具链 smoke test 仍通过；
   - SQLite integrity ok；
   - 噪音文件为 0。
8. 生成报告，明确“迁移/删除/保留/引用修复/验证结果”。

## 关键坑

- 不要把 `.hermes`、`.hermes-web-ui`、shell session、tool state 目录当作普通文件治理对象。
- `案件档案` 一类目录即使在 Home 根部，也不能直接删除；应迁入办案库并修复台账/流转记录路径。
- 引用扫描要排除本轮证据文件，否则验证文件会因为记录旧路径而自我命中。
- macOS Finder 可能在遍历后重新生成 `.DS_Store`，最终验证前需再清理一次。
