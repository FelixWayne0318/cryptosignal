#!/bin/bash
# 查看CryptoSignal实时日志输出

LOG_FILE="/tmp/cryptosignal_scanner.log"

echo "========================================"
echo "📋 CryptoSignal 实时日志"
echo "========================================"
echo ""
echo "日志文件: $LOG_FILE"
echo "按 Ctrl+C 退出"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "$LOG_FILE" ]; then
    # 实时跟踪日志（类似刚开始运行时的动态显示）
    tail -f "$LOG_FILE"
else
    echo "❌ 日志文件不存在"
    echo ""
    echo "可能原因："
    echo "  1. 系统未在后台运行"
    echo "  2. 使用了screen/tmux（日志在会话内）"
    echo ""
    echo "解决方法："
    echo "  • 如果使用screen: screen -r cryptosignal"
    echo "  • 如果使用tmux: tmux attach -t cryptosignal"
    echo "  • 检查系统状态: ./check_status.sh"
fi
