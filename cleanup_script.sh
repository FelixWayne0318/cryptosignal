#!/bin/bash
# ==========================================
# CryptoSignal v7.3.46 仓库清理脚本
# 生成日期: 2025-11-16
# 用途: 清理无用文件,整理文件结构
# ==========================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=============================================="
echo "🧹 CryptoSignal v7.3.46 仓库清理"
echo "=============================================="
echo ""

# 进入项目目录
cd ~/cryptosignal 2>/dev/null || {
    echo -e "${RED}❌ ~/cryptosignal 目录不存在${NC}"
    exit 1
}

echo "📋 清理计划:"
echo "  1. 删除3个无用脚本"
echo "  2. 移动配置补丁到docs/"
echo "  3. 移动报告文件到reports/"
echo "  4. 统一版本号为7.3.46"
echo ""

# 询问确认
read -p "是否继续? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "🚀 开始清理..."
echo ""

# ==========================================
# Step 1: 删除无用脚本 (P0)
# ==========================================
echo "📝 Step 1: 删除无用脚本"

if [ -f "deploy_and_run.sh" ]; then
    rm deploy_and_run.sh
    echo -e "${GREEN}  ✅ 已删除 deploy_and_run.sh${NC}"
else
    echo -e "${YELLOW}  ⏭️  deploy_and_run.sh 不存在${NC}"
fi

if [ -f "scripts/analyze_dependencies.py" ]; then
    rm scripts/analyze_dependencies.py
    echo -e "${GREEN}  ✅ 已删除 scripts/analyze_dependencies.py${NC}"
else
    echo -e "${YELLOW}  ⏭️  scripts/analyze_dependencies.py 不存在${NC}"
fi

if [ -f "scripts/unify_version.py" ]; then
    rm scripts/unify_version.py
    echo -e "${GREEN}  ✅ 已删除 scripts/unify_version.py${NC}"
else
    echo -e "${YELLOW}  ⏭️  scripts/unify_version.py 不存在${NC}"
fi

echo ""

# ==========================================
# Step 2: 移动配置补丁到docs/ (P1)
# ==========================================
echo "📝 Step 2: 移动配置补丁"

if [ -f "config_patch_p0_fixes.json" ]; then
    mv config_patch_p0_fixes.json docs/
    echo -e "${GREEN}  ✅ 已移动 config_patch_p0_fixes.json → docs/${NC}"
else
    echo -e "${YELLOW}  ⏭️  config_patch_p0_fixes.json 不存在${NC}"
fi

echo ""

# ==========================================
# Step 3: 移动报告文件到reports/ (P1)
# ==========================================
echo "📝 Step 3: 移动报告文件"

# 创建子目录
mkdir -p reports/scans
mkdir -p reports/summaries

# 移动硬编码扫描报告
if ls HARDCODE_SCAN_REPORT_*.md 1> /dev/null 2>&1; then
    mv HARDCODE_SCAN_REPORT_*.md reports/scans/
    echo -e "${GREEN}  ✅ 已移动 HARDCODE_SCAN_REPORT_*.md → reports/scans/${NC}"
else
    echo -e "${YELLOW}  ⏭️  HARDCODE_SCAN_REPORT_*.md 不存在${NC}"
fi

# 移动扫描摘要
if ls SCAN_SUMMARY_*.txt 1> /dev/null 2>&1; then
    mv SCAN_SUMMARY_*.txt reports/summaries/
    echo -e "${GREEN}  ✅ 已移动 SCAN_SUMMARY_*.txt → reports/summaries/${NC}"
else
    echo -e "${YELLOW}  ⏭️  SCAN_SUMMARY_*.txt 不存在${NC}"
fi

echo ""

# ==========================================
# Step 4: 统一版本号为7.3.46 (P0)
# ==========================================
echo "📝 Step 4: 统一版本号"

echo "7.3.46" > VERSION
echo -e "${GREEN}  ✅ 已更新 VERSION → 7.3.46${NC}"

# 更新setup.sh中的版本号
if [ -f "setup.sh" ]; then
    sed -i 's/v7\.3\.4/v7.3.46/g' setup.sh
    echo -e "${GREEN}  ✅ 已更新 setup.sh 版本号${NC}"
fi

# 更新realtime_signal_scanner.py中的版本号
if [ -f "scripts/realtime_signal_scanner.py" ]; then
    sed -i 's/v7\.3\.4/v7.3.46/g' scripts/realtime_signal_scanner.py
    echo -e "${GREEN}  ✅ 已更新 realtime_signal_scanner.py 版本号${NC}"
fi

echo ""

# ==========================================
# Step 5: 验证清理结果
# ==========================================
echo "📝 Step 5: 验证清理结果"
echo ""

echo "根目录文件:"
ls -lh *.sh *.md *.txt 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'

echo ""
echo "reports/目录结构:"
find reports/ -type f | head -20 | sed 's/^/  /'

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 清理完成!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "清理效果:"
echo "  ✅ 删除了3个无用脚本"
echo "  ✅ 移动了配置补丁到docs/"
echo "  ✅ 整理了报告文件到reports/"
echo "  ✅ 统一了版本号为7.3.46"
echo ""
echo "下一步建议:"
echo "  1. 验证系统: ./setup.sh"
echo "  2. 查看审计报告: cat SYSTEM_AUDIT_REPORT_v7.3.46_2025-11-16.md"
echo "  3. 处理P0问题 (详见审计报告)"
echo ""
