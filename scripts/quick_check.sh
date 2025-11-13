#!/bin/bash
#
# 快速检查脚本 - 验证v7.2.17修复是否已加载
#

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}快速检查：v7.2.17修复状态${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd ~/cryptosignal 2>/dev/null || { echo -e "${RED}❌ 项目目录不存在${NC}"; exit 1; }

# 1. 分支检查
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
CORRECT_BRANCH="claude/system-v7-refactor-cleanup-011CUzRUdHXVF1UFGJj9HaCH"

echo "1️⃣  分支检查:"
echo "   当前: $CURRENT_BRANCH"
if [ "$CURRENT_BRANCH" = "$CORRECT_BRANCH" ]; then
    echo -e "   ${GREEN}✅ 分支正确${NC}"
else
    echo -e "   ${RED}❌ 分支错误${NC}"
    echo "   期望: $CORRECT_BRANCH"
fi
echo ""

# 2. v7.2.17修复检查
echo "2️⃣  v7.2.17修复检查:"
if grep -q "def _get_dict" ats_core/outputs/telegram_fmt.py 2>/dev/null; then
    COUNT=$(grep -c "_get_dict(" ats_core/outputs/telegram_fmt.py 2>/dev/null || echo "0")
    echo -e "   ${GREEN}✅ _get_dict函数存在${NC}"
    echo "   调用次数: $COUNT (预期≥35)"
    if [ "$COUNT" -ge 35 ]; then
        echo -e "   ${GREEN}✅ 修复完整${NC}"
    else
        echo -e "   ${RED}❌ 修复不完整${NC}"
    fi
else
    echo -e "   ${RED}❌ _get_dict函数不存在${NC}"
    echo -e "   ${RED}⚠️  v7.2.17修复未加载！${NC}"
fi
echo ""

# 3. 缓存检查
echo "3️⃣  缓存检查:"
PYCACHE=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
PYC=$(find . -name "*.pyc" 2>/dev/null | wc -l)
echo "   __pycache__: $PYCACHE 个"
echo "   .pyc文件: $PYC 个"
if [ "$PYCACHE" -eq 0 ] && [ "$PYC" -eq 0 ]; then
    echo -e "   ${GREEN}✅ 无缓存${NC}"
else
    echo -e "   ${RED}⚠️  有缓存残留${NC}"
    echo "   建议运行: bash cleanup_all_cache.sh"
fi
echo ""

# 4. 进程检查
echo "4️⃣  进程检查:"
if ps aux | grep -v grep | grep "python.*cryptosignal" > /dev/null; then
    echo -e "   ${GREEN}✅ 系统运行中${NC}"
    ps aux | grep -v grep | grep "python.*cryptosignal" | awk '{print "   PID " $2 ": " $11}' | head -3
else
    echo -e "   ${RED}⚠️  系统未运行${NC}"
fi
echo ""

# 5. 最近提交
echo "5️⃣  最近提交:"
git log --oneline -3 2>/dev/null | sed 's/^/   /' || echo "   无法获取"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 总结
if [ "$CURRENT_BRANCH" = "$CORRECT_BRANCH" ] && grep -q "def _get_dict" ats_core/outputs/telegram_fmt.py 2>/dev/null; then
    echo -e "${GREEN}✅ 检查通过！v7.2.17修复已正确加载${NC}"
else
    echo -e "${RED}❌ 检查失败！需要清理缓存或切换分支${NC}"
    echo ""
    echo "建议操作："
    echo "   bash cleanup_all_cache.sh"
fi
echo ""
