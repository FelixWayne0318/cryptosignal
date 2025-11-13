#!/bin/bash
# iPhone友好的快速重启脚本
# 用途：拉取最新代码并重启系统

set -e

echo "========================================"
echo "🔄 重启v7.2系统"
echo "========================================"

cd ~/cryptosignal

# 1. 停止旧进程
echo ""
echo "1️⃣  停止旧进程..."
pkill -f "python.*cryptosignal" || true
pkill -f "python.*realtime_signal_scanner" || true
sleep 2
echo "   ✅ 旧进程已停止"

# 2. 拉取最新代码
echo ""
echo "2️⃣  拉取最新代码..."
git fetch origin claude/system-refactor-v7.2-011CUyBts14z3AdVhv9BSubr
git reset --hard origin/claude/system-refactor-v7.2-011CUyBts14z3AdVhv9BSubr
echo "   ✅ 代码已更新"

# 3. 清理Python缓存
echo ""
echo "3️⃣  清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "   ✅ 缓存已清理"

# 4. 启动系统
echo ""
echo "4️⃣  启动系统..."
./setup.sh

echo ""
echo "========================================"
echo "✅ 系统重启完成"
echo "========================================"
