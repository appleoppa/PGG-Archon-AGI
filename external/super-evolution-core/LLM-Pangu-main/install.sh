#!/bin/bash
# install.sh - 盘古安装脚本

set -e

echo "============================================"
echo "  盘古 Pangu - LLM防幻觉框架安装"
echo "============================================"
echo ""

# 检查Python版本
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.8"

if [ $(echo -e "$python_version\n$required_version" | sort -V | head -n1) != "$required_version" ]; then
    echo "❌ Python版本过低: $python_version (需要 >= 3.8)"
    exit 1
fi
echo "✅ Python版本: $python_version"

# 创建目录
echo ""
echo "📁 创建目录结构..."
mkdir -p storage/backups
mkdir -p storage/skills
mkdir -p baseline-v1
mkdir -p examples
echo "✅ 目录创建完成"

# 安装依赖
echo ""
echo "📦 安装Python依赖..."
pip install pytest pyyaml --quiet

# 初始化存储
echo ""
echo "💾 初始化存储..."
if [ ! -f "storage/pangu_memory.json" ]; then
    echo '{"_meta": {"version": 1, "last_updated": ""}, "long_term": {}, "short_term": []}' > storage/pangu_memory.json
    echo "✅ 记忆文件创建完成"
fi

# 运行测试
echo ""
echo "🧪 运行测试..."
python3 -m pytest tests/ -v --tb=short || echo "⚠️ 部分测试可能失败，请检查"

# 完成
echo ""
echo "============================================"
echo "  🎉 盘古安装完成！"
echo "============================================"
echo ""
echo "快速开始："
echo "  python3 run_init.py"
echo ""
echo "运行测试："
echo "  python3 -m pytest tests/ -v"
echo ""
