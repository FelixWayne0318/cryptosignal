#!/bin/bash
# ==========================================
# CryptoSignal 服务器版本修复脚本
# 用途：一键修复服务器版本问题，确保运行v7.4
# ==========================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=============================================="
echo "🔧 CryptoSignal v7.4 服务器修复"
echo "=============================================="
echo ""

# 进入项目目录
cd ~/cryptosignal 2>/dev/null || {
    echo -e "${RED}❌ ~/cryptosignal 目录不存在${NC}"
    exit 1
}

CURRENT_BRANCH=$(git branch --show-current)
echo -e "当前分支: ${GREEN}$CURRENT_BRANCH${NC}"
echo ""

# 步骤1: 停止旧进程
echo "1️⃣  停止旧进程..."
echo "----------------------------------------------"
pkill -f realtime_signal_scanner 2>/dev/null && echo -e "${GREEN}✅ 已停止旧进程${NC}" || echo -e "${YELLOW}⚠️  未发现运行中的进程${NC}"
sleep 2
echo ""

# 步骤2: 拉取最新代码
echo "2️⃣  拉取最新代码..."
echo "----------------------------------------------"
# 保存本地修改（如果有）
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${YELLOW}⚠️  检测到本地修改，正在保存...${NC}"
    BACKUP_NAME="自动备份_$(date +%Y%m%d_%H%M%S)"
    git stash save "$BACKUP_NAME" 2>/dev/null || true
    echo -e "${GREEN}✅ 本地修改已备份: $BACKUP_NAME${NC}"
fi

# 拉取远程代码
if git fetch origin; then
    if git pull --rebase origin "$CURRENT_BRANCH" 2>/dev/null; then
        echo -e "${GREEN}✅ 代码已更新到最新版本${NC}"
    else
        echo -e "${YELLOW}⚠️  检测到分支分歧，强制同步到远程最新版本...${NC}"
        git reset --hard origin/"$CURRENT_BRANCH" 2>/dev/null || true
        echo -e "${GREEN}✅ 已同步到远程最新版本${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  代码拉取失败（可能网络问题），继续使用本地版本...${NC}"
fi
echo ""

# 步骤3: 清理Python缓存
echo "3️⃣  清理Python缓存..."
echo "----------------------------------------------"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✅ Python缓存已清理${NC}"
echo ""

# 步骤4: 验证配置
echo "4️⃣  验证v7.4配置..."
echo "----------------------------------------------"
FOUR_STEP_ENABLED=$(python3 -c "
import json
with open('config/params.json') as f:
    params = json.load(f)
print(params.get('four_step_system', {}).get('enabled', False))
" 2>/dev/null)

FUSION_ENABLED=$(python3 -c "
import json
with open('config/params.json') as f:
    params = json.load(f)
print(params.get('four_step_system', {}).get('fusion_mode', {}).get('enabled', False))
" 2>/dev/null)

if [ "$FOUR_STEP_ENABLED" == "True" ] && [ "$FUSION_ENABLED" == "True" ]; then
    echo -e "${GREEN}✅ v7.4配置正确${NC}"
    echo "  • four_step_system.enabled: True"
    echo "  • fusion_mode.enabled: True"
else
    echo -e "${RED}❌ v7.4配置错误${NC}"
    echo "  • four_step_system.enabled: $FOUR_STEP_ENABLED"
    echo "  • fusion_mode.enabled: $FUSION_ENABLED"
    echo ""
    echo -e "${RED}请检查config/params.json配置文件${NC}"
    exit 1
fi
echo ""

# 步骤5: 验证四步系统模块
echo "5️⃣  验证四步系统模块..."
echo "----------------------------------------------"
MODULES=(
    "ats_core/decision/step1_direction.py"
    "ats_core/decision/step2_timing.py"
    "ats_core/decision/step3_risk.py"
    "ats_core/decision/step4_quality.py"
    "ats_core/decision/four_step_system.py"
)

ALL_EXIST=1
for module in "${MODULES[@]}"; do
    if [ -f "$module" ]; then
        echo -e "  ✅ $module"
    else
        echo -e "  ${RED}❌ $module (缺失)${NC}"
        ALL_EXIST=0
    fi
done

if [ "$ALL_EXIST" -eq 0 ]; then
    echo ""
    echo -e "${RED}❌ 四步系统模块缺失，请检查代码是否完整${NC}"
    exit 1
fi
echo ""

# 步骤6: 重启服务器
echo "6️⃣  重启v7.4服务器..."
echo "----------------------------------------------"
echo -e "${GREEN}正在启动 v7.4 扫描器...${NC}"
echo ""

# 创建日志文件名
LOG_FILE=~/cryptosignal_$(date +%Y%m%d_%H%M%S).log

# 后台启动扫描器
SCANNER_SCRIPT="${SCANNER_SCRIPT:-scripts/realtime_signal_scanner.py}"
SCAN_INTERVAL="${SCAN_INTERVAL:-300}"
AUTO_COMMIT_REPORTS="${AUTO_COMMIT_REPORTS:-false}"

export AUTO_COMMIT_REPORTS
nohup python3 "$SCANNER_SCRIPT" --interval "$SCAN_INTERVAL" > "$LOG_FILE" 2>&1 &
PID=$!

sleep 3

# 验证启动
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ v7.4扫描器已启动（PID: $PID）${NC}"
    echo "   日志文件: $LOG_FILE"
    echo ""
else
    echo -e "${RED}❌ 启动失败${NC}"
    echo "请查看日志: cat $LOG_FILE"
    exit 1
fi

# 步骤7: 验证v7.4运行
echo "7️⃣  验证v7.4运行状态..."
echo "----------------------------------------------"
echo "等待5秒，让系统初始化..."
sleep 5

# 检查日志中的v7.4标识
if grep -q "v7.4\|四步系统\|Step1.*方向确认\|Enhanced.*F.*v2" "$LOG_FILE" 2>/dev/null; then
    echo -e "${GREEN}✅ 日志确认v7.4四步系统正在运行${NC}"
else
    echo -e "${YELLOW}⚠️  日志中未找到v7.4标识，请等待首次扫描完成${NC}"
fi
echo ""

echo "=============================================="
echo -e "${GREEN}✅ 修复完成！${NC}"
echo "=============================================="
echo ""
echo "📋 下一步："
echo "  1. 查看实时日志（按Ctrl+C退出查看）："
echo "     tail -f $LOG_FILE"
echo ""
echo "  2. 等待下一次扫描完成（默认5分钟间隔）"
echo "     日志应该显示："
echo "     • 🚀 v7.4: 启动四步系统"
echo "     • Step1: 方向确认"
echo "     • Step2: 时机判断（Enhanced F v2）"
echo "     • Step3: 风险管理（Entry/SL/TP）"
echo "     • Step4: 质量控制"
echo ""
echo "  3. 如仍有问题，运行诊断脚本："
echo "     ~/cryptosignal/diagnose_server_version.sh"
echo ""
echo "=============================================="
echo ""

# 显示实时日志
echo -e "${GREEN}🟢 正在显示实时日志（按 Ctrl+C 退出查看，程序继续运行）${NC}"
echo "=============================================="
echo ""
sleep 2
tail -f "$LOG_FILE"
