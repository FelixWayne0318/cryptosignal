#!/usr/bin/env bash
set -euo pipefail

# 已按你的要求写死在脚本里（需要时也可用环境变量覆盖）
: "${TELEGRAM_BOT_TOKEN:=7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70}"
: "${TELEGRAM_CHAT_ID:=-1003142003085}"

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