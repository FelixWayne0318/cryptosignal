#!/usr/bin/env bash
# 启动WebSocket实时信号扫描器

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

export PYTHONPATH="$REPO"

echo "======================================================================"
echo "🚀 启动WebSocket实时信号扫描器"
echo "======================================================================"
echo ""
echo "功能: 扫描200个高流动性币种，发送Prime信号到Telegram"
echo "性能: 初始化3-4分钟，后续扫描12-15秒"
echo "模式: 仅发送信号（不执行交易）"
echo ""
echo "======================================================================"
echo ""

# 检查环境变量
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "⚠️  警告: TELEGRAM_BOT_TOKEN 未设置"
    echo "   信号将只显示在控制台，不会发送到Telegram"
    echo ""
fi

# 默认参数
INTERVAL=${INTERVAL:-300}  # 默认5分钟扫描一次
MIN_SCORE=${MIN_SCORE:-70}  # 默认最低分数70

echo "配置:"
echo "  扫描间隔: ${INTERVAL}秒 ($((INTERVAL/60))分钟)"
echo "  最低分数: ${MIN_SCORE}"
echo ""
echo "======================================================================"
echo ""

# 启动扫描器
exec python3 scripts/realtime_signal_scanner.py \
    --interval "$INTERVAL" \
    --min-score "$MIN_SCORE" \
    "$@"
