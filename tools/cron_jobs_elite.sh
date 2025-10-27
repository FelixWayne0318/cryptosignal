#!/usr/bin/env bash
# Elite版定时任务配置（替代旧方案）
set -e
cd "$(dirname "$0")/.."

CRON_TMP=$(mktemp)
{
  # 每30分钟拉取代码更新
  echo '*/30 * * * * cd '"$PWD"' && git pull -q'

  # 每小时:05运行Elite扫描（包含候选池构建+分析）
  echo '5 * * * *  cd '"$PWD"' && export PYTHONPATH='"$PWD"' && python3 -m tools.full_run_elite --send >> logs/elite_scan.log 2>&1'

  # 备选：每天00:05单独更新Elite候选池（可选，如果想缓存候选池）
  # echo '5 0 * * *  cd '"$PWD"' && export PYTHONPATH='"$PWD"' && python3 -c "from ats_core.pools.elite_builder import build_elite_universe; build_elite_universe()" >> logs/elite_pool.log 2>&1'

} > "$CRON_TMP"

crontab "$CRON_TMP"
rm -f "$CRON_TMP"

echo "✅ Elite版Cron已安装"
echo ""
echo "定时任务："
echo "  - 每30分钟：拉取代码"
echo "  - 每小时:05：运行Elite扫描（候选池+分析+发送）"
echo ""
echo "查看日志："
echo "  tail -f logs/elite_scan.log"
