#!/bin/bash
# coding: utf-8
#
# CryptoSignal 完整系统运行脚本
#
# 功能:
# 1. 扫描所有高流动性币种（140个）
# 2. 发送Prime信号到Telegram群组
# 3. 实时输出详细日志
#
# 使用方法:
#     bash scripts/run_full_system.sh
#
# 或者定期扫描（每5分钟）:
#     bash scripts/run_full_system.sh --interval 300

set -e  # 遇到错误立即退出

echo "================================================================================"
echo "  CryptoSignal 完整系统启动"
echo "================================================================================"
echo ""

# 进入项目目录
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)
echo "📁 项目目录: $PROJECT_ROOT"

# 检查环境变量
echo ""
echo "🔍 检查环境变量..."

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ 错误: 未设置 TELEGRAM_BOT_TOKEN"
    echo "   请运行: export TELEGRAM_BOT_TOKEN='your_token'"
    exit 1
fi
echo "   ✅ TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:0:20}..."

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "❌ 错误: 未设置 TELEGRAM_CHAT_ID"
    echo "   请运行: export TELEGRAM_CHAT_ID='your_chat_id'"
    exit 1
fi
echo "   ✅ TELEGRAM_CHAT_ID: $TELEGRAM_CHAT_ID"

# 检查Binance API密钥（可选）
if [ -n "$BINANCE_API_KEY" ]; then
    echo "   ✅ BINANCE_API_KEY: ${BINANCE_API_KEY:0:10}..."
else
    echo "   ⚠️  未设置 BINANCE_API_KEY（部分功能受限）"
fi

# 检查Python版本
echo ""
echo "🐍 检查Python环境..."
python3 --version || {
    echo "❌ 错误: Python3未安装"
    exit 1
}

# 检查依赖
echo ""
echo "📦 检查依赖..."
python3 -c "import aiohttp, pandas, numpy" 2>/dev/null && {
    echo "   ✅ 核心依赖已安装"
} || {
    echo "   ❌ 缺少依赖，正在安装..."
    pip3 install -r requirements.txt
}

# 创建日志目录
mkdir -p logs

# 解析参数
INTERVAL=0
MIN_SCORE=70
MAX_SYMBOLS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --min-score)
            MIN_SCORE="$2"
            shift 2
            ;;
        --max-symbols)
            MAX_SYMBOLS="--max-symbols $2"
            shift 2
            ;;
        --test)
            MAX_SYMBOLS="--max-symbols 10"
            echo "   🧪 测试模式: 只扫描10个币种"
            shift
            ;;
        *)
            echo "❌ 未知参数: $1"
            exit 1
            ;;
    esac
done

# 显示运行参数
echo ""
echo "================================================================================"
echo "  运行参数"
echo "================================================================================"
echo "   最低分数阈值: $MIN_SCORE"
if [ $INTERVAL -gt 0 ]; then
    echo "   扫描模式: 定期扫描"
    echo "   扫描间隔: $INTERVAL 秒 ($((INTERVAL/60)) 分钟)"
else
    echo "   扫描模式: 单次扫描"
fi
if [ -n "$MAX_SYMBOLS" ]; then
    echo "   币种限制: ${MAX_SYMBOLS#--max-symbols }"
else
    echo "   币种限制: 无（扫描所有高流动性币种）"
fi
echo "================================================================================"

# 确认继续
echo ""
read -p "▶️  按Enter键开始运行，或Ctrl+C取消... " -r
echo ""

# 准备日志文件
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/full_system_${TIMESTAMP}.log"

echo "📝 日志文件: $LOG_FILE"
echo ""

# 构建运行命令
CMD="python3 scripts/realtime_signal_scanner.py --min-score $MIN_SCORE"

if [ $INTERVAL -gt 0 ]; then
    CMD="$CMD --interval $INTERVAL"
fi

if [ -n "$MAX_SYMBOLS" ]; then
    CMD="$CMD $MAX_SYMBOLS"
fi

echo "================================================================================"
echo "  🚀 启动中..."
echo "================================================================================"
echo ""
echo "运行命令: $CMD"
echo ""

# 运行系统（同时输出到终端和日志）
$CMD 2>&1 | tee "$LOG_FILE"

# 捕获退出状态
EXIT_CODE=$?

echo ""
echo "================================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "  ✅ 系统正常退出"
else
    echo "  ❌ 系统异常退出 (退出码: $EXIT_CODE)"
fi
echo "================================================================================"
echo ""
echo "📝 完整日志已保存到: $LOG_FILE"
echo ""

exit $EXIT_CODE
