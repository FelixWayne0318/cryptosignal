#!/bin/bash
# 检查CryptoSignal系统运行状态

echo "========================================"
echo "🔍 CryptoSignal 系统状态检查"
echo "========================================"
echo ""

# 1. 检查进程是否在运行
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  检查进程状态"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PROCESS_COUNT=$(ps aux | grep "realtime_signal_scanner" | grep -v grep | wc -l)

if [ "$PROCESS_COUNT" -gt 0 ]; then
    echo "✅ 系统正在运行！"
    echo ""
    echo "进程信息："
    ps aux | grep "realtime_signal_scanner" | grep -v grep | awk '{printf "  PID: %s\n  用户: %s\n  CPU: %s%%\n  内存: %s%%\n  启动时间: %s %s\n  运行时长: %s\n  命令: %s %s %s %s %s\n", $2, $1, $3, $4, $9, $10, $11, $12, $13, $14, $15, $16}'
    echo ""
else
    echo "❌ 系统未运行"
    echo ""
fi

# 2. 检查日志文件
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  最近日志输出（最后20行）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

LOG_FILE="/tmp/cryptosignal_scanner.log"

if [ -f "$LOG_FILE" ]; then
    echo "日志文件: $LOG_FILE"
    echo "文件大小: $(du -h $LOG_FILE | cut -f1)"
    echo "最后更新: $(stat -c %y $LOG_FILE | cut -d. -f1)"
    echo ""
    echo "最近输出："
    echo "────────────────────────────────────────"
    tail -20 "$LOG_FILE"
    echo "────────────────────────────────────────"
else
    echo "⚠️  未找到日志文件"
    echo ""
fi

# 3. 检查screen/tmux会话
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  检查Screen/Tmux会话"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查screen
SCREEN_COUNT=$(screen -ls 2>/dev/null | grep cryptosignal | wc -l)
if [ "$SCREEN_COUNT" -gt 0 ]; then
    echo "✅ 找到Screen会话："
    screen -ls | grep cryptosignal
    echo ""
    echo "重新连接命令："
    echo "  screen -r cryptosignal"
else
    echo "ℹ️  未找到Screen会话"
fi

# 检查tmux
TMUX_COUNT=$(tmux ls 2>/dev/null | grep cryptosignal | wc -l)
if [ "$TMUX_COUNT" -gt 0 ]; then
    echo "✅ 找到Tmux会话："
    tmux ls | grep cryptosignal
    echo ""
    echo "重新连接命令："
    echo "  tmux attach -t cryptosignal"
else
    echo "ℹ️  未找到Tmux会话"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 常用命令"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "查看实时日志："
echo "  ./view_logs.sh"
echo ""
echo "停止系统："
echo "  pkill -f realtime_signal_scanner"
echo ""
echo "重新启动："
echo "  ./run_production.sh"
echo "  或使用后台运行："
echo "  ./run_background.sh"
echo ""
