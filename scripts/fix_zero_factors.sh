#!/bin/bash
# 修复所有因子显示0的问题

set -e

echo "========================================"
echo "🔧 修复v7.2因子显示0的问题"
echo "========================================"

cd ~/cryptosignal

# 1. 停止运行中的进程
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
echo "   ✅ 代码已更新到最新版本"

# 3. 清理Python缓存（重要！）
echo ""
echo "3️⃣  清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "   ✅ Python缓存已清理"

# 4. 运行诊断脚本
echo ""
echo "4️⃣  运行诊断脚本..."
python3 scripts/diagnose_server_v72.py

echo ""
echo "========================================"
echo "✅ 修复完成"
echo "========================================"
echo ""
echo "如果诊断通过，可以重新启动系统:"
echo "   ./setup.sh"
echo ""
