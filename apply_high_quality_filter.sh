#!/bin/bash
#
# 应用高质量信号过滤配置
# 用法: bash apply_high_quality_filter.sh
#

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🏆 应用高质量信号过滤配置${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd ~/cryptosignal

# 检查推荐配置文件
if [ ! -f "config/signal_thresholds_RECOMMENDED.json" ]; then
    echo -e "${RED}❌ 未找到推荐配置文件${NC}"
    echo "   请先从仓库拉取最新代码"
    exit 1
fi

# 显示对比
echo -e "${CYAN}📊 配置对比：${NC}"
echo ""
echo "┌─────────────────┬──────────┬──────────────┐"
echo "│     指标        │  当前值  │  推荐值      │"
echo "├─────────────────┼──────────┼──────────────┤"
echo "│ 胜率要求        │   45%    │   60% ⭐     │"
echo "│ 信心度要求      │    8     │   50  ⭐     │"
echo "│ 期望收益        │   10%    │   20% ⭐     │"
echo "│ F因子要求       │   -50    │   +10 ⭐     │"
echo "│ I因子要求       │    0     │   +20 ⭐     │"
echo "│ 数据质量(K线)   │   100    │   150 ⭐     │"
echo "└─────────────────┴──────────┴──────────────┘"
echo ""

echo -e "${YELLOW}⚠️  注意事项：${NC}"
echo "   • 信号数量将减少 50-70%"
echo "   • 信号质量将显著提升"
echo "   • 预期胜率提升至 65%+"
echo "   • 预期收益提升至 3-5%"
echo ""

read -p "是否应用高质量配置？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⏸️  已取消${NC}"
    exit 0
fi

# 备份当前配置
echo ""
echo -e "${CYAN}📦 备份当前配置...${NC}"
BACKUP_FILE="config/signal_thresholds_backup_$(date +%Y%m%d_%H%M%S).json"
cp config/signal_thresholds.json "$BACKUP_FILE"
echo -e "${GREEN}✅ 已备份到: $BACKUP_FILE${NC}"

# 应用新配置
echo ""
echo -e "${CYAN}🔄 应用高质量配置...${NC}"
cp config/signal_thresholds_RECOMMENDED.json config/signal_thresholds.json
echo -e "${GREEN}✅ 配置已更新${NC}"

# 验证JSON格式
echo ""
echo -e "${CYAN}🔍 验证配置格式...${NC}"
if python3 -c "import json; json.load(open('config/signal_thresholds.json'))" 2>/dev/null; then
    echo -e "${GREEN}✅ JSON格式正确${NC}"
else
    echo -e "${RED}❌ JSON格式错误，恢复备份${NC}"
    cp "$BACKUP_FILE" config/signal_thresholds.json
    exit 1
fi

# 清理缓存
echo ""
echo -e "${CYAN}🧹 清理Python缓存...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✅ 缓存已清理${NC}"

# 提示重启
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 高质量配置已应用！${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📝 下一步操作：${NC}"
echo "   1. 停止当前系统: pkill -f 'python.*cryptosignal'"
echo "   2. 重启系统: ./setup.sh"
echo "   3. 观察信号质量变化"
echo ""
echo -e "${CYAN}💡 提示：${NC}"
echo "   • 如需恢复原配置: cp $BACKUP_FILE config/signal_thresholds.json"
echo "   • 备份文件位置: $BACKUP_FILE"
echo ""
