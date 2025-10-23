#!/usr/bin/env bash
# 安全部署脚本（无硬编码密钥版）
# 用法：直接执行。可在仓库根目录放置 .env 提供环境变量。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 读取 .env（若存在）
if [[ -f ".env" ]]; then
  # shellcheck disable=SC2046
  export $(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' .env | xargs) || true
fi

# 必需环境变量检查（仅当需要向 Telegram 发送验证信息时）
NEED_TG_SEND="${NEED_TG_SEND:-1}"   # 置为0则不发验证消息
if [[ "${NEED_TG_SEND}" == "1" ]]; then
  : "${TELEGRAM_BOT_TOKEN:?请在环境变量或 .env 中设置 TELEGRAM_BOT_TOKEN}"
  : "${TELEGRAM_CHAT_ID:?请在环境变量或 .env 中设置 TELEGRAM_CHAT_ID}"
fi

# 建议：固定 Python 路径或使用系统 python3
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

echo "[deploy] pulling latest..."
git fetch --all -q
git pull --rebase -q

echo "[deploy] self check..."
chmod +x ./scripts/self_check.sh || true
./scripts/self_check.sh

if [[ "${NEED_TG_SEND}" == "1" ]]; then
  echo "[deploy] send verification message to Telegram..."
  # 发送一条简短验证消息（走工具，不在脚本硬编码 Token/ChatID）
  "${PYTHON_BIN}" -m tools.send_text \
    --text "✅ 部署完成：$(date -u +'%Y-%m-%d %H:%M:%S UTC')" \
    --to "${TELEGRAM_CHAT_ID}" || {
      echo "⚠️ 发送验证消息失败（忽略错误