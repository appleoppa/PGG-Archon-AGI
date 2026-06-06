#!/bin/bash
# Bridge ENOENT 诊断脚本
# 用途：检测 bridge worker socket 目录状态、进程健康、macOS /var/folders/ 清理导致的 ENOENT
set -e

BRIDGE_SOCK="/tmp/hermes-agent-bridge.sock"
WORKER_DIR=$(python3 -c "import tempfile; print(tempfile.gettempdir())" 2>/dev/null || echo "/tmp")/hermes-agent-bridge-workers
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

echo "--- Worker Socket 目录状态 ---"
if [ -d "$WORKER_DIR" ]; then
    echo "✅ $WORKER_DIR 存在"
    echo "修改时间: $(stat -f '%Sm' -t '%Y-%m-%d %H:%M:%S' "$WORKER_DIR")"
    WORKER_COUNT=$(ls -1 "$WORKER_DIR" 2>/dev/null | wc -l | tr -d ' ')
    echo "worker socket 文件数: $WORKER_COUNT"
    if [ "$WORKER_COUNT" -gt 0 ]; then
        ls -la "$WORKER_DIR" | head -10
    fi
else
    echo "❌ $WORKER_DIR 不存在（可能被 macOS 清理）"
fi
echo ""

echo "--- Bridge Log 最新 ENOENT ---"
if [ -f "$LOG" ]; then
    ENOENT_COUNT=$(grep -c "ENOENT.*hermes-agent-bridge-workers" "$LOG" 2>/dev/null || echo "0")
    echo "历史 ENOENT 次数: $ENOENT_COUNT"
    grep "ENOENT.*hermes-agent-bridge-workers" "$LOG" 2>/dev/null | tail -3 | while read line; do
        echo "  $(echo "$line" | cut -d',' -f1 | grep -o '"time":[0-9]*' | head -1)"
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
echo "=== 诊断完成 ==="
