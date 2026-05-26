#!/bin/bash
# APEX Spiral 测试运行脚本
# 支持 Python pytest 和 Rust cargo test

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  APEX Spiral 测试套件"
echo "========================================"

# -------------------------------------------
# 1. Python 测试 (pytest)
# -------------------------------------------
echo ""
echo "▶ [Python] 运行 pytest..."
echo "----------------------------------------"

if ! command -v pytest &> /dev/null; then
    echo "[WARN] pytest 未安装，尝试用 python3 -m pytest"
    python3 -m pytest tests/test_apex_v10.py -v --tb=short 2>&1 || {
        echo "[ERROR] Python 测试失败"
        exit 1
    }
else
    pytest tests/test_apex_v10.py -v --tb=short 2>&1 || {
        echo "[ERROR] Python 测试失败"
        exit 1
    }
fi

echo ""
echo "✅ Python 测试完成"

# -------------------------------------------
# 2. Rust 测试 (cargo test)
# -------------------------------------------
echo ""
echo "▶ [Rust] 运行 cargo test..."
echo "----------------------------------------"

if [ ! -f "Cargo.toml" ]; then
    echo "[WARN] Cargo.toml 不存在，跳过 Rust 测试"
else
    cargo test 2>&1 || {
        echo "[ERROR] Rust 测试失败"
        exit 1
    }
    echo ""
    echo "✅ Rust 测试完成"
fi

echo ""
echo "========================================"
echo "  全部测试通过 ✅"
echo "========================================"
