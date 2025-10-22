#!/usr/bin/env bash
# 简单的“候选池->分析->渲染(可选发送)”入口
# 用法示例：
#   ATS_SKIP_SEND=1 ./scripts/scan_watch.sh --n 20
#   ./scripts/scan_watch.sh --n 12 --send
#   ./scripts/scan_watch.sh BTCUSDT ETHUSDT SOLUSDT  # 指定若干币，不走候选池

set -euo pipefail

# 仓库路径，默认 $HOME/ats-analyzer，如需自定义可 export REPO=/path/to/repo
REPO="${REPO:-$HOME/ats-analyzer}"

cd "$REPO"
export PYTHONPATH="$REPO"

# 交给 Python 模块执行，参数原样透传
exec python3 -m tools.scan_watch "$@"