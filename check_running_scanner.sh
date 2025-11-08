#!/bin/bash
# 检查正在运行的扫描器的工作目录

echo "===== 检查正在运行的扫描器 ====="

# 查找进程
PID=$(pgrep -f "realtime_signal_scanner_v72.py" | head -1)

if [ -z "$PID" ]; then
    echo "❌ 没有找到运行中的 realtime_signal_scanner_v72.py"
    exit 1
fi

echo "✅ 找到进程: PID=$PID"
echo ""

# 查看进程的工作目录
echo "工作目录:"
readlink -f /proc/$PID/cwd 2>/dev/null || echo "无法读取"

echo ""
echo "命令行:"
cat /proc/$PID/cmdline 2>/dev/null | tr '\0' ' ' || echo "无法读取"
echo ""

echo ""
echo "环境变量 (与路径相关):"
cat /proc/$PID/environ 2>/dev/null | tr '\0' '\n' | grep -E "PWD|HOME|PATH|PYTHON" || echo "无法读取"
