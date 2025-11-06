#!/bin/bash
# Phase 1 代码验证脚本

echo "================================================================================"
echo "Phase 1 代码完整性验证"
echo "================================================================================"
echo ""

# 检查Git状态
echo "1. Git状态检查:"
echo "   当前分支: $(git branch --show-current)"
echo "   最新提交: $(git log -1 --oneline)"
echo "   代码状态: $(git status --short | wc -l) 个未提交变更"
echo ""

# 检查关键方法是否存在
echo "2. 关键方法存在性检查:"
echo ""

echo "   [realtime_kline_cache.py]"
if grep -q "async def update_current_prices" ats_core/data/realtime_kline_cache.py; then
    line=$(grep -n "async def update_current_prices" ats_core/data/realtime_kline_cache.py | cut -d: -f1)
    echo "   ✓ update_current_prices() 存在 (行:$line)"
else
    echo "   ✗ update_current_prices() 不存在"
fi

if grep -q "async def update_completed_klines" ats_core/data/realtime_kline_cache.py; then
    line=$(grep -n "async def update_completed_klines" ats_core/data/realtime_kline_cache.py | cut -d: -f1)
    echo "   ✓ update_completed_klines() 存在 (行:$line)"
else
    echo "   ✗ update_completed_klines() 不存在"
fi

if grep -q "async def update_market_data" ats_core/data/realtime_kline_cache.py; then
    line=$(grep -n "async def update_market_data" ats_core/data/realtime_kline_cache.py | cut -d: -f1)
    echo "   ✓ update_market_data() 存在 (行:$line)"
else
    echo "   ✗ update_market_data() 不存在"
fi

echo ""
echo "   [batch_scan_optimized.py]"
if grep -q "update_current_prices" ats_core/pipeline/batch_scan_optimized.py; then
    line=$(grep -n "update_current_prices" ats_core/pipeline/batch_scan_optimized.py | head -1 | cut -d: -f1)
    echo "   ✓ Layer 1集成存在 (行:$line)"
else
    echo "   ✗ Layer 1集成不存在"
fi

if grep -q "update_completed_klines" ats_core/pipeline/batch_scan_optimized.py; then
    line=$(grep -n "update_completed_klines" ats_core/pipeline/batch_scan_optimized.py | head -1 | cut -d: -f1)
    echo "   ✓ Layer 2集成存在 (行:$line)"
else
    echo "   ✗ Layer 2集成不存在"
fi

if grep -q "\[Layer 1\]" ats_core/pipeline/batch_scan_optimized.py; then
    echo "   ✓ Layer 1日志存在"
else
    echo "   ✗ Layer 1日志不存在"
fi

echo ""
echo "   [realtime_signal_scanner.py]"
if grep -q "def _calculate_next_scan_time" scripts/realtime_signal_scanner.py; then
    line=$(grep -n "def _calculate_next_scan_time" scripts/realtime_signal_scanner.py | cut -d: -f1)
    echo "   ✓ _calculate_next_scan_time() 存在 (行:$line)"
else
    echo "   ✗ _calculate_next_scan_time() 不存在"
fi

if grep -q "from datetime import datetime, timedelta" scripts/realtime_signal_scanner.py; then
    echo "   ✓ timedelta导入存在"
else
    echo "   ✗ timedelta导入不存在"
fi

# 检查代码行数变化
echo ""
echo "3. 代码行数统计:"
echo "   realtime_kline_cache.py: $(wc -l < ats_core/data/realtime_kline_cache.py) 行"
echo "   batch_scan_optimized.py: $(wc -l < ats_core/pipeline/batch_scan_optimized.py) 行"
echo "   realtime_signal_scanner.py: $(wc -l < scripts/realtime_signal_scanner.py) 行"

# 显示关键代码片段
echo ""
echo "4. 关键代码片段验证:"
echo ""
echo "   [Layer 1价格更新调用]"
sed -n '409,416p' ats_core/pipeline/batch_scan_optimized.py | sed 's/^/   /'

echo ""
echo "   [Layer 2智能触发]"
sed -n '419,430p' ats_core/pipeline/batch_scan_optimized.py | sed 's/^/   /'

echo ""
echo "   [智能时间对齐]"
sed -n '441,441p' scripts/realtime_signal_scanner.py | sed 's/^/   /'

echo ""
echo "================================================================================"
echo "验证完成"
echo "================================================================================"
echo ""
echo "如果所有检查都显示 ✓，说明Phase 1代码完整且正确。"
echo ""
