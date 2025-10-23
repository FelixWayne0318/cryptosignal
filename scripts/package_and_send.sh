#!/usr/bin/env bash
set -euo pipefail

# 已按你的要求写死在脚本里（也可通过环境变量覆盖）
: "${TELEGRAM_BOT_TOKEN:=7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70}"
: "${TELEGRAM_CHAT_ID:=-1003142003085}"

# 自动探测仓库根；失败则回退到 ~/ats-analyzer
REPO="${REPO:-}"
if [[ -z "${REPO}" ]]; then
  if topdir="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    REPO="$topdir"
  else
    REPO="$HOME/ats-analyzer"
  fi
fi

if [[ ! -d "$REPO" ]]; then
  echo "❌ 找不到仓库目录: $REPO" >&2
  exit 2
fi

TS="$(date +%Y%m%d-%H%M%S)"
OUT="/tmp/ats-analyzer_${TS}.tgz"

HOST="$(hostname -f 2>/dev/null || hostname)"
IPV4="$(ip -4 addr show 2>/dev/null | awk '/inet /{print $2}' | paste -sd',' - || true)"
GITINFO="$(cd "$REPO" && (git rev-parse --short HEAD && git log -1 --pretty=%s) 2>/dev/null | paste -sd' ' - || echo 'no-git')"

# 打包（排除缓存与无关目录，避免包太大）
tar -C "$REPO" -czf "$OUT" \
  --exclude-vcs \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.venv' \
  --exclude='.env' \
  --exclude='.DS_Store' \
  --exclude='data/cache' \
  --exclude='data/run_*' \
  .

CAPTION="Repo backup ${TS}
host: ${HOST}
ip: ${IPV4}
git: ${GITINFO}"

# 发送
TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID" \
bash "$(dirname "$0")/send_tg.sh" "$OUT" "$CAPTION"