#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
# write crontab entries (UTC)
CRON_TMP=$(mktemp)
{
  echo '*/30 * * * * cd '"$PWD"' && git pull -q'
  echo '5 0 * * *  cd '"$PWD"' && . .venv/bin/activate && python -m ats_core.pools.base_builder >> logs/base.log 2>&1'
  echo '5 * * * *  cd '"$PWD"' && . .venv/bin/activate && python -m ats_core.pipeline.batch_scan >> logs/scan.log 2>&1'
} > "$CRON_TMP"
crontab "$CRON_TMP"
rm -f "$CRON_TMP"
echo "cron installed."