#!/usr/bin/env bash
set -euo pipefail

# === 基本配置（可在外部用环境变量覆盖） ===
REPO_DIR="${REPO_DIR:-$HOME/ats-analyzer}"
BRANCH="${BRANCH:-main}"

# === Telegram 变量（必须通过环境变量注入；不再硬编码） ===
# 可选：将这些写入 /etc/environment 或 systemd unit 的 Environment= 中
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
TELEGRAM_WATCH_CHAT_ID="${TELEGRAM_WATCH_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"
TELEGRAM_TRADE_CHAT_ID="${TELEGRAM_TRADE_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

require_env() {
  local name="$1" val="$2"
  if [[ -z "$val" ]]; then
    echo "⚠️ 环境变量 $name 未设置：相关发送步骤将被跳过" >&2
    return 1
  fi
  return 0
}

echo "▶ Deploying repo at: $REPO_DIR (branch: $BRANCH)"
cd "$REPO_DIR" || { echo "❌ Repo not found: $REPO_DIR"; exit 1; }

echo "▶ Fetch & checkout"
git fetch --all -p
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "▶ Install deps (optional, skip if managed elsewhere)"
if [[ -f requirements.txt ]]; then
  python3 -m pip install -U -r requirements.txt
fi

echo "▶ Run self-check (non-blocking)"
if ./scripts/self_check.sh; then
  echo "✅ self_check passed (or with warnings)"
else
  echo "⚠️ self_check returned non-zero (check logs above); continue for manual verification"
fi

echo "▶ Send verification message to watch channel (if TELEGRAM_* provided)"
if require_env TELEGRAM_BOT_TOKEN "$TELEGRAM_BOT_TOKEN" && require_env TELEGRAM_WATCH_CHAT_ID "$TELEGRAM_WATCH_CHAT_ID"; then
  export TELEGRAM_BOT_TOKEN TELEGRAM_WATCH_CHAT_ID TELEGRAM_TRADE_CHAT_ID TELEGRAM_CHAT_ID
  if python3 -m tools.send_symbol --symbol BTCUSDT --to watch --tag watch --note "部署验证：渲染&发送"; then
    echo "✅ verification (send_symbol)"
  else
    echo "⚠️ send_symbol failed; try plain text"
    ./scripts/send_manual.sh --to watch --tag watch "部署完成（send_symbol失败，需排查）" || true
  fi
else
  echo "ℹ️ 未提供 Telegram 凭据，跳过发送验证步骤"
fi

echo "✅ Done."