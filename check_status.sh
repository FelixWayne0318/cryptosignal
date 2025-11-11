#!/bin/bash
# ==========================================
# v7.2 系统状态检查脚本
# 用途：检查扫描器运行状态和数据采集情况
# ==========================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=============================================="
echo "🔍 v7.2 系统状态检查"
echo "=============================================="
echo ""

# 1. 检查进程
echo -e "${BLUE}1️⃣  进程状态${NC}"
echo "=============================================="
if pgrep -f "realtime_signal_scanner.py" > /dev/null; then
    PID=$(pgrep -f "realtime_signal_scanner.py")
    echo -e "${GREEN}✅ 扫描器运行中${NC}"
    echo "   进程ID: $PID"
    echo "   运行时间: $(ps -p $PID -o etime= | tr -d ' ')"
    echo "   内存使用: $(ps -p $PID -o rss= | awk '{printf "%.1f MB", $1/1024}')"
else
    echo -e "${RED}❌ 扫描器未运行${NC}"
fi
echo ""

# 2. 检查日志文件
echo -e "${BLUE}2️⃣  最近日志${NC}"
echo "=============================================="
LATEST_LOG=$(ls -t ~/cryptosignal_*.log 2>/dev/null | head -1)
if [ -f "$LATEST_LOG" ]; then
    echo -e "${GREEN}✅ 日志文件: $LATEST_LOG${NC}"
    echo ""
    echo "最后20行日志:"
    echo "---"
    tail -20 "$LATEST_LOG" | sed 's/^/   /'
else
    # 尝试查找logs目录
    LATEST_LOG=$(ls -t ~/cryptosignal/logs/scanner_*.log 2>/dev/null | head -1)
    if [ -f "$LATEST_LOG" ]; then
        echo -e "${GREEN}✅ 日志文件: $LATEST_LOG${NC}"
        echo ""
        echo "最后20行日志:"
        echo "---"
        tail -20 "$LATEST_LOG" | sed 's/^/   /'
    else
        echo -e "${YELLOW}⚠️  未找到日志文件${NC}"
    fi
fi
echo ""

# 3. 检查数据库
echo -e "${BLUE}3️⃣  数据库状态${NC}"
echo "=============================================="
cd ~/cryptosignal

if [ -f "data/analysis.db" ]; then
    SIZE=$(du -h data/analysis.db | cut -f1)
    echo -e "${GREEN}✅ AnalysisDB: $SIZE${NC}"

    # 查询信号数量
    python3 -c "
import sys
sys.path.insert(0, '.')
from ats_core.data.analysis_db import get_analysis_db
db = get_analysis_db()
stats = db.get_gate_statistics()
print(f'   - 总信号数: {stats[\"total_signals\"]}')
print(f'   - 通过闸门: {int(stats[\"all_gates_pass_rate\"]*100)}%')
if stats['total_signals'] > 0:
    for i in range(1, 5):
        rate = stats.get(f'gate{i}_pass_rate', 0)
        print(f'   - 闸门{i}通过率: {int(rate*100)}%')

# v7.2: 显示扫描历史统计
scan_history = db.get_scan_history(days=7)
if scan_history:
    print(f'   - 近7天扫描: {len(scan_history)}次')
    if len(scan_history) > 0:
        latest = scan_history[0]
        print(f'   - 最近扫描: {latest[\"scan_date\"]} ({latest[\"signals_found\"]}个信号)')
" 2>/dev/null || echo "   ⚠️  无法读取统计信息"
else
    echo -e "${YELLOW}⚠️  analysis.db 不存在${NC}"
fi
echo ""

if [ -f "data/trade_history.db" ]; then
    SIZE=$(du -h data/trade_history.db | cut -f1)
    echo -e "${GREEN}✅ TradeRecorder: $SIZE${NC}"

    python3 -c "
import sys
sys.path.insert(0, '.')
from ats_core.data.trade_recorder import get_recorder
recorder = get_recorder()
stats = recorder.get_statistics()
print(f'   - 记录信号: {stats[\"total_signals\"]}')
print(f'   - 通过闸门: {stats[\"gates_passed\"]} ({int(stats[\"gates_pass_rate\"]*100)}%)')
" 2>/dev/null || echo "   ⚠️  无法读取统计信息"
else
    echo -e "${YELLOW}⚠️  trade_history.db 不存在${NC}"
fi
echo ""

# 4. 检查最近扫描
echo -e "${BLUE}4️⃣  最近扫描活动${NC}"
echo "=============================================="
if [ -f "reports/latest/scan_summary.json" ]; then
    python3 -c "
import json
with open('reports/latest/scan_summary.json') as f:
    data = json.load(f)
print(f'   扫描时间: {data.get(\"timestamp\", \"未知\")}')
print(f'   扫描币种: {data.get(\"total_symbols\", 0)}')
print(f'   发现信号: {data.get(\"signals_found\", 0)}')
print(f'   过滤信号: {data.get(\"filtered_signals\", 0)}')
" 2>/dev/null || echo "   ⚠️  无法读取扫描报告"
else
    echo -e "${YELLOW}⚠️  未找到扫描报告${NC}"
fi
echo ""

# 5. 提供管理命令
echo -e "${BLUE}5️⃣  管理命令${NC}"
echo "=============================================="
echo "查看实时日志:"
echo "   tail -f ~/cryptosignal_*.log"
echo ""
echo "查看数据库统计:"
echo "   cd ~/cryptosignal && python3 -c 'from ats_core.data.analysis_db import get_analysis_db; db=get_analysis_db(); print(db.get_gate_statistics())'"
echo ""
echo "重启扫描器:"
echo "   ~/cryptosignal/auto_restart.sh"
echo ""
echo "停止扫描器:"
echo "   pkill -f realtime_signal_scanner.py"
echo ""
echo "=============================================="
echo -e "${GREEN}✅ 状态检查完成${NC}"
echo "=============================================="
