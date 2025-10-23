#!/usr/bin/env bash
set -euo pipefail

# 解析仓库根目录（脚本所在目录的上一级）
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

# 让 Python 以源码方式加载仓库
export PYTHONPATH="$REPO"

# 如需跳过真实发送，可设置 ATS_SKIP_SEND=1
# 例如：ATS_SKIP_SEND=1 ./scripts/scan_watch.sh --n 30
exec python3 -m tools.scan_watch "$@"