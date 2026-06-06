# Phase 报告落盘门禁（2026-05-31）

> 来源：Phase 214 审计踩坑
> 问题：报告写入 `/tmp`，subagent 审计在隔离上下文中找不到，误判为虚构报告

## 问题根因

PGG Archon 进化循环中，Phase 报告必须同时满足：
1. 主会话能写入和读回
2. subagent 审计能访问（subagent 在隔离上下文中运行，无 `/tmp` 访问）
3. 桌面同步路径正确

`/tmp` 不满足第2条。

## 正确路径规范

| 文件类型 | 必须路径 | 禁止路径 |
|----------|----------|----------|
| Phase 报告 (.md) | `~/.hermes/hermes-agent/workspace/ultimate_evolution_formula/PGG-Archon-Phase{NNN}-*.md` | `/tmp` |
| Phase JSON (.json) | `~/.hermes/hermes-agent/workspace/ultimate_evolution_formula/phase{NNN}_*.json` | `/tmp` |
| GeneDB entry (.json) | `~/.hermes/hermes-agent/workspace/ultimate_evolution_formula/GeneDB/gene_{NNN}.json` | `/tmp` |
| 桌面同步 | `~/Desktop/PGG-Archon-Phase{NNN}-*.md` + `~/Desktop/phase{NNN}_*.json` | — |

## 正确 Phase 流程（必须按顺序执行）

```
1. 执行 Phase 实测（tool calls、验证）
2. 写报告 → workspace 路径（不是 /tmp！）
3. 写 JSON → workspace 路径
4. 计算 SHA256（terminal sha256sum）
5. 写 GeneDB entry → GeneDB/ 路径（含真实 SHA）
6. subagent 审计 → 读 workspace 路径（可找到）
7. 更新 GeneDB mimo_audit 字段
8. 桌面同步（cp workspace → ~/Desktop/）
```

## 错误示范（Phase 214 实际顺序）

```
错误顺序：
1. 执行实测
2. 写报告 → /tmp ❌
3. 写 JSON → /tmp ❌
4. 写 GeneDB → GeneDB/（SHA placeholder）❌
5. subagent 审计 → 读 workspace（找不到）→ 误判虚构 ✅ 审计正确
6. 桌面同步（从 /tmp 同步，但审计已报虚构）
```

## SHA256 写入规范

GeneDB entry 的 `sha256` 字段必须用真实计算值，不能用 placeholder：
```bash
sha256sum /path/to/report.json
# 输出: abc123...  filename
# 取第一列填入 sha256 字段
```

## 审计响应规范

当 subagent 审计报告"文件不存在"时：
1. 确认报告实际在 /tmp 而非 workspace → 立即写入 workspace
2. 重新计算 SHA
3. 更新 GeneDB SHA 字段
4. 在 GeneDB entry 添加 `audit_caveat` 字段说明已修复
5. 不得删除 GeneDB entry 重建，必须增量更新
