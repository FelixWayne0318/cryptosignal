#!/bin/bash
# ==========================================
# CryptoSignal 服务器版本诊断脚本
# 用途：检查服务器是否运行v7.4版本
# ==========================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=============================================="
echo "🔍 CryptoSignal 服务器版本诊断"
echo "=============================================="
echo ""

# 1. 检查当前Git分支和版本
echo "📍 1. Git代码版本检查"
echo "----------------------------------------------"
cd ~/cryptosignal 2>/dev/null || {
    echo -e "${RED}❌ ~/cryptosignal 目录不存在${NC}"
    exit 1
}

CURRENT_BRANCH=$(git branch --show-current)
LATEST_COMMIT=$(git log -1 --oneline | head -1)
echo -e "  当前分支: ${GREEN}$CURRENT_BRANCH${NC}"
echo "  最新提交: $LATEST_COMMIT"

# 检查是否有未拉取的远程更新
git fetch origin > /dev/null 2>&1
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "no-remote")
if [ "$LOCAL" != "$REMOTE" ] && [ "$REMOTE" != "no-remote" ]; then
    echo -e "${YELLOW}  ⚠️  本地代码落后于远程，需要拉取更新！${NC}"
    NEEDS_PULL=1
else
    echo -e "${GREEN}  ✅ 本地代码与远程同步${NC}"
    NEEDS_PULL=0
fi

echo ""

# 2. 检查配置文件版本
echo "📍 2. 配置文件版本检查"
echo "----------------------------------------------"
FOUR_STEP_ENABLED=$(python3 -c "
import json
with open('config/params.json') as f:
    params = json.load(f)
print(params.get('four_step_system', {}).get('enabled', False))
" 2>/dev/null || echo "ERROR")

FUSION_ENABLED=$(python3 -c "
import json
with open('config/params.json') as f:
    params = json.load(f)
print(params.get('four_step_system', {}).get('fusion_mode', {}).get('enabled', False))
" 2>/dev/null || echo "ERROR")

if [ "$FOUR_STEP_ENABLED" == "True" ]; then
    echo -e "  four_step_system.enabled: ${GREEN}$FOUR_STEP_ENABLED ✅${NC}"
else
    echo -e "  four_step_system.enabled: ${RED}$FOUR_STEP_ENABLED ❌${NC}"
fi

if [ "$FUSION_ENABLED" == "True" ]; then
    echo -e "  fusion_mode.enabled: ${GREEN}$FUSION_ENABLED ✅${NC}"
else
    echo -e "  fusion_mode.enabled: ${RED}$FUSION_ENABLED ❌${NC}"
fi

echo ""

# 3. 检查四步系统模块是否存在
echo "📍 3. 四步系统模块检查"
echo "----------------------------------------------"
MODULES=(
    "ats_core/decision/step1_direction.py"
    "ats_core/decision/step2_timing.py"
    "ats_core/decision/step3_risk.py"
    "ats_core/decision/step4_quality.py"
    "ats_core/decision/four_step_system.py"
)

ALL_MODULES_EXIST=1
for module in "${MODULES[@]}"; do
    if [ -f "$module" ]; then
        echo -e "  ✅ $module"
    else
        echo -e "  ${RED}❌ $module (缺失)${NC}"
        ALL_MODULES_EXIST=0
    fi
done

echo ""

# 4. 检查运行中的进程
echo "📍 4. 运行进程检查"
echo "----------------------------------------------"
RUNNING_PROCESSES=$(ps aux | grep "realtime_signal_scanner" | grep -v grep | wc -l)
if [ "$RUNNING_PROCESSES" -gt 0 ]; then
    echo -e "  ${GREEN}✅ 检测到 $RUNNING_PROCESSES 个扫描器进程正在运行${NC}"
    echo ""
    echo "  进程详情："
    ps aux | grep "realtime_signal_scanner" | grep -v grep | awk '{print "    PID: "$2", CMD: "$11" "$12" "$13}'
else
    echo -e "  ${YELLOW}⚠️  未检测到运行中的扫描器进程${NC}"
fi

echo ""

# 5. 检查Python缓存
echo "📍 5. Python缓存检查"
echo "----------------------------------------------"
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
PYC_COUNT=$(find . -name "*.pyc" 2>/dev/null | wc -l)

if [ "$PYCACHE_COUNT" -gt 0 ] || [ "$PYC_COUNT" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠️  发现Python缓存:${NC}"
    echo "    __pycache__目录: $PYCACHE_COUNT 个"
    echo "    .pyc文件: $PYC_COUNT 个"
    echo -e "    ${YELLOW}建议清理缓存后重启${NC}"
else
    echo -e "  ${GREEN}✅ 无Python缓存${NC}"
fi

echo ""

# 6. 检查最新日志文件
echo "📍 6. 最新日志检查"
echo "----------------------------------------------"
LATEST_LOG=$(ls -t ~/cryptosignal_*.log 2>/dev/null | head -1)
if [ -n "$LATEST_LOG" ]; then
    echo "  最新日志: $LATEST_LOG"
    echo "  创建时间: $(stat -c %y "$LATEST_LOG" 2>/dev/null | cut -d'.' -f1)"

    # 检查日志中的版本标识
    if grep -q "v7.4" "$LATEST_LOG" 2>/dev/null; then
        echo -e "  ${GREEN}✅ 日志显示v7.4版本${NC}"
    elif grep -q "v7.3" "$LATEST_LOG" 2>/dev/null; then
        echo -e "  ${RED}❌ 日志显示v7.3版本（旧版本）${NC}"
    else
        echo -e "  ${YELLOW}⚠️  日志中未找到明确版本标识${NC}"
    fi

    # 检查是否有四步系统输出
    if grep -q "Step1.*方向确认\|Step2.*时机判断\|Enhanced.*F.*v2" "$LATEST_LOG" 2>/dev/null; then
        echo -e "  ${GREEN}✅ 日志包含四步系统输出${NC}"
    else
        echo -e "  ${RED}❌ 日志缺少四步系统输出${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  未找到日志文件${NC}"
fi

echo ""
echo "=============================================="
echo "📋 诊断结果汇总"
echo "=============================================="

# 综合判断
ISSUES=()

if [ "$NEEDS_PULL" -eq 1 ]; then
    ISSUES+=("本地代码需要更新")
fi

if [ "$FOUR_STEP_ENABLED" != "True" ]; then
    ISSUES+=("四步系统未启用")
fi

if [ "$ALL_MODULES_EXIST" -eq 0 ]; then
    ISSUES+=("四步系统模块缺失")
fi

if [ "$RUNNING_PROCESSES" -eq 0 ]; then
    ISSUES+=("扫描器进程未运行")
fi

if [ "$PYCACHE_COUNT" -gt 0 ] || [ "$PYC_COUNT" -gt 0 ]; then
    ISSUES+=("存在Python缓存")
fi

if [ ${#ISSUES[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ 系统状态正常，应该运行v7.4版本${NC}"
    echo ""
    echo "如果日志仍显示旧版本，请执行："
    echo "  1. 清理Python缓存"
    echo "  2. 重启服务器进程"
else
    echo -e "${RED}❌ 发现以下问题：${NC}"
    for issue in "${ISSUES[@]}"; do
        echo "  • $issue"
    done
    echo ""
    echo -e "${YELLOW}🔧 建议修复步骤：${NC}"
    echo ""

    if [ "$NEEDS_PULL" -eq 1 ]; then
        echo "  1️⃣  拉取最新代码："
        echo "     cd ~/cryptosignal"
        echo "     git pull --rebase origin $CURRENT_BRANCH"
        echo ""
    fi

    echo "  2️⃣  清理Python缓存："
    echo "     cd ~/cryptosignal"
    echo "     find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true"
    echo "     find . -name '*.pyc' -delete 2>/dev/null || true"
    echo ""

    echo "  3️⃣  重启服务器："
    echo "     cd ~/cryptosignal"
    echo "     ./setup.sh"
    echo ""

    echo "  或者使用一键修复脚本："
    echo "     cd ~/cryptosignal && ./fix_server_version.sh"
    echo ""
fi

echo "=============================================="
