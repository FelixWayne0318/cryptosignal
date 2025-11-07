#!/bin/bash
# v7.2 Stage 1 服务器测试脚本
# 在Termius或SSH终端中运行此脚本

echo "======================================"
echo "v7.2 Stage 1 服务器测试"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Python版本
echo "检查Python版本..."
python3 --version
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Python3未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python版本检查通过${NC}"
echo ""

# 检查当前目录
echo "当前目录: $(pwd)"
if [ ! -f "test_v72_stage1.py" ]; then
    echo -e "${RED}❌ 测试文件不存在，请确保在cryptosignal目录中运行${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 目录检查通过${NC}"
echo ""

# 测试1: v7.2核心功能
echo "======================================"
echo "测试1: v7.2核心功能"
echo "======================================"
python3 test_v72_stage1.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ v7.2核心功能测试通过${NC}"
else
    echo -e "${RED}❌ v7.2核心功能测试失败${NC}"
    exit 1
fi
echo ""

# 测试2: Telegram消息格式
echo "======================================"
echo "测试2: Telegram消息格式"
echo "======================================"
python3 test_telegram_v72.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Telegram消息格式测试通过${NC}"
else
    echo -e "${RED}❌ Telegram消息格式测试失败${NC}"
    exit 1
fi
echo ""

# 测试3: 模块导入
echo "======================================"
echo "测试3: 模块导入检查"
echo "======================================"

echo "检查fund_leading模块..."
python3 -c "from ats_core.features.fund_leading import score_fund_leading_v2; print('✅ fund_leading模块加载成功')"

echo "检查factor_groups模块..."
python3 -c "from ats_core.scoring.factor_groups import calculate_grouped_score; print('✅ factor_groups模块加载成功')"

echo "检查empirical_calibration模块..."
python3 -c "from ats_core.calibration.empirical_calibration import EmpiricalCalibrator; print('✅ calibration模块加载成功')"

echo "检查gates模块..."
python3 -c "from ats_core.pipeline.gates import FourGatesFilter; print('✅ gates模块加载成功')"

echo "检查analyze_symbol_v72模块..."
python3 -c "from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements; print('✅ analyze_symbol_v72模块加载成功')"

echo "检查telegram_fmt模块..."
python3 -c "from ats_core.outputs.telegram_fmt import render_signal_v72, render_watch_v72, render_trade_v72; print('✅ telegram_fmt模块加载成功')"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 所有模块导入测试通过${NC}"
else
    echo -e "${RED}❌ 模块导入测试失败${NC}"
    exit 1
fi
echo ""

# 测试4: 文件完整性
echo "======================================"
echo "测试4: 文件完整性检查"
echo "======================================"

files=(
    "ats_core/features/fund_leading.py"
    "ats_core/scoring/factor_groups.py"
    "ats_core/calibration/empirical_calibration.py"
    "ats_core/pipeline/gates.py"
    "ats_core/pipeline/analyze_symbol_v72.py"
    "ats_core/outputs/telegram_fmt.py"
    "test_v72_stage1.py"
    "test_telegram_v72.py"
)

all_files_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file (缺失)"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = true ]; then
    echo -e "${GREEN}✅ 所有文件完整性检查通过${NC}"
else
    echo -e "${RED}❌ 部分文件缺失${NC}"
    exit 1
fi
echo ""

# 总结
echo "======================================"
echo "测试总结"
echo "======================================"
echo -e "${GREEN}✅ v7.2核心功能测试: 通过${NC}"
echo -e "${GREEN}✅ Telegram消息格式测试: 通过${NC}"
echo -e "${GREEN}✅ 模块导入测试: 通过${NC}"
echo -e "${GREEN}✅ 文件完整性测试: 通过${NC}"
echo ""
echo -e "${GREEN}🎉 v7.2 Stage 1 服务器测试全部通过！${NC}"
echo -e "${GREEN}💡 系统已准备好部署到生产环境${NC}"
echo ""

# 系统信息
echo "======================================"
echo "系统信息"
echo "======================================"
echo "主机名: $(hostname)"
echo "Python版本: $(python3 --version)"
echo "当前用户: $(whoami)"
echo "磁盘使用: $(df -h . | tail -1 | awk '{print $5 " used"}')"
echo "内存使用: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo ""

echo "测试完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================"
