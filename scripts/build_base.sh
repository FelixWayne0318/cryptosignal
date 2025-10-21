#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
. ./scripts/_env.sh
# === TODO: 把下面这行替换成你仓库“构建基础池”的真实入口 ===
python -m app.build_base
