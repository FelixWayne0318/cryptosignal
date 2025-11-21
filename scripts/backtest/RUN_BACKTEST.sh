#!/bin/bash
# ==========================================
# CryptoSignal v7.4.2 回测执行脚本
# 用途：在服务器上运行完整回测
# 日期：2025-11-19
# ==========================================

set -e

echo "=========================================="
echo "🔬 CryptoSignal v7.4.2 回测系统"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查环境
echo "📋 步骤1: 检查环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3 已安装: $(python3 --version)${NC}"

# 检查API密钥
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
    echo -e "${YELLOW}⚠️  警告: BINANCE_API_KEY 或 BINANCE_API_SECRET 环境变量未设置${NC}"
    echo "   请先设置环境变量："
    echo "   export BINANCE_API_KEY='your_key'"
    echo "   export BINANCE_API_SECRET='your_secret'"
    echo ""
    read -p "是否继续（可能失败）？ (y/n): " continue
    if [ "$continue" != "y" ]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ Binance API 密钥已配置${NC}"
fi

# 创建报告目录
echo ""
echo "📋 步骤2: 准备目录..."
mkdir -p reports
mkdir -p data/backtest_cache
echo -e "${GREEN}✅ 目录已创建${NC}"

# 回测配置
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_JSON="reports/backtest_${TIMESTAMP}.json"
REPORT_MD="reports/backtest_${TIMESTAMP}.md"

echo ""
echo "=========================================="
echo "🚀 开始回测"
echo "=========================================="
echo ""
echo "测试配置："
echo "  币种: ETHUSDT, BTCUSDT, BNBUSDT"
echo "  时间: 2024-08-01 ~ 2024-11-01 (3个月)"
echo "  输出: $REPORT_JSON"
echo "  报告: $REPORT_MD"
echo ""

# 运行回测
python3 scripts/backtest_four_step.py \
    --symbols ETHUSDT,BTCUSDT,BNBUSDT \
    --start 2024-08-01 \
    --end 2024-11-01 \
    --output "$REPORT_JSON" \
    --report-format markdown \
    --report-output "$REPORT_MD" \
    --verbose

# 检查结果
if [ -f "$REPORT_JSON" ]; then
    echo ""
    echo "=========================================="
    echo "✅ 回测完成！"
    echo "=========================================="
    echo ""
    echo "📊 结果文件："
    echo "  - JSON: $REPORT_JSON"
    echo "  - Markdown: $REPORT_MD"
    echo ""
    echo "📈 文件大小："
    ls -lh "$REPORT_JSON" "$REPORT_MD"
    echo ""
    echo "🔍 快速预览："
    echo "----------------------------------------"
    head -50 "$REPORT_MD"
    echo "----------------------------------------"
    echo ""
    echo "💡 完整报告请查看: $REPORT_MD"
else
    echo -e "${RED}❌ 回测失败，未生成报告文件${NC}"
    exit 1
fi
