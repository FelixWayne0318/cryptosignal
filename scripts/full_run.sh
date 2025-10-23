#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

export PYTHONPATH="$REPO"

# 用法示例：
#   ./scripts/full_run.sh --limit 50
#   ./scripts/full_run.sh --send --only-prime
#   ./scripts/full_run.sh --limit 50 --save-json
exec python3 -m tools.full_run "$@"