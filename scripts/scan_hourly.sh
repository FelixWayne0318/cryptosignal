#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
. ./scripts/_env.sh
# === TODO: 把下面这行替换成你仓库“小时扫描”的真实入口 ===
python -m app.scan_hourly
