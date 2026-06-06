#!/bin/bash
# Bridge ENOENT 诊断脚本
# 用途：检测 bridge worker socket 目录状态、进程健康、macOS /var/folders/ 清理导致的 ENOENT (Variant A)
#       以及缺失 /tmp/hermes-agent-bridge-workers/ 目录导致的 ENOENT (Variant B)
set -e

BRIDGE_SOCK="/tmp/hermes-agent-bridge.sock"
TMP_WORKER_DIR="/tmp/hermes-agent-bridge-workers"
LOG="${HOME}/.hermes-web-ui/logs/bridge.log"

echo "=== Bridge ENOENT 诊断 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo "--- 进程状态 ---"
ps aux | grep -E "hermes.*bridge|hermes-web-ui.*node" | grep -v grep | awk '{print "pid="$2, "status="$8, "cmd="$11,$12,$13,$14}' || echo "无进程"
echo ""

echo "--- 主 Socket 状态 ---"
if [ -S "$BRIDGE_SOCK" ]; then
    echo "✅ $BRIDGE_SOCK 存在 ($(stat -f '%Sm' -t '%Y-%m-%d %H:%M:%S' "$BRIDGE_SOCK"))"
    lsof -nP 2>/dev/null | grep "$BRIDGE_SOCK" | grep -v grep | head -3
else
    echo "❌ $BRIDGE_SOCK 不存在或非 socket"
fi
echo ""

echo "--- Variant B: /tmp/ worker socket 目录状态 ---"
if [ -d "$TMP_WORKER_DIR" ]; then
    echo "✅ $TMP_WORKER_DIR 存在"
    echo "修改时间: $(stat -f '%Sm' -t '%Y-%m-%d %H:%M:%S' "$TMP_WORKER_DIR")"
    WORKER_COUNT=$(ls -1 "$TMP_WORKER_DIR" 2>/dev/null | wc -l | tr -d ' ')
    echo "worker socket 文件数: $WORKER_COUNT"
    if [ "$WORKER_COUNT" -gt 0 ]; then
        ls -la "$TMP_WORKER_DIR" | head -10
    fi
else
    echo "❌ $TMP_WORKER_DIR 不存在 → Variant B ENOENT 根因"
fi
echo ""

echo "--- Bridge Log 最新 ENOENT (提取实际路径) ---"
if [ -f "$LOG" ]; then
    ENOENT_COUNT=$(grep -c "ENOENT.*hermes-agent-bridge-workers" "$LOG" 2>/dev/null || echo "0")
    echo "历史 ENOENT 次数: $ENOENT_COUNT"
    # Extract the actual path from ENOENT lines (Variant A: /var/folders/..., Variant B: /tmp/...)
    grep "ENOENT.*hermes-agent-bridge-workers" "$LOG" 2>/dev/null | tail -3 | while read line; do
        # Extract socket path — find the path between "ENOENT" or "connect" and the next comma/space
        PATH_IN_LOG=$(echo "$line" | grep -oE '/[a-zA-Z0-9_/.-]*hermes-agent-bridge-workers/[a-zA-Z0-9_.-]*\.sock' | head -1)
        if [ -n "$PATH_IN_LOG" ]; then
            WORKER_DIR_IN_LOG=$(dirname "$PATH_IN_LOG")
            echo "  日志中的 worker 目录: $WORKER_DIR_IN_LOG"
            if [ -d "$WORKER_DIR_IN_LOG" ]; then
                echo "    ✅ 该目录存在"
            else
                echo "    ❌ 该目录不存在 → 可能已被 macOS 清理 (Variant A)"
            fi
        fi
        TIME=$(echo "$line" | grep -o '"time":[0-9]*' | head -1)
        echo "  $TIME"
    done
else
    echo "日志文件不存在"
fi
echo ""

echo "--- Web UI 健康检查 ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8648/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Web UI HTTP $HTTP_CODE"
else
    echo "❌ Web UI HTTP $HTTP_CODE"
fi

echo ""
echo "--- 修复建议 ---"
if [ ! -d "$TMP_WORKER_DIR" ]; then
    echo "Variant B: mkdir -p $TMP_WORKER_DIR && hermes-web-ui restart"
fi
if [ -f "$LOG" ]; then
    VAR_FOLDER_ENOENT=$(grep "ENOENT.*/var/folders" "$LOG" 2>/dev/null | tail -1)
    if [ -n "$VAR_FOLDER_ENOENT" ]; then
        echo "Variant A: 检测到 /var/folders/ ENOENT — bootstrap 会在重启后自动恢复该目录"
    fi
fi

echo ""
echo "=== 诊断完成 ==="
