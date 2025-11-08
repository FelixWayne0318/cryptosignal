#!/bin/bash
# ==========================================
# 部署v7.2重组后的代码
# 分支：claude/reorganize-repo-structure-011CUvEzbqkdKuPnh33PSRPn
# ==========================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=============================================="
echo "🚀 部署v7.2重组后的代码"
echo "=============================================="
echo ""

# 检测项目目录（支持多种路径）
if [ -d "/home/user/cryptosignal" ]; then
    REPO_DIR="/home/user/cryptosignal"
elif [ -d "$HOME/cryptosignal" ]; then
    REPO_DIR="$HOME/cryptosignal"
else
    echo -e "${RED}❌ 找不到cryptosignal目录${NC}"
    echo "请确认项目路径"
    exit 1
fi

cd "$REPO_DIR" || {
    echo -e "${RED}❌ 无法进入目录: $REPO_DIR${NC}"
    exit 1
}

echo "📁 项目目录: $(pwd)"
echo ""

# 新分支名（本次重组创建的分支）
NEW_BRANCH="claude/reorganize-repo-structure-011CUvEzbqkdKuPnh33PSRPn"

echo "1️⃣  拉取远程分支信息..."
git fetch origin

echo ""
echo "2️⃣  切换到新分支: $NEW_BRANCH"
git checkout "$NEW_BRANCH"

echo ""
echo "3️⃣  拉取最新代码..."
git pull origin "$NEW_BRANCH"

echo ""
echo "4️⃣  清理Python缓存（重要！确保新代码生效）..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✅ Python缓存已清理${NC}"

echo ""
echo "5️⃣  验证重组后的目录结构..."
echo "   检查tests/目录: $(ls tests/*.py 2>/dev/null | wc -l) 个测试文件"
echo "   检查diagnose/目录: $(ls diagnose/*.py 2>/dev/null | wc -l) 个诊断文件"
echo "   检查docs/目录: $(ls docs/*.md 2>/dev/null | wc -l) 个文档文件"
echo -e "${GREEN}✅ 目录结构验证通过${NC}"

echo ""
echo "6️⃣  开始部署v7.2系统..."
echo "=============================================="
./setup.sh

echo ""
echo "=============================================="
echo -e "${GREEN}✅ 部署完成！${NC}"
echo "=============================================="
echo ""
echo "📋 重组说明："
echo "   - 测试文件已移至 tests/"
echo "   - 诊断文件已移至 diagnose/"
echo "   - 文档文件已移至 docs/"
echo "   - 规范文档已更新到 v7.2"
echo ""
echo "⚙️  环境变量控制："
echo "   - 自动提交报告：默认启用"
echo "   - 手动测试禁用：export AUTO_COMMIT_REPORTS=false"
echo ""
echo "📚 详细文档："
echo "   - 重组总结：REORGANIZATION_SUMMARY.md"
echo "   - 规范索引：standards/00_INDEX.md"
echo ""
