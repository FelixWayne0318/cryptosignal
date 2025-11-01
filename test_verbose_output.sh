#!/bin/bash
# 测试verbose输出功能的快速测试脚本

echo "========================================"
echo "🧪 测试verbose输出功能"
echo "========================================"
echo ""

cd /home/user/cryptosignal

echo "测试1: 普通模式（只显示前10个币种的详细信息）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 scripts/realtime_signal_scanner.py \
    --max-symbols 20 \
    --no-telegram \
    | grep -A 15 "正在分析"

echo ""
echo ""
echo "测试2: Verbose模式（显示所有币种的详细信息）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 scripts/realtime_signal_scanner.py \
    --max-symbols 20 \
    --no-telegram \
    --verbose \
    | grep -A 15 "正在分析"

echo ""
echo "✅ 测试完成！"
echo ""
echo "预期结果："
echo "  - 测试1: 只有前10个币种显示详细因子分数"
echo "  - 测试2: 所有20个币种都显示详细因子分数"
