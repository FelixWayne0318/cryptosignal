#!/usr/bin/env bash
set -euo pipefail

# 必须由外部注入，避免明文硬编码
: "${TELEGRAM_BOT_TOKEN:?请通过环境变量 TELEGRAM_BOT_TOKEN 提供 Bot Token}"
: "${TELEGRAM_CHAT_ID:?请通过环境变量 TELEGRAM_CHAT_ID 提供 Chat ID}"

if [[ $# -lt 1 ]]; then
  echo "用法: $0 <file> [caption]" >&2
  exit 2
fi

FILE="$1"; shift || true
CAPTION="${*:-}"

if [[ ! -f "$FILE" ]]; then
  echo "❌ 文件不存在: $FILE" >&2
  exit 3
fi

API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument"

resp="$(curl -sS -X POST "$API" \
  -F "chat_id=${TELEGRAM_CHAT_ID}" \
  -F "document=@${FILE}" \
  -F "caption=${CAPTION}" \
  -F "parse_mode=HTML")"

if printf '%s' "$resp" | grep -q '"ok":true'; then
  echo "✅ 已发送: $FILE"
else
  echo "❌ 发送失败，返回: $resp" >&2
  exit 4
fi