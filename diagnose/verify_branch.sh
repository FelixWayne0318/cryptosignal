#!/bin/bash
# 快速验证当前分支和v7.2.17修复状态

echo "=========================================="
echo "  分支和修复状态验证"
echo "=========================================="

cd ~/cryptosignal

# 1. 当前分支
CURRENT_BRANCH=$(git branch --show-current)
CORRECT_BRANCH="claude/system-v7-refactor-cleanup-011CUzRUdHXVF1UFGJj9HaCH"

echo ""
echo "📌 分支检查："
echo "   当前分支: $CURRENT_BRANCH"
echo "   正确分支: $CORRECT_BRANCH"

if [ "$CURRENT_BRANCH" = "$CORRECT_BRANCH" ]; then
    echo "   状态: ✅ 分支正确"
else
    echo "   状态: ❌ 分支错误！"
    echo ""
    echo "⚠️  您正在使用错误的分支！"
    echo "请运行: ./start_system_correct_branch.sh"
    exit 1
fi

# 2. v7.2.17修复验证
echo ""
echo "🔍 v7.2.17修复检查："

if [ -f "ats_core/outputs/telegram_fmt.py" ]; then
    if grep -q "def _get_dict" ats_core/outputs/telegram_fmt.py; then
        echo "   ✅ _get_dict函数存在"

        # 统计_get_dict使用次数
        COUNT=$(grep -c "_get_dict(" ats_core/outputs/telegram_fmt.py || echo "0")
        echo "   ✅ _get_dict调用次数: $COUNT"

        if [ "$COUNT" -ge 35 ]; then
            echo "   ✅ 修复已完整应用（预期≥35次调用）"
        else
            echo "   ⚠️  警告：调用次数少于预期（可能修复不完整）"
        fi
    else
        echo "   ❌ _get_dict函数不存在"
        echo "   ⚠️  v7.2.17修复未应用！"
        exit 1
    fi
else
    echo "   ❌ telegram_fmt.py文件不存在"
    exit 1
fi

# 3. 最近提交记录
echo ""
echo "📋 最近3次提交："
git log --oneline -3

# 4. Python缓存状态
echo ""
echo "🧹 Python缓存检查："
CACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
PYC_COUNT=$(find . -name "*.pyc" 2>/dev/null | wc -l)

if [ "$CACHE_COUNT" -gt 0 ] || [ "$PYC_COUNT" -gt 0 ]; then
    echo "   ⚠️  发现缓存文件："
    echo "      __pycache__目录: $CACHE_COUNT 个"
    echo "      .pyc文件: $PYC_COUNT 个"
    echo "   建议运行清理："
    echo "      find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null"
    echo "      find . -name '*.pyc' -delete 2>/dev/null"
else
    echo "   ✅ 无缓存文件"
fi

# 5. 测试脚本检查
echo ""
echo "🧪 测试脚本检查："
if [ -f "test_v7217_fix.py" ]; then
    echo "   ✅ test_v7217_fix.py 存在"
    echo "   建议运行: python3 test_v7217_fix.py"
else
    echo "   ❌ test_v7217_fix.py 不存在"
fi

echo ""
echo "=========================================="
echo "✅ 验证完成！"
echo ""
echo "💡 如果一切正常，系统应该不会再出现"
echo "   'str' object has no attribute 'get'错误"
echo "=========================================="
