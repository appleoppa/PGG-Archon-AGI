# 后台进化守护 × Rust 进化模块融合要点

来源：2026-06 Hermes Agent 升级后后台进化连续性审计与融合。

## 触发场景

当用户要求检查、恢复、继续或优化后台进化，且存在旧 launchd label：

- `com.appleoppa.apex-god.ars`
- `com.appleoppa.apex-god.autoloop`

同时本机存在 Rust 进化模块：

- `hermes_apex_evolution`
- `ai.hermes.evol-watcher`

## 核心纪律

不要把旧目录缺失直接判定为升级覆盖；也不要以恢复旧配置为目标。应先评估当前最新版结构的完整性和优化性：

1. 官方 Hermes Agent repo 是否完整、可启动、与 upstream 一致。
2. 当前配置、gateway、Web UI、launchd 是否真实可用。
3. 缺失的旧 overlay 是否是用户优化/迁移结果。
4. 是否存在失效 launchd、pycache-only 空壳、指向不存在 module 的 wrapper。
5. Rust 进化模块是否已经承担原生 evaluate/audit/watcher 能力。

## 当前推荐架构：Rust-native fused watcher

当前最优方向不是恢复旧 Python `apex_god.workers.*`，也不是让多个定时任务并行抢调度，而是：

```text
ai.hermes.evol-watcher
  -> apex13 fused-watch
  -> Rust event watcher + Rust ARS/autoloop native cycles
  -> unified ledger/status/decisions
```

当前主入口：

```text
/Users/appleoppa/.hermes/apex-evolution-engine/target/release/apex13 fused-watch
```

launchd：

```text
~/Library/LaunchAgents/ai.hermes.evol-watcher.plist
```

核心能力：

- `src/background.rs`：Rust 原生 ARS/autoloop cycle，写 ledger/status/decisions。
- `src/evol.rs`：Rust watcher，已融合 `run_with_stop_and_background()`，启动时立刻跑一次 autoloop + ars，之后按 interval 运行。
- `src/lib.rs`：PyO3 仍保留 `py_background_cycle()` 和 `start_fused_evol_watcher()` 作为 Python 调用入口。
- `src/main.rs`：CLI 已有 `background` 和 `fused-watch` 子命令，launchd 可直接运行 Rust binary。

旧兼容 label 的当前处理：

```text
com.appleoppa.apex-god.ars       Disabled=true，已 bootout
com.appleoppa.apex-god.autoloop  Disabled=true，已 bootout
```

保留旧 plist 仅作兼容/回滚线索，不作为活跃 scheduler。活跃 scheduler 应只有 `ai.hermes.evol-watcher`。

## 状态位置

```text
~/.hermes/data/pgg-background-evolution/status.json
~/.hermes/data/pgg-background-evolution/ledger.jsonl
~/.hermes/data/pgg-background-evolution/decisions.jsonl
~/.hermes/data/pgg-background-evolution/rust/*.json
~/.hermes/logs/evol_watcher.log
~/.hermes/logs/evol_watcher_daemon.log
```

## 验证门禁

完成/维护后必须读回：

```bash
cargo check
cargo build --release
codesign --force --sign - ~/.hermes/apex-evolution-engine/target/release/apex13
launchctl list | egrep 'ai.hermes.evol-watcher|com.appleoppa.apex-god'
ps -p $(launchctl list | awk '/ai.hermes.evol-watcher/{print $1}') -o pid,ppid,command
grep '"_background_cycle"' ~/.hermes/logs/evol_watcher.log | tail
python - <<'PY'
import json, pathlib
p=pathlib.Path('~/.hermes/data/pgg-background-evolution/status.json').expanduser()
print(json.dumps(json.loads(p.read_text())['score'], ensure_ascii=False, indent=2))
PY
```

合格证据：

- launchd 只有 `ai.hermes.evol-watcher` 活跃；旧 `apex-god.ars/autoloop` 不活跃。
- 进程 command 指向 `target/release/apex13 fused-watch`，不是 Python daemon。
- 日志有 `Native background fusion: enabled`。
- `evol_watcher.log` 有 `_background_cycle` marker。
- `status.json` schema 为 `PGGBackgroundEvolutionRustCycle/v1`。
- score 无 errors，`next_stage_allowed=true`。

## 冲突点与处理

| 冲突 | 风险 | 处理 |
|---|---|---|
| Rust watcher 与 launchd interval 同时调度 | 重复触发 | 旧 interval label 禁用，统一由 fused watcher 内部 interval 调度 |
| APEX ΔE 与 continuity score 并列 | 分数口径混乱 | 分别记录，不混成单一最终分 |
| 多套状态源 | 事实分裂 | 统一写入 background-evolution ledger/status/decisions |
| 两边都自动 patch Hermes core | 互相踩文件 | 禁止双写 core；只允许低风险证据消费与账本写入 |

## 回滚路径

如 Rust-native launchd 失败：

1. `launchctl bootout gui/$(id -u)/ai.hermes.evol-watcher`
2. 从 `~/.hermes/workspace/治理/pgg-background-evolution-rust-native-migration/<timestamp>/` 取回旧 `ai.hermes.evol-watcher.plist`。
3. 重新 bootstrap 旧 plist。
4. 如需恢复旧兼容 interval，移除两个 plist 的 `Disabled` 并 bootstrap，但只有在确认不与 fused watcher 重复调度时才允许。

## 禁止项

- 不默认恢复旧 `apex_god/`、`se20/`、`agent/pgg_archon_*` overlay。
- 不用旧文件存在/缺失做唯一判断。
- 不让 Rust watcher 与 ARS/autoloop 同时自动修改 Hermes core。
- 不把 watcher running 说成进化完成。
- 不把文件存在说成后台进化已恢复；必须有 launchd、日志、账本、smoke test 证据。
