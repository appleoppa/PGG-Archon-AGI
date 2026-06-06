# 9router 实时状态同步 → PGG OmniRoute 吸收参考（2026-06-05）

## 触发场景

当任务涉及：

- 对比/吸收 9router、LLM gateway/router、dashboard 实时状态同步；
- PGG OmniRoute / quantum router 的 health、dashboard、provider cards、route decision 可视化；
- 用户要求“反编译/学习 9route 的实时状态同步”；
- 需要区分 cache、实时 UI、provider 真实参与证据。

## 本轮结论

9router 的实时状态同步不是单一 provider health cache，而是四层混合模型：

```text
前端 Zustand TTL store
        ↓
Next.js dynamic no-store API
        ↓
Node EventEmitter 事件总线
        ↓
SSE text/event-stream 实时推送
```

PGG OmniRoute 当前实现更接近：

```text
provider health JSON TTL snapshot
        ↓
Python bridge 调 Rust dashboard-from-live
        ↓
dashboard JSON / HTML 静态展示
```

因此当前已补齐“昂贵 provider probe 的 TTL cache”，但还没有 9router 式 UI 实时同步链。

## 9router 关键源码证据

### 1. 前端 TTL store

证据文件：

- `src/store/providerStore.js`
- `src/store/settingsStore.js`
- `src/shared/constants/config.js`

关键机制：

```text
CLIENT_STORE_TTL_MS = 60000
lastFetched
fetchProviders(force=false)
fetchSettings(force=false)
TTL 内跳过 API
force=true 强制刷新
PATCH settings 成功后 merge 本地 cache + lastFetched=Date.now()
```

### 2. dynamic no-store API

证据文件：

- `src/app/api/settings/route.js`

关键机制：

```text
dynamic = "force-dynamic"
revalidate = 0
Cache-Control: no-store
PATCH 后 applyOutboundProxyEnv(settings)
策略变化 resetComboRotation()
```

意义：配置写入后立即影响 runtime，避免框架/CDN 缓存污染状态。

### 3. EventEmitter 事件总线

证据文件：

- `src/lib/db/repos/usageRepo.js`

关键机制：

```text
global._statsEmitter = new EventEmitter()
setMaxListeners(50)
global._pendingRequests
global._recentRing
global._connectionMapCache
CONN_CACHE_TTL_MS = 30000
trackPendingRequest(...) → statsEmitter.emit("pending")
saveRequestUsage(...) → SQLite transaction → pushToRing(entry) → statsEmitter.emit("update")
```

意义：请求生命周期主动发事件，不是靠 dashboard 轮询文件冒充实时。

### 4. SSE stream 推送

证据文件：

- `src/app/api/usage/stream/route.js`

关键机制：

```text
ReadableStream
Content-Type: text/event-stream
连接后立即 send() 当前完整 stats
statsEmitter.on("update", state.send)
statsEmitter.on("pending", state.sendPending)
pending 只推轻量 activeRequests / recentRequests
25 秒 keepalive ping
cancel 时 off listener + clearInterval
```

模式：

```text
初始全量快照 + 事件驱动增量 + keepalive + 断开清理
```

## PGG OmniRoute 当前差距

PGG 已有：

```text
provider health TTL cache
force refresh
JSON dashboard
Rust route decision
Python bridge
HTML dashboard
```

PGG 缺少：

1. 浏览器/前端 store TTL。
2. no-store dashboard API。
3. 内存事件总线或等价事件源。
4. SSE `/stream` 实时推送。
5. pending/update 分层事件。
6. 初始全量 + 轻量增量模式。
7. listener cleanup / keepalive。
8. dashboard generation 与 provider health generation 的一致性门禁。

## 安全吸收设计

不要照搬 9router 的 OAuth/free-provider/cookie bypass 路径；只吸收同步架构模式。

推荐：

```text
provider health JSON TTL
        ↓
OmniRoute snapshot service
        ↓
event ledger JSONL
        ↓
SSE endpoint
        ↓
dashboard frontend store
```

事件类型建议：

```text
health_cache_hit
health_refresh_started
health_refresh_finished
health_refresh_error
dashboard_regenerated
route_decision_changed
force_refresh_requested
```

## 最小实现路线

### P0：只读 SSE snapshot

- 新增 `/api/omniroute/stream` 或等价 Hermes/Web UI endpoint。
- 连接时读取现有 dashboard JSON + provider health JSON。
- 推一次完整 snapshot。
- 每 25 秒 ping。
- 不触发 provider probe。
- 不重跑 Rust router。
- 不改 provider 决策。

### P1：事件 ledger

- 写 `~/.hermes/data/omniroute_events.jsonl`。
- 每次 health refresh / dashboard regenerated / force_refresh 写事件。
- SSE 读取 ledger 或轻量 watcher 推增量。

### P2：前端 store

- `lastFetched` + `ttlMs=60000`。
- 支持 `forceRefresh()`。
- UI 显示 `cache_status / generated_at / expires_at / age_sec / ttl_sec / generation_id`。

### P3：一致性门禁

- `health_snapshot.generation_id`。
- `dashboard.generation_id`。
- `route_decision.generation_id`。
- 若混代，显示 `stale_mixed_generation`，不得冒充实时一致。

## 不应吸收的风险

1. 不直接照搬 Node global EventEmitter 作为 PGG 核心；PGG 是 Python/Rust 主链，多进程下 Node global 会分裂。
2. 不用纯内存状态替代 JSON/manifest/ledger 可审计落盘。
3. 不把 health TTL 从 300 秒盲目降到 60 秒；provider probe 成本不同。
4. 不让每个 pending 都 shell Rust dashboard；会抖动、浪费、污染证据。
5. 不吸收 OAuth/free-provider/cookie bypass 相关路径。
6. 不把 dashboard 实时显示冒充 provider 正式参与。

## 多模型审计工具经验

本轮 Claude 参与路径：

- Hermes CLI 长 prompt / 文件路径引用可能导致模型说“没看到审计包”或超时。
- 有效做法：把审计包压缩为短 prompt，走 direct Responses API，设置 `max_completion_tokens`，并记录 `http_status / elapsed_sec / visible_chars / output path`。
- 不要把失败的 CLI 尝试计入有效 LLM 共识；只把有可见输出的 direct API 结果计入证据。

本轮有效证据：

```text
Claude direct Responses API
http_status=200
elapsed_sec=32.0
visible_chars=5761
```

## 输出边界

- provider health probe ≠ benchmark。
- dashboard/SSE 实时显示 ≠ provider 正式参与任务。
- route decision JSON ≠ full AGI。
- 9router 模式吸收应以“同步架构模式”为主，不吸收高风险账号/OAuth/free-provider 行为。
