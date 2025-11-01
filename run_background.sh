#!/bin/bash
# CryptoSignal 后台运行脚本（防止终端断开）

set -e

echo "========================================"
echo "🚀 CryptoSignal 后台运行模式"
echo "========================================"
echo ""

# 1. 切换到项目目录
PROJECT_DIR="/home/user/cryptosignal"
cd "$PROJECT_DIR"

# 2. 检查是否已经在运行
RUNNING=$(ps aux | grep "realtime_signal_scanner.py" | grep -v grep | wc -l)
if [ "$RUNNING" -gt 0 ]; then
    echo "⚠️  系统已经在运行！"
    echo ""
    echo "当前进程："
    ps aux | grep "realtime_signal_scanner.py" | grep -v grep
    echo ""
    read -p "是否停止当前进程并重新启动？(y/N): " RESTART
    if [[ "$RESTART" == "y" || "$RESTART" == "Y" ]]; then
        echo "正在停止当前进程..."
        pkill -f realtime_signal_scanner.py
        sleep 2
        echo "✅ 已停止"
    else
        echo "保持当前运行状态"
        exit 0
    fi
fi

# 3. 配置参数
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 运行配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 扫描间隔
read -p "扫描间隔（秒，默认300=5分钟）: " INTERVAL
INTERVAL=${INTERVAL:-300}

# 最低分数
read -p "最低信号分数（默认70）: " MIN_SCORE
MIN_SCORE=${MIN_SCORE:-70}

# 是否简化输出
read -p "使用简化输出模式？(y/N): " SIMPLE
VERBOSE_FLAG=""
if [[ "$SIMPLE" == "y" || "$SIMPLE" == "Y" ]]; then
    VERBOSE_FLAG="--no-verbose"
fi

# 日志文件
LOG_FILE="/tmp/cryptosignal_scanner.log"

echo ""
echo "配置总结："
echo "  扫描间隔: $INTERVAL 秒"
echo "  最低分数: $MIN_SCORE"
echo "  输出模式: $([ -z "$VERBOSE_FLAG" ] && echo '详细（所有140个币种）' || echo '简化（前10个币种）')"
echo "  日志文件: $LOG_FILE"
echo ""

# 4. 拉取最新代码
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📥 拉取最新代码"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CURRENT_BRANCH=$(git branch --show-current)
echo "当前分支: $CURRENT_BRANCH"

git fetch origin
git pull origin "$CURRENT_BRANCH"

echo "✅ 代码已更新"
echo ""

# 5. 启动后台运行
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 启动后台运行"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 使用nohup后台运行，输出重定向到日志文件
nohup python3 scripts/realtime_signal_scanner.py \
    --interval "$INTERVAL" \
    --min-score "$MIN_SCORE" \
    $VERBOSE_FLAG \
    > "$LOG_FILE" 2>&1 &

PID=$!

# 等待进程启动
sleep 2

# 检查进程是否成功启动
if ps -p $PID > /dev/null; then
    echo "✅ 系统已在后台启动！"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 进程信息"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  PID: $PID"
    echo "  日志文件: $LOG_FILE"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 常用命令"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "查看实时日志（动态显示，跟运行时一样）："
    echo "  ./view_logs.sh"
    echo "  或："
    echo "  tail -f $LOG_FILE"
    echo ""
    echo "查看系统状态："
    echo "  ./check_status.sh"
    echo ""
    echo "停止系统："
    echo "  kill $PID"
    echo "  或："
    echo "  pkill -f realtime_signal_scanner.py"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "✅ 即使关闭Termius，系统也会继续运行！"
    echo "   重新连接后使用 ./view_logs.sh 查看实时输出"
    echo ""

    # 显示最近的日志输出
    echo "最近日志输出（前30行）："
    echo "────────────────────────────────────────"
    sleep 1
    head -30 "$LOG_FILE" 2>/dev/null || echo "等待日志输出..."
    echo "────────────────────────────────────────"
    echo ""
    echo "💡 使用 ./view_logs.sh 查看完整实时日志"
else
    echo "❌ 启动失败！"
    echo ""
    echo "查看日志文件获取错误信息："
    echo "  cat $LOG_FILE"
    exit 1
fi
