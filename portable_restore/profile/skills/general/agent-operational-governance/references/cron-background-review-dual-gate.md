# Cron Job 后台执行 dual-layer gate 冲突

## 背景

cron job 在 `~/.hermes/cron/jobs.json` 中配置 `enabled_toolsets`，但后台执行时有一个额外的后台审查层（`Background review`），两层规则不一致导致 job 永远无法完成写操作。

## 冲突结构

### Layer 1 — cron job 配置层
```json
{
  "enabled_toolsets": ["terminal", "file"]
}
```
`file` toolset 包含 `read_file`、`patch`、`write_file`。

### Layer 2 — 后台执行审查层
后台 cron 执行时，安全审查只允许 `memory` 和 `skill` 类工具：
```
"Background review denied non-whitelisted tool: read_file. Only memory/skill tools are allowed."
"Background review denied non-whitelisted tool: patch. Only memory/skill tools are allowed."
```

### Layer 3 — approval_pending 阻塞
部分 terminal 命令需要交互式审批，cron 环境无法提供：
```
"status": "pending_approval", "approval_pending": true
```

## 实际日志证据

```
# 2026-05-24 04:25:27 ~ 04:25:38 (cron_91064196c7eb_20260524_042223)
WARNING [cron_91064196c7eb_20260524_042223] agent.tool_executor: Tool read_file returned error (0.00s): {"error": "Background review denied non-whitelisted tool: read_file. Only memory/skill tools are allowed."}
WARNING [cron_91064196c7eb_20260524_042223] agent.tool_executor: Tool patch returned error (0.00s): {"error": "Background review denied non-whelitested tool: patch. Only memory/skill tools are allowed."}

# 2026-05-24 08:51:47 ~ 08:52:55 (cron_3c318a039c51_20260524_085043)
WARNING [cron_3c318a039c51_20260524_085043] agent.tool_executor: Tool terminal returned error (0.14s): {"status": "pending_approval", "approval_pending": true, "command": "cat ... | python3 -c \"import json..."}
```

## 后果

cron job 配置了 `file` toolset，看起来有写文件权限，但后台执行时所有 file 类工具（read_file/patch/write_file）都被拦截，导致：
- 无法读取 ledger 文件判断完成状态
- 无法写入 round summary 和 evidence
- 无法 patch ledger 更新完成数
- job 状态永远是 error 或 blocked

## 解决方向（未执行，需用户授权）

1. **toolsets 扩展**：在 cron job 配置中增加 `memory` toolset，或在 job prompt 层面使用 `skill_manage` 更新 ledger（纯 skill 操作，被后台允许）
2. **审查白名单**：为 cron job prompt 单独设置白名单，不触发 `destructive_root_rm` 和 `Background review` 规则
3. **写操作改走 skill_manage**：所有 ledger 更新改用 `skill_manage`（memory 类工具），绕过 file toolset 限制
4. **避免 terminal pipe to python**：cron job prompt 中的 `cat | python3 -c` 触发 approval_pending，改用纯 shell/python 脚本文件

## 关联问题

- `skills_guard` 的 `destructive_root_rm` 规则会拦截 cron prompt 中含 `rm -rf` 字面量的任务
- `clawdefender-1` skill 本身是安全扫描器，但被安全扫描器误标记为注入风险（false positive）
- `AGENTS.md` 入口引用的 `治理/部门配置/现行部门配置.md` 文件不存在

## 验证命令

```bash
# 检查 cron job 当前状态
python3 -c "
import json
with open('/Users/appleoppa/.hermes/cron/jobs.json') as f:
    d = json.load(f)
for j in d.get('jobs', []):
    print(f\"ID:{j['id']} name:{j.get('name','?')} enabled:{j.get('enabled',True)} state:{j.get('state','?')} last_error:{j.get('last_error','?')[:80]}\")
"

# 检查 skills_guard 后台审查拦截记录
grep "Background review denied" /Users/appleoppa/.hermes/logs/errors.log | tail -10

# 检查 destructive_root_rm 拦截记录
grep "destructive_root_rm" /Users/appleoppa/.hermes/logs/errors.log | tail -10
```
