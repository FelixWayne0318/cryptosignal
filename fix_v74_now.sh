#!/bin/bash

# v7.4一键修复脚本 - 解决进程使用旧代码问题

echo "========================================="
echo "🔧 CryptoSignal v7.4 一键修复"
echo "========================================="
echo ""

# 1. 停止旧进程
echo "1️⃣ 停止旧进程..."
if pgrep -f "realtime_signal_scanner" > /dev/null; then
    pkill -f "realtime_signal_scanner"
    echo "✅ 旧进程已停止"
    sleep 2
else
    echo "⚠️ 未找到运行中的进程"
fi

# 2. 清理Python缓存（关键！）
echo ""
echo "2️⃣ 清理Python缓存（包括.pyc文件）..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null
echo "✅ Python缓存已清理"

# 验证缓存清理
REMAINING_CACHE=$(find . -type d -name "__pycache__" | wc -l)
echo "   剩余 __pycache__ 目录: $REMAINING_CACHE"

# 3. 验证代码
echo ""
echo "3️⃣ 验证最新代码..."
if grep -q "CFG.reload()" ats_core/pipeline/analyze_symbol.py; then
    echo "✅ CFG.reload() 存在"
else
    echo "❌ CFG.reload() 不存在，请先 git pull"
    exit 1
fi

if grep -q "🔍 \[v7.4诊断\]" ats_core/pipeline/analyze_symbol.py; then
    echo "✅ v7.4诊断日志存在"
else
    echo "❌ v7.4诊断日志不存在"
fi

# 4. 验证配置
echo ""
echo "4️⃣ 验证配置..."
if grep -q '"enabled": true' config/params.json | head -1; then
    echo "✅ four_step_system.enabled = true"
else
    echo "⚠️ 请检查配置文件"
fi

# 5. 重启服务
echo ""
echo "5️⃣ 重启服务（使用setup.sh）..."
echo "========================================="
nohup ./setup.sh > /tmp/cryptosignal_startup.log 2>&1 &
sleep 5

# 6. 验证进程
echo ""
echo "6️⃣ 验证新进程..."
if pgrep -f "realtime_signal_scanner" > /dev/null; then
    NEW_PID=$(pgrep -f "realtime_signal_scanner" | head -1)
    echo "✅ 新进程已启动 (PID: $NEW_PID)"
    echo "   启动时间: $(ps -p $NEW_PID -o lstart=)"
else
    echo "❌ 进程启动失败！"
    echo "查看启动日志: cat /tmp/cryptosignal_startup.log"
    exit 1
fi

# 7. 实时日志监控（找到正确的日志文件）
echo ""
echo "7️⃣ 实时日志监控（查找v7.4诊断输出）..."
echo "========================================="
echo ""
echo "等待日志输出（30秒）..."
sleep 30

# 查找最新的日志文件
LATEST_LOG=$(find /tmp -name "cryptosignal*.log" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" ")

if [ -n "$LATEST_LOG" ]; then
    echo "📋 日志文件: $LATEST_LOG"
    echo ""
    echo "查找v7.4诊断标记:"
    echo "-----------------------------------"
    tail -100 "$LATEST_LOG" | grep -E "(🔍.*v7.4诊断|🚀.*v7.4|Step[1-4]|Entry|入场价)" | tail -20
    echo ""
    echo "查找配置状态:"
    echo "-----------------------------------"
    tail -100 "$LATEST_LOG" | grep -i "four_step_system.enabled" | tail -5
    echo ""
fi

# 8. 提供下一步指令
echo ""
echo "========================================="
echo "✅ 修复完成"
echo "========================================="
echo ""
echo "📊 下一步验证："
echo "1. 实时监控日志:"
echo "   tail -f $LATEST_LOG | grep -E '(v7.4|Step|Entry)'"
echo ""
echo "2. 查看配置诊断输出:"
echo "   tail -f $LATEST_LOG | grep '🔍'"
echo ""
echo "3. 如果还是没有v7.4输出，请运行完整诊断:"
echo "   ./diagnose_v74_issue.sh"
echo ""
