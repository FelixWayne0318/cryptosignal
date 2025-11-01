#!/bin/bash
# 停止CryptoSignal系统

echo "========================================"
echo "🛑 停止CryptoSignal系统"
echo "========================================"
echo ""

# 检查进程
PROCESS_COUNT=$(ps aux | grep "realtime_signal_scanner.py" | grep -v grep | wc -l)

if [ "$PROCESS_COUNT" -eq 0 ]; then
    echo "ℹ️  系统未运行"
    exit 0
fi

echo "找到 $PROCESS_COUNT 个运行中的进程："
ps aux | grep "realtime_signal_scanner.py" | grep -v grep | awk '{print "  PID: " $2 " | 用户: " $1 " | 命令: " $11 " " $12 " " $13}'
echo ""

read -p "确认停止？(y/N): " CONFIRM

if [[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]]; then
    echo "正在停止..."
    pkill -f realtime_signal_scanner.py
    sleep 2

    # 再次检查
    STILL_RUNNING=$(ps aux | grep "realtime_signal_scanner.py" | grep -v grep | wc -l)
    if [ "$STILL_RUNNING" -eq 0 ]; then
        echo "✅ 系统已停止"
    else
        echo "⚠️  部分进程仍在运行，尝试强制停止..."
        pkill -9 -f realtime_signal_scanner.py
        sleep 1
        echo "✅ 已强制停止"
    fi
else
    echo "取消操作"
fi
