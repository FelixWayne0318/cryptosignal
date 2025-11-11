#!/bin/bash
# v7.2.17+ 系统启动脚本 - 使用正确分支
# 用法: ./start_system_correct_branch.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "  CryptoSignal v7.2.17+ 启动脚本"
echo "=========================================="

cd ~/cryptosignal

# 显示当前分支
echo ""
echo "🔍 检查当前分支..."
CURRENT_BRANCH=$(git branch --show-current)
echo "   当前分支: $CURRENT_BRANCH"

# 正确的分支（v7.2.17修复所在分支）
CORRECT_BRANCH="claude/system-v7-refactor-cleanup-011CUzRUdHXVF1UFGJj9HaCH"

echo ""
echo "📥 拉取最新代码..."
echo "   目标分支: $CORRECT_BRANCH"

# 强制同步到正确分支
git fetch origin "$CORRECT_BRANCH"
git reset --hard "origin/$CORRECT_BRANCH"

echo "✅ 已同步到最新代码"

# 验证是否有v7.2.17修复
echo ""
echo "🔍 验证v7.2.17修复..."
if grep -q "def _get_dict" ats_core/outputs/telegram_fmt.py; then
    echo "✅ 确认v7.2.17修复存在（_get_dict函数已存在）"
else
    echo "❌ 警告：未找到v7.2.17修复！"
    echo "   请检查分支是否正确"
    exit 1
fi

# 显示最近的commit
echo ""
echo "📋 最近的提交记录："
git log --oneline -3

# 清理Python缓存
echo ""
echo "🧹 清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "✅ 缓存已清理"

# 启动系统
echo ""
echo "🚀 启动系统..."
echo "=========================================="
./setup.sh

echo ""
echo "✅ 系统启动完成"
echo ""
echo "💡 提示："
echo "   - 如果仍有错误，请运行: python3 test_v7217_fix.py"
echo "   - 查看日志: tail -f logs/*.log"
