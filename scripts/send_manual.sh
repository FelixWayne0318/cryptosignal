#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
# 兼容老变量名
export ATS_TELEGRAM_BOT_TOKEN="${ATS_TELEGRAM_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
export ATS_TELEGRAM_CHAT_ID="${ATS_TELEGRAM_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"
python3 -m tools.send_text "$@"