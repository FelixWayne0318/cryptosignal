#!/usr/bin/env bash
set -euo pipefail

# 读取 Telegram 凭据
[ -f "$HOME/.telegram.env" ] && . "$HOME/.telegram.env" || true

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"

if [ -z "${BOT_TOKEN}" ] || [ -z "${CHAT_ID}" ]; then
  echo "❌ TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 未设置。请在 ~/.telegram.env 配置后重试。" >&2
  exit 2
fi

if [ $# -lt 1 ]; then
  echo "用法: $0 <file> [caption]" >&2
  exit 2
fi

FILE="$1"
CAPTION="${2:-}"

if [ ! -f "$FILE" ]; then
  echo "❌ 文件不存在: $FILE" >&2
  exit 2
fi

API="https://api.telegram.org/bot${BOT_TOKEN}/sendDocument"

echo "→ 发送: $FILE"
curl -fsS -X POST "$API" \
  -F "chat_id=${CHAT_ID}" \
  -F "document=@${FILE}" \
  -F "caption=${CAPTION}" \
  -m 600 -o /dev/null

echo "✅ 发送完成: $FILE"