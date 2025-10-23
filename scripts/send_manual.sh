# scripts/send_manual.sh
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export PYTHONPATH="$PWD"

TO="${1:-watch}"
shift || true

# 兼容别名：trade -> prime
if [[ "$TO" == "trade" ]]; then
  TO="prime"
fi

# 标记（可选第二个参数，否则跟 TO 一样）
TAG="${1:-$TO}"
shift || true

# 剩余的拼成文本
TEXT="${*:-手动播报：无内容}"
# 清 CRLF + 执行位
sed -i 's/\r$//' scripts/*.sh 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true

# 直接调用现有 Python 文本发送器（它的 --to 不认识 trade，所以我们已映射成 prime）
python3 -m tools.send_text --to "$TO" --tag "$TAG" "$TEXT"