#!/bin/bash
# ==========================================
# v7.2 实时日志启动脚本
# 用途：前台运行扫描器，显示实时日志
# 特点：Ctrl+C 停止，SSH断开后程序继续运行
# ==========================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cd ~/cryptosignal

echo "=============================================="
echo "🚀 v7.2 扫描器（实时日志模式）"
echo "=============================================="
echo ""

# 停止旧进程
echo "🛑 停止旧进程..."
pkill -f realtime_signal_scanner_v72.py 2>/dev/null || true
screen -S cryptosignal -X quit 2>/dev/null || true
sleep 1
echo ""

# 检查Python环境
if ! python3 -c "import sys; sys.path.insert(0, '.'); from ats_core.data.analysis_db import get_analysis_db" 2>/dev/null; then
    echo -e "${YELLOW}⚠️ 首次运行，正在初始化环境...${NC}"
    python3 -c "
import sys
sys.path.insert(0, '.')
from ats_core.data.trade_recorder import get_recorder
from ats_core.data.analysis_db import get_analysis_db
get_recorder()
get_analysis_db()
print('✅ 数据库初始化完成')
"
    echo ""
fi

echo -e "${GREEN}✅ 准备就绪${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 使用说明："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  • 即将显示实时滚动日志"
echo "  • 按 Ctrl+C 可以停止程序"
echo "  • 关闭SSH窗口程序会停止（前台模式）"
echo ""
echo "  如果需要后台运行（SSH断开后继续）："
echo "  请使用: ~/cryptosignal/auto_restart.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⏳ 3秒后启动..."
sleep 3

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}🟢 实时日志（按 Ctrl+C 停止）${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 前台运行，显示实时日志
python3 scripts/realtime_signal_scanner_v72.py --interval 300

# 如果程序退出
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}⚠️ 程序已停止${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "重新启动: ~/cryptosignal/start_live.sh"
echo "后台运行: ~/cryptosignal/auto_restart.sh"
echo ""
