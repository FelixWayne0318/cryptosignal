#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 统一环境
export PYTHONPATH="$PWD"

# 兼容旧变量名（如代码里还在读 ATS_*，这里自动映射）
export ATS_TELEGRAM_BOT_TOKEN="${ATS_TELEGRAM_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
export ATS_TELEGRAM_CHAT_ID="${ATS_TELEGRAM_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

# 常见坑：行尾 / 执行位
sed -i 's/\r$//' scripts/*.sh 2>/dev/null || true
chmod +x scripts/*.sh || true

# 清理字节码，避免旧缓存干扰
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find . -name '*.py[co]' -delete 2>/dev/null || true

exec python3 -m tools.self_check "$@"