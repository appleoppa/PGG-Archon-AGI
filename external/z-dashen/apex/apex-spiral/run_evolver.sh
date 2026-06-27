#!/bin/bash
#璇玑 Evolver 进程守护脚本 v3
#新增：PID文件锁，防止并发启动多个实例
#解决：多个subagent sessions同时调用导致7个并发进程

LOCKFILE="/root/.nvm/evolver.lock"
PIDFILE="/root/.nvm/evolver.pid"
LOGFILE="/root/.nvm/evolver_watchdog.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOGFILE"; }

EVOLVER_DIR="/root/.nvm"
EVOLVER_PATT="node index.js"

# ── 互斥锁：只允许一个实例 ──
acquire_lock() {
  if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
    if kill -0 "$OLD_PID" 2>/dev/null; then
      log "[拒绝] 已有实例 PID=$OLD_PID 运行中，拒绝重复启动"
      echo "BLOCKED: evolver already running as PID=$OLD_PID"
      exit 0
    else
      log "[警告] 锁文件存在但进程已死，清理中"
      rm -f "$LOCKFILE"
    fi
  fi
  
  # 创建锁文件
  echo $$ > "$LOCKFILE"
  log "[锁定] PID=$$ 已获取锁"
}

# ── 清理函数 ──
cleanup() {
  if [ -f "$PIDFILE" ]; then
    OLD=$(cat "$PIDFILE")
    if kill -0 "$OLD" 2>/dev/null; then
      log "[清理] 发现旧进程 PID=$OLD，杀掉"
      kill "$OLD" 2>/dev/null; sleep 2; kill -9 "$OLD" 2>/dev/null
    fi
    rm -f "$PIDFILE"
  fi
  rm -f "$LOCKFILE"
}

# ── 信号处理 ──
trap cleanup EXIT INT TERM

# ── 主入口 ──
acquire_lock
cleanup

# 启动 node 于背景
cd "$EVOLVER_DIR"
node index.js run "$@" &
NODE_PID=$!

echo "$NODE_PID" > "$PIDFILE"
log "[启动] PID=$NODE_PID | args=$@"

# 等待 node 退出
wait $NODE_PID
EXIT_CODE=$?

log "[退出] PID=$NODE_PID exit=$EXIT_CODE"
rm -f "$PIDFILE"
rm -f "$LOCKFILE"

# ── APEX后处理：修复Evolver写入缺失字段 ──
if [ -f "$EVOLVER_DIR/standard/post-evolver-fix.sh" ]; then
  log "[APEX] 执行后处理修复..."
  bash "$EVOLVER_DIR/standard/post-evolver-fix.sh" >> "$LOGFILE" 2>&1
fi

exit $EXIT_CODE
