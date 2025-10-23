#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"

# 说明：
# 旧版 send_manual.sh 是“纯文本直发”，不会走正式模板。
# 现在改成超薄包装器，直接把参数转给 tools.send_symbol（统一用正式模板）。
#
# 用法示例：
#   ./scripts/send_manual.sh --symbol BTCUSDT --to watch --tag watch --note "手动观察（用模板）"
#   ./scripts/send_manual.sh --symbol ETHUSDT --to trade --tag trade --note "手动正式（用模板）" --ttl-h 6
#
# Chat 映射（未显式 --chat-id 时）：
#   to=watch/base -> TELEGRAM_WATCH_CHAT_ID 或 TELEGRAM_CHAT_ID
#   to=trade/prime -> TELEGRAM_TRADE_CHAT_ID 或 TELEGRAM_PRIME_CHAT_ID 或 TELEGRAM_CHAT_ID

exec python3 -m tools.send_symbol "$@"