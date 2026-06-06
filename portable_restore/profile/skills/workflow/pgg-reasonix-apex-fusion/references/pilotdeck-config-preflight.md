# PilotDeck 配置优先门禁（2026-06-03 会话复盘）

## 适用场景
当任务是把 PilotDeck 接入 PGG Archon / AGI / 进化公式 / 多 LLM 融合之前，若用户反馈 UI 无法操作、配置页报错、Service Config 不能打开，必须先完成配置与 UI 可操作性修复，再谈详细进化。

## 关键教训
- 不要只验证 YAML 文件本身；必须验证浏览器实际前端拿到的 `/api/config` 响应。
- “无法解析配置文件 YAML” 可能是前端拿不到 `raw` 字符串导致的误报，而不是 YAML 语法错误。
- 对 PilotDeck dev UI，必须同时固定：
  - `PILOT_HOME=/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck`
  - `PILOTDECK_CONFIG_PATH=/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/pilotdeck.yaml`
  - `PILOTDECK_DISABLE_LOCAL_AUTH=true`
  - `VITE_DISABLE_LOCAL_AUTH=true`
  - `SERVER_PORT=3001`
  - `VITE_PORT=5173`
- Vite client（5173）访问 `/api/config` 必须经 proxy 返回 `200 application/json`，且 JSON 中 `raw` 必须是非空 string；只验证 `3001/api/config` 不够。

## 推荐验证顺序
1. 备份配置 YAML。
2. 用后端 loader / validator 验证 YAML。
3. 启动 UI server 和 client 时显式传入 `PILOT_HOME`、`PILOTDECK_CONFIG_PATH`、local-auth 开关和端口。
4. 在浏览器上下文验证：
   - `fetch('/api/config')` status 为 200。
   - 返回 JSON 的 `path` 指向隐藏 PilotDeck 配置。
   - `typeof raw === 'string'` 且长度大于 0。
   - `validation.valid === true`。
5. 浏览器实测 Settings → Service Config，不再显示 YAML parse error，且出现 Model Pool / Agents / Router / Memory / Search / Gateway / Service 等配置入口。

## 用户工作流偏好
用户明确纠正：PilotDeck 进化/融合前，必须先把配置、UI 可操作性、启动路径和读回验证搞稳定。不能在 UI 仍无法操作时继续写进化方案或宣称第二 AGI 已可用。
