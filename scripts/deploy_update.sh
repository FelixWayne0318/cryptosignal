#!/usr/bin/env bash
set -euo pipefail

# === 基本配置（可在外部用环境变量覆盖） ===
REPO_DIR="${REPO_DIR:-$HOME/ats-analyzer}"
BRANCH="${BRANCH:-main}"

# Telegram 变量（用你提供的值；也可在 shell 里 export 覆盖）
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70}"
export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:--1003142003085}"
export TELEGRAM_WATCH_CHAT_ID="${TELEGRAM_WATCH_CHAT_ID:-$TELEGRAM_CHAT_ID}"
export TELEGRAM_TRADE_CHAT_ID="${TELEGRAM_TRADE_CHAT_ID:-$TELEGRAM_CHAT_ID}"

echo "▶ Deploying repo at: $REPO_DIR (branch: $BRANCH)"
cd "$REPO_DIR" || { echo "❌ Repo not found: $REPO_DIR"; exit 1; }

echo "▶ Git fetch & hard reset"
git fetch origin
git reset --hard "origin/${BRANCH}"

echo "▶ Fix line endings & exec bits"
sed -i 's/\r$//' scripts/*.sh 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true

echo "▶ Cleanup python caches"
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find . -name '*.py[co]' -delete 2>/dev/null || true

echo "▶ Set PYTHONPATH"
export PYTHONPATH="$PWD"

echo "▶ Run self-check (non-blocking)"
if ./scripts/self_check.sh; then
  echo "✅ self_check passed (or with warnings)"
else
  echo "⚠️ self_check returned non-zero (check logs above); continue for manual verification"
fi

echo "▶ Send verification message to watch channel"
python3 -m tools.send_symbol --symbol BTCUSDT --to watch --tag watch --note "部署验证：渲染&发送" || {
  echo "⚠️ send_symbol failed; sending a plain text instead"
  ./scripts/send_manual.sh --to watch --tag watch "部署完成（send_symbol失败，需排查）" || true
}

echo "✅ Done."