#!/usr/bin/env bash
set -euo pipefail
REPO="$HOME/ats-analyzer"
cd "$REPO"
export PYTHONPATH="$REPO"
exec python3 -m tools.oneoff "$@"