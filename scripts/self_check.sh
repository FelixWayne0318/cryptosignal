#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 统一环境
export PYTHONPATH="$PWD"

# 兼容旧变量名 + watch/trade 回退
export ATS_TELEGRAM_BOT_TOKEN="${ATS_TELEGRAM_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
export ATS_TELEGRAM_CHAT_ID="${ATS_TELEGRAM_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"
export TELEGRAM_WATCH_CHAT_ID="${TELEGRAM_WATCH_CHAT_ID:-${TELEGRAM_CHAT_ID:-${ATS_TELEGRAM_CHAT_ID:-}}}"
export TELEGRAM_TRADE_CHAT_ID="${TELEGRAM_TRADE_CHAT_ID:-${TELEGRAM_CHAT_ID:-${ATS_TELEGRAM_CHAT_ID:-}}}"

# 常见坑：CRLF / 执行位
sed -i 's/\r$//' scripts/*.sh 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true

# 清理缓存
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find . -name '*.py[co]' -delete 2>/dev/null || true

# SELF_CHECK_SEND=1 时每个环节会实发 Telegram 消息
exec python3 -m tools.self_check "$@"