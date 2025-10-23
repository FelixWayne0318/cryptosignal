#!/usr/bin/env bash
# 发送一条手动文本到 Telegram（支持 watch / trade / base 三类目的地）
# 用法示例：
#   ./scripts/send_manual.sh --to watch --tag watch "手动测试：网络与权限已就绪 ✅"
#   ./scripts/send_manual.sh --to trade "这是发到正式频道的一条消息"
#   ./scripts/send_manual.sh --chat-id -100xxxxxxxxx "直接指定 chat_id 发送"
#
# 依赖环境变量（至少需要 BOT）：
#   TELEGRAM_BOT_TOKEN=xxx:yyyy
#   TELEGRAM_CHAT_ID                       # 兜底默认
#   TELEGRAM_WATCH_CHAT_ID                 # 观察频道（可选，优先于 TELEGRAM_CHAT_ID）
#   TELEGRAM_TRADE_CHAT_ID                 # 正式频道（可选，优先于 TELEGRAM_CHAT_ID）

set -euo pipefail
cd "$(dirname "$0")/.."

# --- 统一换行与执行位，避免 CRLF/Permission denied ---
sed -i 's/\r$//' scripts/*.sh 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true

DEST="watch"          # watch | trade | base
CHAT_ID=""
TAG="none"            # watch | trade | prime | none

usage() {
  cat <<USAGE
Usage: $0 [--to watch|trade|base] [--chat-id ID] [--tag watch|trade|prime|none] "text ..."
Examples:
  $0 --to watch --tag watch "手动测试：网络与权限已就绪 ✅"
  $0 --to trade "这是发到正式频道的一条消息"
  $0 --chat-id -1003142003085 "直接指定 chat_id 发送"
USAGE
}

# --- 解析参数 ---
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --to)      DEST="${2:-}"; shift 2 ;;
    --chat-id) CHAT_ID="${2:-}"; shift 2 ;;
    --tag)     TAG="${2:-}"; shift 2 ;;
    --) shift; break ;;
    *)  ARGS+=("$1"); shift ;;
  esac
done
# 剩余参数也并入文本
if [[ $# -gt 0 ]]; then
  while [[ $# -gt 0 ]]; do ARGS+=("$1"); shift; done
fi

if [[ ${#ARGS[@]} -eq 0 ]]; then
  echo "❌ 缺少要发送的文本"; usage; exit 2
fi

# 拼接文本（保留空格）
TEXT="$(printf "%s " "${ARGS[@]}")"
TEXT="${TEXT% }"

# --- 解析目的地得到 chat_id ---
# 优先级：--chat-id > 目的地专用env > TELEGRAM_CHAT_ID
case "$DEST" in
  watch)
    CHAT_ID="${CHAT_ID:-${TELEGRAM_WATCH_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}}"
    ;;
  trade|prime)
    CHAT_ID="${CHAT_ID:-${TELEGRAM_TRADE_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}}"
    ;;
  base)
    CHAT_ID="${CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"
    ;;
  *)
    echo "❌ --to 只支持 watch|trade|base；收到：$DEST"
    exit 2
    ;;
esac

BOT="${TELEGRAM_BOT_TOKEN:-}"
if [[ -z "${BOT}" ]]; then
  echo "❌ 未设置 TELEGRAM_BOT_TOKEN"
  exit 2
fi
if [[ -z "${CHAT_ID}" ]]; then
  echo "❌ 未能解析 chat_id（可通过 --chat-id 或环境变量提供）"
  exit 2
fi

# --- 追加标签（可选） ---
if [[ "${TAG}" != "none" && -n "${TAG}" ]]; then
  TEXT="${TEXT}"$'\n'"#${TAG}"
fi

# --- 发送 ---
API="https://api.telegram.org/bot${BOT}/sendMessage"

# 使用 --data-urlencode，保证中文与换行安全
resp="$(curl -sS -X POST \
  --data-urlencode "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${TEXT}" \
  -d "parse_mode=HTML" \
  -d "disable_web_page_preview=true" \
  "${API}" || true)"

# 粗略判断是否成功
if echo "${resp}" | grep -q '"ok":true'; then
  echo "✅ 已发送到 ${DEST} (${CHAT_ID})"
else
  echo "⚠️ 发送可能失败，返回：${resp}"
  exit 1
fi